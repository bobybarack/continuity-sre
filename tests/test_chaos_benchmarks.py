import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import pytest
from benchmarks.run_scenarios import run_scenario_benchmark
from services.chaos import FailureMode

@pytest.mark.asyncio
async def test_benchmark_cdn_scenario_integrity():
    """Validates that running a benchmark iteration adheres to zero false resolutions."""
    summary = await run_scenario_benchmark("Test CDN Outage", FailureMode.CDN_OUTAGE, is_adversarial=False, runs=1)
    assert summary["false_resolution_count"] == 0
    assert summary["runs"] == 1

@pytest.mark.asyncio
async def test_benchmark_adversarial_scenario_integrity():
    """Validates that running an adversarial benchmark iteration triggers rollback without false resolution."""
    summary = await run_scenario_benchmark("Test Adversarial", FailureMode.SECONDARY_PATH_DEGRADED, is_adversarial=True, runs=1)
    assert summary["false_resolution_count"] == 0
    assert summary["rollbacks_triggered"] == 1
    assert summary["escalations_generated"] == 1
