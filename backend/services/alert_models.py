import time
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field

class GrafanaAlertItem(BaseModel):
    status: str = "firing"
    labels: Dict[str, str] = Field(default_factory=dict)
    annotations: Dict[str, str] = Field(default_factory=dict)
    startsAt: Optional[str] = None
    endsAt: Optional[str] = None
    generatorURL: Optional[str] = None
    fingerprint: Optional[str] = None

class GrafanaAlertPayload(BaseModel):
    receiver: Optional[str] = None
    status: str = "firing" # "firing" or "resolved"
    alerts: List[GrafanaAlertItem] = Field(default_factory=list)
    groupLabels: Dict[str, str] = Field(default_factory=dict)
    commonLabels: Dict[str, str] = Field(default_factory=dict)
    commonAnnotations: Dict[str, str] = Field(default_factory=dict)
    externalURL: Optional[str] = None
    version: Optional[str] = "1"
    groupKey: Optional[str] = None

class AlertIngestResponse(BaseModel):
    status: str # "ACCEPTED", "DEDUPLICATED", "IGNORED", "ERROR"
    incident_id: Optional[str] = None
    failure_mode: Optional[str] = None
    severity: Optional[str] = None
    message: str
    timestamp: float = Field(default_factory=time.time)
    workflow_started: bool = False
