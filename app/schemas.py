from pydantic import BaseModel


class PropertyCreate(BaseModel):
    name: str
    address: str
    status: str = "active"


class PropertyResponse(BaseModel):
    id: int
    name: str
    address: str
    status: str

    class Config:
        from_attributes = True


class MaintenanceRequestCreate(BaseModel):
    property_id: int
    issue: str
    priority: str = "medium"


class MaintenanceRequestResponse(BaseModel):
    id: int
    property_id: int
    issue: str
    priority: str
    status: str

    class Config:
        from_attributes = True



class ApprovalRequestCreate(BaseModel):
    maintenance_request_id: int
    reason: str


class ApprovalRequestResponse(BaseModel):
    id: int
    maintenance_request_id: int
    reason: str
    status: str

    class Config:
        from_attributes = True

class AuditLogResponse(BaseModel):
    id: int
    action: str
    resource_type: str
    resource_id: int
    old_status: str | None
    new_status: str | None
    actor: str

    class Config:
        from_attributes = True

class TriageSuggestionResponse(BaseModel):
    id: int
    maintenance_request_id: int
    suggested_priority: str
    suggested_trade: str
    recommended_action: str
    rationale: str
    source: str

    class Config:
        from_attributes = True
