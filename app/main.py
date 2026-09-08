from fastapi import Depends, FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pathlib import Path
from sqlalchemy.orm import Session

from app import models, schemas
from app.database import Base, SessionLocal, engine


app = FastAPI(
    title="PropertyOps AI Agent",
    version="0.1.0",
)

Base.metadata.create_all(bind=engine)

STATIC_DIR = Path(__file__).resolve().parent / "static"
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/", include_in_schema=False)
def dashboard():
    return FileResponse(STATIC_DIR / "index.html")


def get_db():
    db = SessionLocal()

    try:
        yield db
    finally:
        db.close()


@app.get("/health")
def health_check():
    return {
        "status": "ok",
        "service": "propertyops-ai-agent",
    }


@app.get("/triage-config")
def get_triage_config():
    """Report the selected mode without revealing credentials or calling OpenAI."""
    from app.ai_triage import TriageUnavailable, settings, triage_mode

    try:
        mode = triage_mode()
    except TriageUnavailable as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from None
    key, model = settings()
    return {
        "mode": mode,
        "model": model if mode == "openai" else None,
        "configured": mode == "rules" or bool(key),
        "requires_api_credit": mode == "openai",
        "human_review_required": True,
    }


@app.post(
    "/properties",
    response_model=schemas.PropertyResponse,
)
def create_property(
    property_data: schemas.PropertyCreate,
    db: Session = Depends(get_db),
):
    property_record = models.Property(
        name=property_data.name,
        address=property_data.address,
        status=property_data.status,
    )

    db.add(property_record)
    db.commit()
    db.refresh(property_record)

    return property_record


@app.get(
    "/properties",
    response_model=list[schemas.PropertyResponse],
)
def get_properties(
    db: Session = Depends(get_db),
):
    return db.query(models.Property).all()


@app.get(
    "/properties/{property_id}",
    response_model=schemas.PropertyResponse,
)
def get_property(
    property_id: int,
    db: Session = Depends(get_db),
):
    property_record = (
        db.query(models.Property)
        .filter(models.Property.id == property_id)
        .first()
    )

    if property_record is None:
        raise HTTPException(
            status_code=404,
            detail="Property not found",
        )

    return property_record


@app.post(
    "/maintenance",
    response_model=schemas.MaintenanceRequestResponse,
)
def create_maintenance_request(
    maintenance_data: schemas.MaintenanceRequestCreate,
    db: Session = Depends(get_db),
):
    property_record = (
        db.query(models.Property)
        .filter(
            models.Property.id
            == maintenance_data.property_id
        )
        .first()
    )

    if property_record is None:
        raise HTTPException(
            status_code=404,
            detail="Property not found",
        )

    maintenance_record = models.MaintenanceRequest(
        property_id=maintenance_data.property_id,
        issue=maintenance_data.issue,
        priority=maintenance_data.priority,
        status="pending",
    )

    db.add(maintenance_record)
    db.commit()
    db.refresh(maintenance_record)

    return maintenance_record

@app.get(
    "/maintenance",
    response_model=list[schemas.MaintenanceRequestResponse],
)
def get_maintenance_requests(
    db: Session = Depends(get_db),
):
    return db.query(models.MaintenanceRequest).all()

@app.post(
    "/approvals",
    response_model=schemas.ApprovalRequestResponse,
)
def create_approval_request(
    approval_data: schemas.ApprovalRequestCreate,
    db: Session = Depends(get_db),
):
    maintenance_record = (
        db.query(models.MaintenanceRequest)
        .filter(
            models.MaintenanceRequest.id
            == approval_data.maintenance_request_id
        )
        .first()
    )

    if maintenance_record is None:
        raise HTTPException(
            status_code=404,
            detail="Maintenance request not found",
        )

    existing_approval = (
        db.query(models.ApprovalRequest)
        .filter(
            models.ApprovalRequest.maintenance_request_id
            == approval_data.maintenance_request_id,
            models.ApprovalRequest.status == "pending",
        )
        .first()
    )

    if existing_approval is not None:
        raise HTTPException(
            status_code=409,
            detail=(
                "A pending approval already exists "
                "for this maintenance request"
            ),
        )

    approval_record = models.ApprovalRequest(
        maintenance_request_id=(
            approval_data.maintenance_request_id
        ),
        reason=approval_data.reason,
        status="pending",
    )

    db.add(approval_record)
    db.commit()
    db.refresh(approval_record)

    return approval_record


