from sqlalchemy import Column, ForeignKey, Integer, String

from app.database import Base


class Property(Base):
    __tablename__ = "properties"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    address = Column(String, nullable=False)
    status = Column(String, default="active")


class MaintenanceRequest(Base):
    __tablename__ = "maintenance_requests"

    id = Column(Integer, primary_key=True, index=True)
    property_id = Column(
        Integer,
        ForeignKey("properties.id"),
        nullable=False,
    )
    issue = Column(String, nullable=False)
    priority = Column(String, default="medium")
    status = Column(String, default="pending")


class ApprovalRequest(Base):
    __tablename__ = "approval_requests"

    id = Column(Integer, primary_key=True, index=True)
    maintenance_request_id = Column(
        Integer,
        ForeignKey("maintenance_requests.id"),
        nullable=False,
    )
    reason = Column(String, nullable=False)
    status = Column(String, default="pending")

class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    action = Column(String, nullable=False)
    resource_type = Column(String, nullable=False)
    resource_id = Column(Integer, nullable=False)
    old_status = Column(String, nullable=True)
    new_status = Column(String, nullable=True)
    actor = Column(String, nullable=False)

class TriageSuggestion(Base):
    __tablename__ = "triage_suggestions"

    id = Column(Integer, primary_key=True, index=True)
    maintenance_request_id = Column(Integer, ForeignKey("maintenance_requests.id"), nullable=False)
    suggested_priority = Column(String, nullable=False)
    suggested_trade = Column(String, nullable=False)
    recommended_action = Column(String, nullable=False)
    rationale = Column(String, nullable=False)
    source = Column(String, nullable=False)
