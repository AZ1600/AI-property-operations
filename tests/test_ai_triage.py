import os
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from openai import OpenAIError
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.ai_triage import AISuggestion, TriageUnavailable, settings, suggest_ai_triage
from app.main import triage_maintenance
from app.database import Base
from app import models


class AITriageTests(unittest.TestCase):
    @patch('app.ai_triage.dotenv_values', return_value={'OPENAI_API_KEY': 'file-key', 'OPENAI_MODEL': 'file-model'})
    def test_environment_overrides_file(self, _values):
        with patch.dict(os.environ, {'OPENAI_API_KEY': 'env-key', 'OPENAI_MODEL': 'env-model'}):
            self.assertEqual(settings(), ('env-key', 'env-model'))

    @patch('app.ai_triage.OpenAI')
    def test_structured_response_and_refusal(self, factory):
        client = factory.return_value.__enter__.return_value
        parsed = AISuggestion(suggested_priority='medium', suggested_trade='plumber',
                              recommended_action='Request assessment for approval.', rationale='Reported leak.')
        client.responses.parse.return_value = SimpleNamespace(status='completed', output_parsed=parsed)
        result = suggest_ai_triage('Leaking tap', 'test-key', 'gpt-5-mini')
        self.assertEqual(result['source'], 'openai:gpt-5-mini')
        self.assertFalse(client.responses.parse.call_args.kwargs['store'])
        for status in ('completed', 'incomplete'):
            client.responses.parse.return_value = SimpleNamespace(status=status, output_parsed=None)
            with self.assertRaises(TriageUnavailable):
                suggest_ai_triage('test', 'test-key', 'gpt-5-mini')
        client.responses.parse.side_effect = OpenAIError('sensitive provider error')
        with self.assertRaises(TriageUnavailable) as error:
            suggest_ai_triage('test', 'test-key', 'gpt-5-mini')
        self.assertNotIn('sensitive', str(error.exception))

    @patch('app.ai_triage.settings', return_value=('test-key', 'gpt-5-mini'))
    @patch('app.ai_triage.suggest_ai_triage')
    @patch('app.ai_triage.triage_mode', return_value='openai')
    def test_ai_persistence_and_failure_are_non_mutating(self, _mode, generate, _settings):
        engine = create_engine('sqlite://')
        Base.metadata.create_all(engine)
        with Session(engine) as db:
            prop = models.Property(name='Test', address='Test')
            db.add(prop)
            db.flush()
            maintenance = models.MaintenanceRequest(property_id=prop.id, issue='Leaking tap', priority='low')
            db.add(maintenance)
            db.commit()
            generate.return_value = dict(suggested_priority='medium', suggested_trade='plumber',
                                         recommended_action='Request assessment.', rationale='Leak.', source='openai:gpt-5-mini')
            saved = triage_maintenance(maintenance.id, db)
            self.assertEqual(saved.source, 'openai:gpt-5-mini')
            self.assertEqual((maintenance.priority, maintenance.status), ('low', 'pending'))
            self.assertEqual(db.query(models.ApprovalRequest).count(), 0)
            generate.side_effect = TriageUnavailable('AI unavailable')
            with self.assertRaises(HTTPException) as error:
                triage_maintenance(maintenance.id, db)
            self.assertEqual(error.exception.status_code, 503)
            self.assertEqual(db.query(models.TriageSuggestion).count(), 1)
            self.assertEqual(db.query(models.AuditLog).count(), 0)
        engine.dispose()
