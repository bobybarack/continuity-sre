# CONTINUITY Remediation Baseline

## Repository State
- Branch: `remediation/playbook-refactor`
- Commit SHA: `bd2222719b2247fa12ac3431ada7aa7c089020e8`
- Commit Message: `docs(readme): add prometheus_value_available and verification_source_trusted`

## Test Execution
- Backend Test Suite: 32 passed, 0 failed, 1 warning in 87.01s (`.venv/bin/pytest -q`)
- Concurrency & Stress Tests: Passed (100 simultaneous async workers)
- Live Grafana Cloud Integration: Verified (connected=True, status=HEALTHY, datasources_count>=5, annotations and incidents verified)
- Live Gemini SDK Integration: Verified (`models/gemini-3.7-flash` and function calling tools)

## Frontend State
- Build (`npm run build`): Passed (Compiled successfully, static pages generated)
- Lint (`npm run lint`): Failed with 16 errors and 44 warnings (unescaped quotes in JSX, `@typescript-eslint/no-explicit-any`, comment syntax inside children)
- Fixture Mode: Found query-driven and hardcoded demo numbers in UI components (`$1.45M+`, `100% Resolved`, `SLA Operational (99.98%)`, `mttr_seconds || 4.2`)

## Architecture & Code Issues Identified
1. State Truth: `apply_autonomous_remediation` sets `state.current_mode = "REMEDIATED"` and `is_outage_active = False` before verification executes.
2. Scenario Truth: CDN, DRM, and ISP peering failures all converge to generic Akamai traffic shift.
3. Telemetry Truth: Multiple calls to `generate_current_snapshot()` create fresh random samples instead of reading from a 1 Hz canonical tick.
4. Metric Cardinality: No unbounded metric labels currently in gauges, but Loki pushes and Prometheus pushes need formalization.
5. Deployment: `deploy.sh` specifies `--min-instances 0` and `--max-instances 10`, risking multi-instance split-brain for in-memory state.
6. Security: Mutation endpoints (`/api/chaos/*`, `/api/agent/investigate-and-remediate`) have no authentication guard. CORS allows all origins (`*`).
