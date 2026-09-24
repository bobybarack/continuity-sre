import time
import asyncio
import logging
from typing import Optional, Dict
from fastapi import APIRouter, Header, Query, Request, HTTPException, status
from services.alert_models import GrafanaAlertPayload, AlertIngestResponse
from services.chaos import chaos_manager, FailureMode
from services.agent_commander import agent_commander
from config import CONTINUITY_DEMO_KEY

logger = logging.getLogger("continuity.alerts")
router = APIRouter(prefix="/api/alerts", tags=["Grafana Cloud Webhooks"])

# Deduplication cache: fingerprint -> timestamp
_DEDUP_CACHE: Dict[str, float] = {}
_DEDUP_TTL_SECONDS = 60.0

def _verify_webhook_auth(
    x_continuity_demo_key: Optional[str] = Header(None, alias="X-Continuity-Demo-Key"),
    x_webhook_secret: Optional[str] = Header(None, alias="X-Webhook-Secret"),
    authorization: Optional[str] = Header(None, alias="Authorization"),
    token: Optional[str] = Query(None),
    secret: Optional[str] = Query(None)
) -> bool:
    expected = CONTINUITY_DEMO_KEY
    if not expected:
        return True

    # Check header tokens
    if x_continuity_demo_key and x_continuity_demo_key == expected:
        return True
    if x_webhook_secret and x_webhook_secret == expected:
        return True
    if authorization:
        parts = authorization.split(" ", 1)
        if len(parts) == 2 and parts[0].lower() == "bearer" and parts[1] == expected:
            return True
        if authorization == expected:
            return True
    # Check query params
    if token and token == expected:
        return True
    if secret and secret == expected:
        return True

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Unauthorized Grafana alert webhook: invalid webhook secret or demo key"
    )

def _classify_failure_mode(labels: Dict[str, str], annotations: Dict[str, str]) -> FailureMode:
    combined = " ".join(list(labels.values()) + list(annotations.values())).upper()
    if any(k in combined for k in ["DRM", "WIDEVINE", "LICENSE", "HANDSHAKE"]):
        return FailureMode.DRM_TIMEOUT
    if any(k in combined for k in ["ISP", "BGP", "TRANSIT", "PEERING", "AS3356", "PACKET"]):
        return FailureMode.ISP_PEERING_DROP
    return FailureMode.CDN_OUTAGE

@router.post("/grafana", response_model=AlertIngestResponse)
async def ingest_grafana_alert(
    payload: GrafanaAlertPayload,
    request: Request,
    x_continuity_demo_key: Optional[str] = Header(None, alias="X-Continuity-Demo-Key"),
    x_webhook_secret: Optional[str] = Header(None, alias="X-Webhook-Secret"),
    authorization: Optional[str] = Header(None, alias="Authorization"),
    token: Optional[str] = Query(None),
    secret: Optional[str] = Query(None)
):
    """Event-driven webhook ingest for Grafana Cloud Alertmanager alerts.
    
    Validates webhook secret, deduplicates alerts, and triggers autonomous
    SRE investigation without requiring human clicks.
    """
    _verify_webhook_auth(
        x_continuity_demo_key=x_continuity_demo_key,
        x_webhook_secret=x_webhook_secret,
        authorization=authorization,
        token=token,
        secret=secret
    )

    if payload.status.lower() == "resolved":
        logger.info(f"[Grafana Webhook] Received resolved notification for group {payload.groupKey}")
        return AlertIngestResponse(
            status="IGNORED",
            message="Alert resolution acknowledged; no autonomous action required",
            workflow_started=False
        )

    # Extract primary alert metadata
    first_alert = payload.alerts[0] if payload.alerts else None
    labels = {**payload.commonLabels, **(first_alert.labels if first_alert else {})}
    annotations = {**payload.commonAnnotations, **(first_alert.annotations if first_alert else {})}

    failure_mode = _classify_failure_mode(labels, annotations)
    severity = labels.get("severity", "CRITICAL").upper()
    region = labels.get("region", "us-east-2")

    # Deduplication fingerprint
    fp = (first_alert.fingerprint if first_alert and first_alert.fingerprint else None) or payload.groupKey or f"{failure_mode.value}:{region}"
    now = time.time()

    # Clean old cache entries
    expired = [k for k, v in _DEDUP_CACHE.items() if now - v > _DEDUP_TTL_SECONDS]
    for k in expired:
        _DEDUP_CACHE.pop(k, None)

    # Check deduplication
    state = chaos_manager.get_state()
    if fp in _DEDUP_CACHE or (state.is_outage_active and state.failure_mode == failure_mode):
        logger.info(f"[Grafana Webhook] Deduplicated alert {fp}; workflow already active")
        return AlertIngestResponse(
            status="DEDUPLICATED",
            incident_id=state.active_incident_id or f"INC-{fp[:8]}",
            failure_mode=failure_mode.value,
            severity=severity,
            message="Duplicate alert suppressed; autonomous remediation or active incident already in progress",
            workflow_started=False
        )

    _DEDUP_CACHE[fp] = now
    incident_id = f"INC-GRAFANA-{int(now)}"

    # Ensure system state reflects outage before autonomous workflow
    if not state.is_outage_active:
        if failure_mode == FailureMode.DRM_TIMEOUT:
            chaos_manager.inject_drm_timeout()
        elif failure_mode == FailureMode.ISP_PEERING_DROP:
            chaos_manager.inject_isp_drop()
        else:
            chaos_manager.inject_cdn_outage()

    # Trigger autonomous background investigation
    asyncio.create_task(
        agent_commander.investigate_and_remediate(
            incident_id=incident_id,
            failure_mode_override=failure_mode.value,
            trigger_source="grafana_alert_webhook"
        )
    )

    logger.info(f"[Grafana Webhook] Autonomous investigation launched for {incident_id} ({failure_mode.value})")

    return AlertIngestResponse(
        status="ACCEPTED",
        incident_id=incident_id,
        failure_mode=failure_mode.value,
        severity=severity,
        message=f"Grafana alert ingested. Autonomous incident commander dispatched for {failure_mode.value}.",
        workflow_started=True
    )
