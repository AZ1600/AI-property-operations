"""HTTP workflow checks use an isolated database and never call an AI service."""
import os
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.database import Base
from app.main import app, get_db


class WorkflowTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine('sqlite://', poolclass=StaticPool,
                                    connect_args={'check_same_thread': False})
        Base.metadata.create_all(self.engine)

        def database():
            with Session(self.engine) as session:
                yield session

        app.dependency_overrides[get_db] = database
        self.addCleanup(app.dependency_overrides.clear)
        self.addCleanup(self.engine.dispose)
        self.env = patch.dict(os.environ, {}, clear=True)
        self.env.start()
        self.addCleanup(self.env.stop)
        values = patch('app.ai_triage.dotenv_values', return_value={
            'OPENAI_API_KEY': 'test-key-must-never-be-exposed', 'OPENAI_MODEL': 'gpt-5-mini',
        })
        values.start()
        self.addCleanup(values.stop)
        provider = patch('app.ai_triage.OpenAI', side_effect=AssertionError('Unexpected AI call'))
        self.provider = provider.start()
        self.addCleanup(provider.stop)
        self.client = TestClient(app)
        self.addCleanup(self.client.close)

    def create_request(self):
        response = self.client.post('/properties', json={'name': 'Test flat', 'address': 'Test address'})
        self.assertEqual(response.status_code, 200)
        response = self.client.post('/maintenance', json={
            'property_id': response.json()['id'], 'issue': 'Leaking tap', 'priority': 'low',
        })
        self.assertEqual(response.status_code, 200)
        return response.json()['id']

    def test_offline_workflow_through_approval_and_audit(self):
        config = self.client.get('/triage-config')
        self.assertEqual(config.status_code, 200)
        self.assertEqual(config.json(), dict(mode='rules', model=None, configured=True,
                                            requires_api_credit=False, human_review_required=True))
        self.assertNotIn('test-key', config.text)
        maintenance_id = self.create_request()
        response = self.client.post(f'/maintenance/{maintenance_id}/triage')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['source'], 'rules-v1')
        self.assertEqual(response.json()['suggested_trade'], 'plumber')
        request = self.client.get('/maintenance').json()[0]
        self.assertEqual((request['priority'], request['status']), ('low', 'pending'))
        self.assertEqual(self.client.get('/approvals').json(), [])
        self.assertEqual(self.client.get('/audit-logs').json(), [])

        payload = {'maintenance_request_id': maintenance_id, 'reason': 'Assess the leak'}
        response = self.client.post('/approvals', json=payload)
        self.assertEqual(response.status_code, 200)
        approval_id = response.json()['id']
        self.assertEqual(self.client.post('/approvals', json=payload).status_code, 409)
        self.assertEqual(self.client.post(f'/approvals/{approval_id}/approve').status_code, 200)
        self.assertEqual(self.client.post(f'/approvals/{approval_id}/reject').status_code, 409)
        self.assertEqual(self.client.get('/maintenance').json()[0]['status'], 'approved')
        audit = self.client.get('/audit-logs').json()
        self.assertEqual(len(audit), 1)
        self.assertEqual((audit[0]['resource_id'], audit[0]['new_status']), (approval_id, 'approved'))
        self.assertEqual(len(self.client.get(f'/maintenance/{maintenance_id}/triage').json()), 1)
        self.provider.assert_not_called()

    def test_invalid_mode_does_not_save_suggestions(self):
        maintenance_id = self.create_request()
        with patch.dict(os.environ, {'TRIAGE_MODE': 'typo'}):
            self.assertEqual(self.client.get('/triage-config').status_code, 503)
            self.assertEqual(self.client.post(f'/maintenance/{maintenance_id}/triage').status_code, 503)
        self.assertEqual(self.client.get(f'/maintenance/{maintenance_id}/triage').json(), [])
        self.provider.assert_not_called()

    def test_openai_requires_key_and_reports_configuration_only(self):
        maintenance_id = self.create_request()
        with patch.dict(os.environ, {'TRIAGE_MODE': 'openai', 'OPENAI_API_KEY': ''}):
            config = self.client.get('/triage-config').json()
            self.assertEqual(config['mode'], 'openai')
            self.assertFalse(config['configured'])
            self.assertEqual(self.client.post(f'/maintenance/{maintenance_id}/triage').status_code, 503)
        self.assertEqual(self.client.get(f'/maintenance/{maintenance_id}/triage').json(), [])
        self.provider.assert_not_called()

    def test_unknown_request_does_not_trigger_triage(self):
        self.assertEqual(self.client.post('/maintenance/999/triage').status_code, 404)
        self.assertEqual(self.client.get('/maintenance/999/triage').status_code, 404)
        self.provider.assert_not_called()
