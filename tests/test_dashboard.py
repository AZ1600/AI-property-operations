"""Verify the dashboard's HTTP integration without modifying saved records."""
import unittest

from fastapi.testclient import TestClient

from app.main import app


class DashboardTests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)
        self.addCleanup(self.client.close)

    def test_home_and_assets_are_served(self):
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)
        self.assertIn('text/html', response.headers['content-type'])
        self.assertIn('PropertyOps', response.text)
        for path, content_type in [('/static/dashboard.css', 'text/css'),
                                   ('/static/dashboard.js', 'javascript')]:
            with self.subTest(path=path):
                asset = self.client.get(path)
                self.assertEqual(asset.status_code, 200)
                self.assertIn(content_type, asset.headers['content-type'])

    def test_private_files_are_not_served(self):
        for path in ['/.env', '/propertyops.db', '/app/main.py', '/static/.env',
                     '/static/%2e%2e/ai_triage.py', '/static/%2e%2e/%2e%2e/.env']:
            with self.subTest(path=path):
                self.assertEqual(self.client.get(path).status_code, 404)

    def test_api_docs_and_health_remain_available(self):
        self.assertEqual(self.client.get('/health').json()['status'], 'ok')
        self.assertEqual(self.client.get('/docs').status_code, 200)
        schema = self.client.get('/openapi.json').json()
        self.assertIn('/maintenance/{maintenance_id}/triage', schema['paths'])
        self.assertNotIn('/', schema['paths'])
