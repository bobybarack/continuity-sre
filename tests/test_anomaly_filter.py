import sys
from pathlib import Path
import pytest

# Add backend to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

from services.anomaly_filter import ScalarInnovationFilter, StreamingAnomalyGate, anomaly_gate
from services.telemetry import telemetry_engine
from services.chaos import chaos_manager

def test_scalar_innovation_filter_nominal_vs_outage():
    """Verifies that nominal jitter produces low NIS and an outage jump produces a dramatic NIS spike."""
    filter_inst = ScalarInnovationFilter(initial_state=0.10, q=0.005, r=0.02)

    # 1. Feed nominal samples near 0.10
    for _ in range(10):
        y, nis = filter_inst.step(0.12)
        assert abs(y) < 0.05
        assert nis < 3.84  # Below Chi-squared 95% threshold

    # 2. Sudden outage spike: VPF jumps to 8.5%
    y_spike, nis_spike = filter_inst.step(8.5)
    assert y_spike > 7.0
    assert nis_spike > 10.0  # Massive statistical anomaly

def test_streaming_anomaly_gate_token_savings():
    """Verifies that nominal telemetry suppresses LLM inference and records >90% token savings."""
    gate = StreamingAnomalyGate(nis_threshold=3.84, persistence_ticks=2)

    # Feed 25 nominal ticks
    for _ in range(25):
        eval_res = gate.process_sample(
            vpf_pct=0.15,
            latency_ms=45.0,
            buffer_sec=14.5
        )
        assert eval_res["gate_triggered"] is False

    assert gate.total_ticks == 25
    assert gate.suppressed_ticks == 25
    assert gate.llm_dispatches == 0
    assert eval_res["token_savings_pct"] == 100.0

def test_streaming_anomaly_gate_sustained_violation_triggers():
    """Verifies that an anomaly must be sustained for >= persistence_ticks before triggering."""
    gate = StreamingAnomalyGate(nis_threshold=3.84, persistence_ticks=2)

    # Single transient spike (e.g. measurement noise)
    eval1 = gate.process_sample(vpf_pct=5.0, latency_ms=45.0, buffer_sec=14.5)
    assert eval1["consecutive_violations"] == 1
    assert eval1["gate_triggered"] is False  # Suppressed because not sustained

    # Second consecutive anomaly tick
    eval2 = gate.process_sample(vpf_pct=5.5, latency_ms=45.0, buffer_sec=14.5)
    assert eval2["consecutive_violations"] == 2
    assert eval2["gate_triggered"] is True  # Sustained: triggers agent crew dispatch
    assert gate.llm_dispatches == 1

def test_telemetry_engine_wires_anomaly_gate():
    """Verifies that TelemetryEngine populates NIS and anomaly evaluation in real-time snapshots."""
    chaos_manager.reset()
    snapshot = telemetry_engine.generate_current_snapshot()

    assert hasattr(snapshot, "nis_composite")
    assert snapshot.nis_composite >= 0.0
    assert hasattr(snapshot, "anomaly_gate_triggered")
    assert isinstance(snapshot.anomaly_gate_triggered, bool)
    assert snapshot.token_savings_pct >= 0.0
    assert snapshot.gate_eval is not None
    assert "nis_vpf" in snapshot.gate_eval
