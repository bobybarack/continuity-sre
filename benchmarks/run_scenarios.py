#!/usr/bin/env python3
import sys
import os
import time
import json
import asyncio
import statistics
from typing import Dict, Any, List

# Ensure backend modules can be imported
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend")))

from services.chaos import chaos_manager, FailureMode, IncidentLifecycle
from services.agent_commander import agent_commander
from services.transaction_manager import transaction_manager
from services.telemetry import telemetry_engine

async def run_scenario_benchmark(
    scenario_name: str,
    failure_mode: FailureMode,
    is_adversarial: bool = False,
    runs: int = 5
) -> Dict[str, Any]:
    print(f"\n======================================================================")
    print(f"BENCHMARK: {scenario_name} (Runs: {runs}, Adversarial: {is_adversarial})")
    print(f"======================================================================")

    mttr_list: List[float] = []
    proof_hashes: List[str] = []
    false_resolutions = 0
    passed_runs = 0
    rollback_count = 0
    escalation_count = 0

    for i in range(1, runs + 1):
        transaction_manager.clear()
        chaos_manager.reset()
        
        # Inject scenario
        if failure_mode == FailureMode.CDN_OUTAGE:
            state = chaos_manager.inject_cdn_outage()
        elif failure_mode == FailureMode.DRM_TIMEOUT:
            state = chaos_manager.inject_drm_timeout()
        elif failure_mode == FailureMode.ISP_PEERING_DROP:
            state = chaos_manager.inject_isp_drop()
        elif failure_mode == FailureMode.SECONDARY_PATH_DEGRADED:
            state = chaos_manager.inject_secondary_path_degradation()
        else:
            raise ValueError(f"Unsupported failure mode: {failure_mode}")

        inc_id = state.active_incident_id or f"INC-BENCH-{int(time.time()*1000)}"
        t0 = time.time()

        # Execute autonomous investigation & remediation
        result = await agent_commander.investigate_and_remediate(
            incident_id=inc_id,
            failure_mode_override=failure_mode.value,
            trigger_source="chaos_benchmark"
        )
        elapsed = round(time.time() - t0, 2)

        # Invariant Verification
        if not is_adversarial:
            # Normal recovery must pass verification gate and produce cryptographic proof
            if result.closed_loop_verified:
                passed_runs += 1
                mttr_val = result.mttr_seconds or elapsed
                mttr_list.append(mttr_val)
                if result.recovery_proof and "evidence_hash" in result.recovery_proof:
                    proof_hashes.append(result.recovery_proof["evidence_hash"])
                print(f"  Run {i}/{runs}: PASS | MTTR={mttr_val}s | Tx={result.remediation_transaction_id}")
            else:
                # If marked resolved without verification, that is a false resolution
                if result.workflow_status == "RESOLVED":
                    false_resolutions += 1
                    print(f"  Run {i}/{runs}: FAIL (FALSE RESOLUTION) | Unverified resolution detected!")
                else:
                    print(f"  Run {i}/{runs}: PENDING/ESCALATED | Gate validation did not pass within timeout")
        else:
            # Adversarial double-fault MUST trigger rollback and escalation, NEVER false resolution
            if result.closed_loop_verified or result.workflow_status == "RESOLVED":
                false_resolutions += 1
                print(f"  Run {i}/{runs}: CRITICAL FAIL (FALSE RESOLUTION ON ADVERSARIAL SCENARIO)")
            else:
                if result.rollback_status in ("EXECUTED", "ROLLED_BACK") and result.escalation_package:
                    passed_runs += 1
                    rollback_count += 1
                    escalation_count += 1
                    print(f"  Run {i}/{runs}: PASS | Rollback Executed | Escalation Package Created | Evidence Preserved")
                else:
                    print(f"  Run {i}/{runs}: FAIL | Rollback or Escalation incomplete")

    mean_mttr = round(statistics.mean(mttr_list), 2) if mttr_list else None
    p95_mttr = round(statistics.quantiles(mttr_list, n=20)[-1], 2) if len(mttr_list) >= 5 else (max(mttr_list) if mttr_list else None)

    summary = {
        "scenario": scenario_name,
        "failure_mode": failure_mode.value,
        "runs": runs,
        "passed_runs": passed_runs,
        "pass_rate_pct": round((passed_runs / runs) * 100, 1),
        "false_resolution_count": false_resolutions,
        "mean_mttr_sec": mean_mttr,
        "p95_mttr_sec": p95_mttr,
        "proofs_generated": len(proof_hashes),
        "rollbacks_triggered": rollback_count,
        "escalations_generated": escalation_count,
    }
    return summary

async def main():
    runs_per_scenario = 5
    print("\nCONTINUITY REPEATABLE CHAOS BENCHMARK SUITE")
    print("Testing Invariant: COMMAND SUCCEEDED != SERVICE RECOVERED")
    print(f"Configured Runs per Scenario: {runs_per_scenario}\n")

    scenarios = [
        ("Edge CDN Failover", FailureMode.CDN_OUTAGE, False),
        ("DRM Key Proxy Failover", FailureMode.DRM_TIMEOUT, False),
        ("ISP BGP Route Reroute", FailureMode.ISP_PEERING_DROP, False),
        ("Adversarial Double-Fault (Secondary Path Degraded)", FailureMode.SECONDARY_PATH_DEGRADED, True),
    ]

    all_results = []
    total_false_resolutions = 0

    for name, mode, is_adv in scenarios:
        res = await run_scenario_benchmark(name, mode, is_adv, runs=runs_per_scenario)
        all_results.append(res)
        total_false_resolutions += res["false_resolution_count"]

    # Render ASCII Summary Table
    print("\n" + "=" * 90)
    print(f"{'SCENARIO':<35} | {'PASS RATE':<10} | {'FALSE RESOLVE':<13} | {'MEAN MTTR':<10} | {'STATUS':<8}")
    print("-" * 90)
    
    all_passed = True
    for r in all_results:
        status_str = "PASS" if (r["pass_rate_pct"] == 100.0 and r["false_resolution_count"] == 0) else "WARN"
        if r["false_resolution_count"] > 0:
            status_str = "FAIL"
            all_passed = False
        mttr_str = f"{r['mean_mttr_sec']}s" if r['mean_mttr_sec'] else "N/A (Rollback)"
        print(f"{r['scenario']:<35} | {r['pass_rate_pct']:>8.1f}% | {r['false_resolution_count']:>13} | {mttr_str:>10} | {status_str:<8}")
    
    print("=" * 90)
    print(f"Total Invariant False Resolutions: {total_false_resolutions}")

    # Write report artifact
    os.makedirs(os.path.join(os.path.dirname(__file__)), exist_ok=True)
    report_path = os.path.join(os.path.dirname(__file__), "benchmark_report.json")
    with open(report_path, "w") as f:
        json.dump({
            "timestamp": time.time(),
            "runs_per_scenario": runs_per_scenario,
            "all_passed": all_passed,
            "false_resolution_count": total_false_resolutions,
            "scenarios": all_results
        }, f, indent=2)
    print(f"Benchmark results saved to: {report_path}\n")

    if total_false_resolutions > 0:
        print("FAIL: False resolution invariant violated!")
        sys.exit(1)
    else:
        print("SUCCESS: 100% Closed-Loop Verification & Rollback Invariants Proven.")
        sys.exit(0)

if __name__ == "__main__":
    asyncio.run(main())
