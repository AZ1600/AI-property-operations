import unittest
from unittest.mock import patch

from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app import models
from app.database import Base
from app.main import (
    get_triage_suggestions,
    reject_request,
    triage_maintenance,
)
from app.triage import suggest_rules_triage


class TriageTests(unittest.TestCase):
    def test_routing_and_unknown_issue(self):
        test_cases = [
            ("BOILER broken", "heating engineer"),
            ("Leaking tap", "plumber"),
            ("Socket broken", "electrician"),
            ("Flooding near boiler", "urgent assessment"),
            ("Unknown problem", "general maintenance"),
            ("Fireplace paint chipped", "general maintenance"),
        ]

        for issue, trade in test_cases:
            with self.subTest(issue=issue):
                result = suggest_rules_triage(issue)

                self.assertEqual(
                    result["suggested_trade"],
                    trade,
                )

    @patch(
        "app.ai_triage.settings",
        return_value=("", "gpt-5-mini"),
    )
    @patch(
        "app.ai_triage.triage_mode",
        return_value="rules",
    )
    def test_saved_suggestions_preserve_decision_workflow(
        self,
        _mode,
        _settings,
    ):
        engine = create_engine(
            "sqlite://"
        )

        Base.metadata.create_all(
            engine
        )

        test_manager = {
            "actor": "test-manager@example.com",
            "roles": {
                "PropertyOps.Manager"
            },
            "claims": [],
        }

        try:
            with Session(engine) as db:
                prop = models.Property(
                    name="Test",
                    address="Test",
                )

                db.add(prop)
                db.flush()

                maintenance = models.MaintenanceRequest(
                    property_id=prop.id,
                    issue="Boiler broken",
                    priority="low",
                )

                db.add(maintenance)
                db.flush()

                approval = models.ApprovalRequest(
                    maintenance_request_id=maintenance.id,
                    reason="Test",
                )

                db.add(approval)
                db.commit()

                self.assertEqual(
                    get_triage_suggestions(
                        maintenance_id=maintenance.id,
                        db=db,
                        user=test_manager,
                    ),
                    [],
                )

                suggestion = triage_maintenance(
                    maintenance_id=maintenance.id,
                    db=db,
                    user=test_manager,
                )

                db.expire_all()

                self.assertEqual(
                    suggestion.source,
                    "rules-v1",
                )

                self.assertEqual(
                    suggestion.suggested_priority,
                    "high",
                )

                self.assertEqual(
                    (
                        maintenance.status,
                        maintenance.priority,
                        approval.status,
                    ),
                    (
                        "pending",
                        "low",
                        "pending",
                    ),
                )

                self.assertEqual(
                    db.query(
                        models.AuditLog
                    ).count(),
                    0,
                )

                self.assertEqual(
                    len(
                        get_triage_suggestions(
                            maintenance_id=maintenance.id,
                            db=db,
                            user=test_manager,
                        )
                    ),
                    1,
                )

                rejected = reject_request(
                    approval_id=approval.id,
                    db=db,
                    user=test_manager,
                )

                self.assertEqual(
                    rejected.status,
                    "rejected",
                )

                self.assertEqual(
                    maintenance.status,
                    "rejected",
                )

                audit_record = db.query(
                    models.AuditLog
                ).one()

                self.assertEqual(
                    audit_record.new_status,
                    "rejected",
                )

                self.assertEqual(
                    audit_record.actor,
                    "test-manager@example.com",
                )

                with self.assertRaises(
                    HTTPException
                ) as error:
                    triage_maintenance(
                        maintenance_id=999,
                        db=db,
                        user=test_manager,
                    )

                self.assertEqual(
                    error.exception.status_code,
                    404,
                )

                with self.assertRaises(
                    HTTPException
                ) as error:
                    get_triage_suggestions(
                        maintenance_id=999,
                        db=db,
                        user=test_manager,
                    )

                self.assertEqual(
                    error.exception.status_code,
                    404,
                )

        finally:
            engine.dispose()