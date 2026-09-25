import pytest
import asyncio
from services.chaos import chaos_manager
from services.agent_commander import agent_commander

@pytest.mark.asyncio
async def test_per_incident_concurrency_locking():
    """Verifies that concurrent investigations for the same incident run safely without racing."""
    chaos_manager.reset()
    chaos_manager.inject_cdn_outage()
    incident_id = "INC-CONCURRENCY-LOCK-1"
    
    # Launch two investigations for the exact same incident ID concurrently
    res1, res2 = await asyncio.gather(
        agent_commander.investigate_and_remediate(
            incident_id=incident_id,
            failure_mode_override="CDN_OUTAGE",
            trigger_source="webhook"
        ),
        agent_commander.investigate_and_remediate(
            incident_id=incident_id,
            failure_mode_override="CDN_OUTAGE",
            trigger_source="webhook"
        )
    )
    
    assert res1.incident_id == incident_id
    assert res2.incident_id == incident_id
    # Second should have returned the cached/idempotent result
    assert res1.remediation_transaction_id == res2.remediation_transaction_id
    assert res1.workflow_status in ("COMPLETED", "RESOLVED", "RECOVERED", "ESCALATED")

