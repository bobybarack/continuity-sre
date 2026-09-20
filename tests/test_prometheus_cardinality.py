import pytest
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

from services.telemetry import telemetry_engine, PREMIERE_REGISTRY, generate_latest
from services.chaos import chaos_manager

def test_prometheus_labels_are_strictly_bounded():
    """Verifies that Prometheus metrics do not contain unbounded labels such as incident_id."""
    # 1. Inject an incident with an active incident ID
    chaos_manager.inject_cdn_outage()
    assert chaos_manager.get_state().active_incident_id is not None
    
    # 2. Trigger tick to serialize metrics into registry
    telemetry_engine._tick()
    
    # 3. Export OpenMetrics exposition format
    metrics_text = generate_latest(PREMIERE_REGISTRY).decode("utf-8")
    
    # 4. Assert that 'incident_id' does not appear in metric label names
    assert 'incident_id=' not in metrics_text
    
    # 5. Assert that ott_incident_active_status uses bounded labels (chaos_mode, region)
    region = chaos_manager.get_state().affected_region
    assert f'ott_incident_active_status{{chaos_mode="CDN_OUTAGE",region="{region}"}} 1.0' in metrics_text
    
    # Reset
    chaos_manager.reset_to_normal()
    telemetry_engine._tick()
