import unittest
from unittest.mock import patch

from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app import models
from app.database import Base
from app.main import triage_maintenance, get_triage_suggestions, reject_request
from app.triage import suggest_rules_triage


class TriageTests(unittest.TestCase):
    def test_routing_and_unknown_issue(self):
        for issue, trade in [('BOILER broken', 'heating engineer'), ('Leaking tap', 'plumber'),
                             ('Socket broken', 'electrician'), ('Flooding near boiler', 'urgent assessment'),
                             ('Unknown problem', 'general maintenance'), ('Fireplace paint chipped', 'general maintenance')]:
            with self.subTest(issue=issue):
                self.assertEqual(suggest_rules_triage(issue)['suggested_trade'], trade)

    @patch('app.ai_triage.settings', return_value=('', 'gpt-5-mini'))
    @patch('app.ai_triage.triage_mode', return_value='rules')
    def test_saved_suggestions_preserve_decision_workflow(self, _mode, _settings):
        engine = create_engine('sqlite://')
        Base.metadata.create_all(engine)
        with Session(engine) as db:
            prop = models.Property(name='Test', address='Test')
            db.add(prop)
            db.flush()
            maintenance = models.MaintenanceRequest(property_id=prop.id, issue='Boiler broken', priority='low')
            db.add(maintenance)
            db.flush()
            approval = models.ApprovalRequest(maintenance_request_id=maintenance.id, reason='Test')
            db.add(approval)
            db.commit()
            self.assertEqual(get_triage_suggestions(maintenance.id, db), [])
            suggestion = triage_maintenance(maintenance.id, db)
            db.expire_all()
            self.assertEqual(suggestion.source, 'rules-v1')
            self.assertEqual(suggestion.suggested_priority, 'high')
            self.assertEqual((maintenance.status, maintenance.priority, approval.status), ('pending', 'low', 'pending'))
            self.assertEqual(db.query(models.AuditLog).count(), 0)
            self.assertEqual(len(get_triage_suggestions(maintenance.id, db)), 1)
            self.assertEqual(reject_request(approval.id, db).status, 'rejected')
            self.assertEqual(maintenance.status, 'rejected')
            self.assertEqual(db.query(models.AuditLog).one().new_status, 'rejected')
            for endpoint in (triage_maintenance, get_triage_suggestions):
                with self.assertRaises(HTTPException) as error:
                    endpoint(999, db)
                self.assertEqual(error.exception.status_code, 404)
        engine.dispose()