@app.get(
    "/approvals",
    response_model=list[schemas.ApprovalRequestResponse],
)
def get_approvals(
    db: Session = Depends(get_db),
):
    return db.query(models.ApprovalRequest).all()


@app.post(
    "/approvals/{approval_id}/approve",
    response_model=schemas.ApprovalRequestResponse,
)
def approve_request(
    approval_id: int,
    db: Session = Depends(get_db),
):
    approval_record = (
        db.query(models.ApprovalRequest)
        .filter(
            models.ApprovalRequest.id == approval_id
        )
        .first()
    )

    if approval_record is None:
        raise HTTPException(
            status_code=404,
            detail="Approval request not found",
        )

    if approval_record.status != "pending":
        raise HTTPException(
            status_code=409,
            detail=(
                f"Approval has already been "
                f"{approval_record.status}"
            ),
        )

    maintenance_record = (
        db.query(models.MaintenanceRequest)
        .filter(
            models.MaintenanceRequest.id
            == approval_record.maintenance_request_id
        )
        .first()
    )

    if maintenance_record is None:
        raise HTTPException(
            status_code=404,
            detail="Maintenance request not found",
        )

    approval_record.status = "approved"
    maintenance_record.status = "approved"
    audit_record = models.AuditLog(
        action="approval_decision",
        resource_type="approval",
        resource_id=approval_record.id,
        old_status="pending",
        new_status="approved",
        actor="human",
    )

    db.add(audit_record)
    db.commit()

    db.refresh(approval_record)
    db.refresh(maintenance_record)

    return approval_record


@app.post(
    "/approvals/{approval_id}/reject",
    response_model=schemas.ApprovalRequestResponse,
)
def reject_request(
    approval_id: int,
    db: Session = Depends(get_db),
):
    approval_record = (
        db.query(models.ApprovalRequest)
        .filter(
            models.ApprovalRequest.id == approval_id
        )
        .first()
    )

    if approval_record is None:
        raise HTTPException(
            status_code=404,
            detail="Approval request not found",
        )

    if approval_record.status != "pending":
        raise HTTPException(
            status_code=409,
            detail=(
                f"Approval has already been "
                f"{approval_record.status}"
            ),
        )

    maintenance_record = (
        db.query(models.MaintenanceRequest)
        .filter(
            models.MaintenanceRequest.id
            == approval_record.maintenance_request_id
        )
        .first()
    )

    if maintenance_record is None:
        raise HTTPException(
            status_code=404,
            detail="Maintenance request not found",
        )

    approval_record.status = "rejected"
    maintenance_record.status = "rejected"

    audit_record = models.AuditLog(
        action="approval_decision",
        resource_type="approval",
        resource_id=approval_record.id,
        old_status="pending",
        new_status="rejected",
        actor="human",
    )

    db.add(audit_record)
    db.commit()

    db.refresh(approval_record)
    db.refresh(maintenance_record)

    return approval_record

@app.get(
    "/audit-logs",
    response_model=list[schemas.AuditLogResponse],
)
def get_audit_logs(
    db: Session = Depends(get_db),
):
    return db.query(models.AuditLog).all()

@app.post("/maintenance/{maintenance_id}/triage", response_model=schemas.TriageSuggestionResponse)
def triage_maintenance(maintenance_id: int, db: Session = Depends(get_db)):
    from app.triage import suggest_triage
    from app.ai_triage import TriageUnavailable

    maintenance = db.get(models.MaintenanceRequest, maintenance_id)
    if maintenance is None:
        raise HTTPException(status_code=404, detail="Maintenance request not found")
    try:
        result = suggest_triage(maintenance.issue)
    except TriageUnavailable as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from None
    suggestion = models.TriageSuggestion(
        maintenance_request_id=maintenance.id,
        **result,
    )
    db.add(suggestion)
    db.commit()
    db.refresh(suggestion)
    return suggestion


@app.get("/maintenance/{maintenance_id}/triage", response_model=list[schemas.TriageSuggestionResponse])
def get_triage_suggestions(maintenance_id: int, db: Session = Depends(get_db)):
    if db.get(models.MaintenanceRequest, maintenance_id) is None:
        raise HTTPException(status_code=404, detail="Maintenance request not found")
    return (db.query(models.TriageSuggestion)
            .filter(models.TriageSuggestion.maintenance_request_id == maintenance_id)
            .order_by(models.TriageSuggestion.id).all())
