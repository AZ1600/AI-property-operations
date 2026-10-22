"""Exercise real role dependencies with synthetic Azure principal headers.

These headers model the trusted Easy Auth bridge, not Entra token validation.
Every test gets a fresh in-memory database and no auth dependency override.
"""

import base64
import json

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app import models
from app.auth import get_current_user
from app.database import Base
from app.main import app, get_db


def encoded(value):
    return base64.b64encode(json.dumps(value).encode()).decode()


def identity(role="PropertyOps.User", actor="operator@example.test"):
    claims = [{"typ": "preferred_username", "val": actor}]
    if role is not None:
        claims.append({"typ": "roles", "val": role})
    return {"X-MS-CLIENT-PRINCIPAL": encoded({"auth_typ": "aad", "claims": claims})}


@pytest.fixture
def workspace():
    engine = create_engine(
        "sqlite://", poolclass=StaticPool,
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        property_record = models.Property(name="Test flat", address="Synthetic address")
        db.add(property_record)
        db.flush()
        maintenance = models.MaintenanceRequest(
            property_id=property_record.id, issue="Leaking tap", priority="low",
        )
        db.add(maintenance)
        db.flush()
        approval = models.ApprovalRequest(
            maintenance_request_id=maintenance.id, reason="Review repair",
        )
        db.add(approval)
        db.commit()
        ids = {"property": property_record.id, "maintenance": maintenance.id, "approval": approval.id}

    def database():
        with Session(engine) as db:
            yield db

    previous_overrides = app.dependency_overrides.copy()
    app.dependency_overrides.pop(get_current_user, None)
    app.dependency_overrides[get_db] = database
    try:
        with TestClient(app, raise_server_exceptions=False) as client:
            yield client, engine, ids
    finally:
        app.dependency_overrides.clear()
        app.dependency_overrides.update(previous_overrides)
        engine.dispose()


PROTECTED_REQUESTS = [
    ("GET", "/me", None),
    ("GET", "/properties", None),
    ("GET", "/properties/1", None),
    ("POST", "/properties", {"name": "Test", "address": "Test"}),
    ("GET", "/maintenance", None),
    ("POST", "/maintenance", {"property_id": 1, "issue": "Test"}),
    ("POST", "/maintenance/1/triage", None),
    ("GET", "/maintenance/1/triage", None),
    ("GET", "/approvals", None),
    ("POST", "/approvals", {"maintenance_request_id": 1, "reason": "Test"}),
    ("POST", "/approvals/1/approve", None),
    ("POST", "/approvals/1/reject", None),
    ("GET", "/audit-logs", None),
]


@pytest.mark.parametrize("method,path,payload", PROTECTED_REQUESTS)
def test_missing_identity_is_401_without_writes(workspace, method, path, payload):
    client, engine, _ = workspace
    response = client.request(method, path, json=payload)
    assert response.status_code == 401
    with Session(engine) as db:
        assert db.query(models.Property).count() == 1
        assert db.query(models.MaintenanceRequest).one().status == "pending"
        assert db.query(models.ApprovalRequest).one().status == "pending"
        assert db.query(models.TriageSuggestion).count() == 0
        assert db.query(models.AuditLog).count() == 0


INVALID_HEADERS = [
    "not-base64!", "====", encoded(None), encoded([]), encoded("manager"),
    encoded({"claims": None}), encoded({"claims": {}}), encoded({"claims": "roles"}),
    encoded({"claims": [None]}), encoded({"claims": ["PropertyOps.Manager"]}),
    encoded({"claims": [{"typ": 7, "val": "PropertyOps.Manager"}]}),
    encoded({"claims": [{"typ": "roles", "val": ["PropertyOps.Manager"]}]}),
    encoded({"claims": [], "name": {"actor": "manager"}}),
    base64.b64encode(b"\xff").decode(),
    base64.b64encode(b"{invalid-json").decode(),
]


@pytest.mark.parametrize("header", INVALID_HEADERS, ids=range(len(INVALID_HEADERS)))
def test_malformed_identity_is_401_not_500(workspace, header):
    client, _, _ = workspace
    response = client.get("/me", headers={"X-MS-CLIENT-PRINCIPAL": header})
    assert response.status_code == 401
    assert response.json() == {"detail": "Invalid authentication information"}


@pytest.mark.parametrize("role", [None, "unknown", "propertyops.manager"])
def test_unassigned_or_unknown_role_is_403(workspace, role):
    client, _, _ = workspace
    assert client.get("/properties", headers=identity(role)).status_code == 403


@pytest.mark.parametrize("principal,actor", [
    ({"claims": [{"typ": "preferred_username", "val": "preferred@example.test"}], "name": "Fallback"}, "preferred@example.test"),
    ({"claims": [{"typ": "email", "val": "email@example.test"}]}, "email@example.test"),
    ({"claims": [{"typ": "upn", "val": "upn@example.test"}]}, "upn@example.test"),
    ({"claims": [], "name": "Fallback"}, "Fallback"),
    ({"claims": []}, "authenticated-user"),
])
def test_valid_principal_actor_formats_remain_supported(workspace, principal, actor):
    client, _, _ = workspace
    response = client.get("/me", headers={"X-MS-CLIENT-PRINCIPAL": encoded(principal)})
    assert response.status_code == 200
    assert response.json() == {"actor": actor, "roles": []}


@pytest.mark.parametrize("decision", ["approve", "reject"])
def test_user_cannot_decide_or_forge_manager_in_body(workspace, decision):
    client, engine, ids = workspace
    response = client.post(
        f"/approvals/{ids['approval']}/{decision}", headers=identity(),
        json={"roles": ["PropertyOps.Manager"], "actor": "forged-manager"},
    )
    assert response.status_code == 403
    with Session(engine) as db:
        assert db.get(models.ApprovalRequest, ids["approval"]).status == "pending"
        assert db.get(models.MaintenanceRequest, ids["maintenance"]).status == "pending"
        assert db.query(models.AuditLog).count() == 0


@pytest.mark.parametrize("role", ["PropertyOps.User", "PropertyOps.Manager"])
def test_user_and_manager_can_create_normal_workflow(workspace, role):
    client, _, _ = workspace
    headers = identity(role)
    response = client.post("/properties", headers=headers, json={"name": "New flat", "address": "Test"})
    assert response.status_code == 200
    property_id = response.json()["id"]
    assert client.get(f"/properties/{property_id}", headers=headers).status_code == 200
    response = client.post("/maintenance", headers=headers, json={"property_id": property_id, "issue": "Boiler broken"})
    assert response.status_code == 200
    response = client.post("/approvals", headers=headers, json={"maintenance_request_id": response.json()["id"], "reason": "Human review"})
    assert response.status_code == 200
    assert response.json()["status"] == "pending"


@pytest.mark.parametrize("decision,status", [("approve", "approved"), ("reject", "rejected")])
def test_manager_decision_records_trusted_actor_and_consistent_status(workspace, decision, status):
    client, engine, ids = workspace
    response = client.post(
        f"/approvals/{ids['approval']}/{decision}",
        headers=identity("PropertyOps.Manager", "reviewer@example.test"),
        json={"actor": "forged-actor"},
    )
    assert response.status_code == 200
    assert response.json()["status"] == status
    with Session(engine) as db:
        assert db.get(models.MaintenanceRequest, ids["maintenance"]).status == status
        audit = db.query(models.AuditLog).one()
        assert (audit.actor, audit.old_status, audit.new_status) == ("reviewer@example.test", "pending", status)
        assert (audit.resource_type, audit.resource_id) == ("approval", ids["approval"])


@pytest.mark.parametrize("first", ["approve", "reject"])
@pytest.mark.parametrize("second", ["approve", "reject"])
def test_repeat_or_conflicting_decision_is_409_without_extra_audit(workspace, first, second):
    client, engine, ids = workspace
    headers = identity("PropertyOps.Manager")
    assert client.post(f"/approvals/{ids['approval']}/{first}", headers=headers).status_code == 200
    assert client.post(f"/approvals/{ids['approval']}/{second}", headers=headers).status_code == 409
    status = "approved" if first == "approve" else "rejected"
    with Session(engine) as db:
        assert db.get(models.ApprovalRequest, ids["approval"]).status == status
        assert db.get(models.MaintenanceRequest, ids["maintenance"]).status == status
        assert db.query(models.AuditLog).count() == 1


@pytest.mark.parametrize("decision", ["approve", "reject"])
def test_database_audit_failure_rolls_back_decision_and_allows_retry(workspace, decision):
    client, engine, ids = workspace
    with engine.begin() as connection:
        connection.execute(text("""
            CREATE TRIGGER reject_test_audit BEFORE INSERT ON audit_logs
            BEGIN SELECT RAISE(ABORT, 'synthetic audit failure'); END
        """))
    headers = identity("PropertyOps.Manager")
    assert client.post(f"/approvals/{ids['approval']}/{decision}", headers=headers).status_code == 500
    with Session(engine) as db:
        assert db.get(models.ApprovalRequest, ids["approval"]).status == "pending"
        assert db.get(models.MaintenanceRequest, ids["maintenance"]).status == "pending"
        assert db.query(models.AuditLog).count() == 0
    with engine.begin() as connection:
        connection.execute(text("DROP TRIGGER reject_test_audit"))
    assert client.post(f"/approvals/{ids['approval']}/{decision}", headers=headers).status_code == 200
    with Session(engine) as db:
        assert db.query(models.AuditLog).count() == 1


def test_duplicate_pending_approval_does_not_create_second_record(workspace):
    client, engine, ids = workspace
    response = client.post("/approvals", headers=identity(), json={"maintenance_request_id": ids["maintenance"], "reason": "Duplicate"})
    assert response.status_code == 409
    with Session(engine) as db:
        assert db.query(models.ApprovalRequest).count() == 1


@pytest.mark.parametrize("decision", ["approve", "reject"])
def test_unknown_approval_is_404_without_side_effects(workspace, decision):
    client, engine, _ = workspace
    assert client.post(f"/approvals/999/{decision}", headers=identity("PropertyOps.Manager")).status_code == 404
    with Session(engine) as db:
        assert db.query(models.AuditLog).count() == 0
        assert db.query(models.ApprovalRequest).one().status == "pending"


@pytest.mark.parametrize("mode", ["rules", "openai"])
def test_triage_suggestion_does_not_make_a_human_decision(workspace, monkeypatch, mode):
    from app import ai_triage

    monkeypatch.setenv("TRIAGE_MODE", mode)
    monkeypatch.setenv("OPENAI_API_KEY", "synthetic-test-key")
    monkeypatch.setattr(ai_triage, "suggest_ai_triage", lambda *args: {
        "suggested_priority": "high", "suggested_trade": "plumber",
        "recommended_action": "Request a repair assessment.",
        "rationale": "Needs human review.", "source": "openai:test-model",
    })
    client, engine, ids = workspace
    response = client.post(f"/maintenance/{ids['maintenance']}/triage", headers=identity())
    assert response.status_code == 200
    assert response.json()["source"] == ("rules-v1" if mode == "rules" else "openai:test-model")
    with Session(engine) as db:
        assert db.get(models.MaintenanceRequest, ids["maintenance"]).status == "pending"
        assert db.get(models.ApprovalRequest, ids["approval"]).status == "pending"
        assert db.query(models.AuditLog).count() == 0
        assert db.query(models.TriageSuggestion).count() == 1
