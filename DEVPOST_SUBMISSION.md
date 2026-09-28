# CONTINUITY: Autonomous SRE for Hollywood Premiere Nights

> **Tagline:** Closed-loop incident commander for mission-critical streaming reliability. Built with Google Gemini, Google ADK, and Grafana Cloud MCP.  
> **Repository:** [https://github.com/bobybarack/continuity-sre](https://github.com/bobybarack/continuity-sre)  
> **Live Command Center:** [https://continuity-sre.pages.dev](https://continuity-sre.pages.dev)  
> **Backend API:** [https://continuity-api-121300560395.us-central1.run.app](https://continuity-api-121300560395.us-central1.run.app)  
> **Public Grafana Dashboard:** [https://joyfuljasmine1550.grafana.net/public-dashboards/4cf5f0a12aee4d48a3ed18abd2c03db7](https://joyfuljasmine1550.grafana.net/public-dashboards/4cf5f0a12aee4d48a3ed18abd2c03db7)  

---

## 1. Inspiration: The $100M Premiere Night Dilemma

On a Hollywood premiere night, a tier-1 OTT streaming service broadcasts a global tentpole release to millions of concurrent viewers. A 2% spike in Video Playback Failures (VPF) or a 300ms DRM handshake delay triggers immediate subscriber churn, social media outrage, and brand damage.

Traditional broadcast SRE tooling suffers from three fatal architectural flaws:
1. **Blind Remediation:** SRE runbooks issue an infrastructure mutation (e.g., shifting CDN traffic or restarting a key proxy) and immediately declare the incident resolved before downstream clients stabilize.
2. **False Resolutions:** When secondary failover infrastructure is degraded, naive scripts leave viewers stranded on a broken path while Grafana alerts are falsely cleared.
3. **LLM Polling Fatigue & Cost:** Sending 1 Hz continuous telemetry streams to LLM inference endpoints incurs massive latency and quota exhaustion.

We engineered **CONTINUITY** on one non-negotiable operational invariant:

> **"Command Executed ≠ Service Recovered."**  
> An autonomous remediation is not complete until authoritative remote telemetry proves convergence below SLA thresholds. If convergence fails, CONTINUITY executes an automated transactional rollback to the pre-incident snapshot and escalates with cryptographic evidence.

---

## 2. What CONTINUITY Does

CONTINUITY is an autonomous incident commander combining Google Gemini 2.5/3.0 Flash, Google Agent Development Kit (ADK), official Grafana Cloud MCP (1.5.1), and a Next.js 15 command center:

```
┌────────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                       CONTINUITY PIPELINE ARCHITECTURE                                 │
├────────────────────────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                                        │
│   [Canonical 1 Hz Telemetry] ────► [Statistical Innovation Anomaly Gate]                               │
│                                           │ (94.2% Tick Inference Suppression Rate; χ² = 3.84)         │
│                                           ▼                                                            │
│   [Edge Logs & Loki Telemetry] ──► [In-Memory Model Armor Defense Gateway]                             │
│                                           │ (Neutralizes prompt injections; redacts credentials)       │
│                                           ▼                                                            │
│   ┌────────────────────────────────────────────────────────────────────────────────────────────────┐   │
│   │                               4-AGENT SEQUENTIAL CINEMA SRE CREW                               │   │
│   │                                                                                                │   │
│   │   [1st AD: Commander]   ───► [DIT: Signal Scout] ───► [Key Grip: Rigger] ───► [Continuity: Gate]  │   │
│   │   (TriagePackage)            (EvidencePackage)        (RemediationIntent)     (VerificationVerdict)│
│   └───────────────────────────────────────────────────────────────┬────────────────────────────────┘   │
│                                                                   ▼                                    │
│   [High-Risk Blast Radius > 0.80] ─► [Durable SQLite WAL Checkpoint + Supervisor Approval Gate]        │
│                                           │ (Supervisor Approved)                                      │
│                                           ▼                                                            │
│   [ACID Transaction Mutation] ──────► [Closed-Loop Recovery Verification Gate]                         │
│                                           │                                                            │
│                    ┌──────────────────────┴──────────────────────┐                                     │
│                    ▼                                             ▼                                     │
│          [HEALTH GATES PASS]                           [HEALTH GATES FAIL]                             │
│       • Transaction COMMITTED                       • Transaction ROLLED_BACK                          │
│       • SHA-256 RecoveryProof Issued                • Pre-Mutation State Restored                      │
│       • Grafana IRM Incident RESOLVED               • EscalationPackage Compiled                       │
│       • Live Annotation Placed                      • Operator Notified via SSE                        │
└────────────────────────────────────────────────────────────────────────────────────────────────────────┘
```

### Key Architectural Pillars:

- **Mathematical Innovation Anomaly Gate:** Continuous 1D Kalman-style innovation filtering evaluates streaming telemetry ticks against a chi-squared distribution ($\chi^2 = 3.84$). During nominal operations, **94.2% of telemetry ticks are suppressed** from triggering LLM inference, eliminating token churn while reacting instantaneously to genuine SLA anomalies.
- **In-Memory Model Armor Defense Gateway:** Telemetry logs and error streams pass through an in-memory defense-in-depth sanitization layer that neutralizes prompt-injection payloads (instruction overrides, role hijacks, system prompt escapes) and redacts credentials (`glsa_*` service tokens, bearer tokens, API keys) before data reaches Gemini context windows.
- **4-Agent Sequential Cinema SRE Crew:** Implements four separated Google ADK agents mirroring Hollywood studio production separation of duties:
  1. **1st AD (Incident Director):** Scopes incident severity, coordinates roles, and enforces governance (`TriagePackage`).
  2. **DIT (Digital Imaging Technician / Observability Scout):** Executes PromQL and screened LogQL queries via official Grafana MCP (`EvidencePackage`).
  3. **Key Grip (Infrastructure Rigger / Actuator):** Executes scoped transactional traffic shifts or key cluster failovers within ACID boundaries (`RemediationIntent`).
  4. **Continuity (Quality Gate / Recovery Authority):** Re-queries remote Prometheus VPF readback, validates health gates, and holds sole authority to commit or rollback (`VerificationVerdict`).
- **Durable Checkpointing & Container Reboot Recovery:** All incidents, transactions, snapshots, and approval states persist in SQLite configured with Write-Ahead Logging (`PRAGMA journal_mode = WAL`) backed by persistent Docker volumes. The transaction manager automatically reloads active transactions and idempotency indices on startup, surviving container crashes seamlessly.
- **Falsifiable Closed-Loop Verification & Automated Rollback:** When remediation is applied, CONTINUITY polls authoritative telemetry convergence. If metrics fail to restabilize (e.g. in secondary-path degraded scenarios), CONTINUITY rolls back the mutation, restores pristine baseline configuration, and compiles a SHA-256 content-addressed `RecoveryProof` digest.

---

## 3. How We Built It

CONTINUITY was engineered as a full-stack, cloud-native platform:

| Tier | Technologies Used | Key Implementation Details |
|---|---|---|
| **Agent Intelligence** | Google Gemini 2.5 / 3.0 Flash (`google.genai`) | Function calling mode `AUTO`, structured Pydantic schema validation, fallback model cascade. |
| **Agent Orchestration** | Google Agent Development Kit (ADK) | Dedicated `google.adk.agents.Agent` instances, `McpToolset`, structured inter-agent handover pipelines. |
| **Observability** | Grafana Cloud MCP 1.5.1 & Grafana REST | Stdio MCP bridge with REST fallback, PromQL Mimir queries, Loki error streams, and live dashboard annotations. |
| **Backend & Control Plane** | Python 3.11, FastAPI, Uvicorn | Async SSE streaming, mutation write guards (`X-Continuity-Demo-Key`), ACID transaction ledger. |
| **Durability & Persistence** | SQLite 3 WAL (`journal_mode = WAL`) | Checkpoint persistence service, schema migrations, container restart state rehydration. |
| **Frontend Command Center** | Next.js 15, React 19, TypeScript, TailwindCSS | Real-time SSE telemetry feed, interactive HLS video player, HITL supervisor approval modal, crew radio dispatch view. |
| **Streaming Testbed** | High-Fidelity Python Simulator | Modeled multi-CDN egress (Akamai/Fastly), Widevine/FairPlay DRM cluster rotation, and BGP transit routes. |

---

## 4. Empirical Verification & Benchmark Results

CONTINUITY has been subjected to rigorous engineering verification across unit, integration, and scenario benchmark suites:

### Test Suite Summary:
- **164 Passing Tests** across core unit suites, MCP integration, persistence, adversarial prompt injection resilience, and HITL checkpoint recovery.
- **0 Test Failures** across full workspace regression runs.

### Authoritative Scenario Benchmark (20 Automated Runs):

| Failure Scenario | Simulated Intervention | Expected Outcome | Benchmark Success | Mean MTTR | False Resolutions |
|---|---|---|:---:|:---:|:---:|
| **Primary CDN Edge Outage** | `SHIFT_TRAFFIC_TO_AKAMAI` | Egress rebalanced; VPF $\le$ 0.5% | 4/5 (80%) | 5.77 s | **0** |
| **DRM Key Cluster Timeout** | `FAILOVER_DRM_KEY_CLUSTER` | Auth rotated; Handshake $\le$ 250ms | 5/5 (100%) | 5.82 s | **0** |
| **ISP Peering Route Drop** | `REROUTE_BGP_TRANSIT` | Secondary transit routed; Bitrate $\ge$ 10 Mbps | 5/5 (100%) | 5.75 s | **0** |
| **Secondary Path Degraded** | CDN failover into degraded egress | Verification fails $\rightarrow$ Automated Rollback | 5/5 (100% Rollback) | 35.37 s (Timeout) | **0** |

**Zero False Resolutions:** Across all 20 benchmark runs, CONTINUITY maintained an invariant record of **0 false resolutions**. When remediation succeeded, it was verified against remote telemetry; when secondary infrastructure was degraded, it consistently aborted, rolled back, and escalated.

---

## 5. Scope & Reality Transparency

To ensure complete production integrity and audit transparency, the following scope boundaries are explicitly documented:
- **High-Fidelity Simulation Testbed:** CDN egress shifts, DRM key rotation, and BGP transit switches are executed against a high-fidelity local streaming simulation testbed. This repository does not hold production Akamai EdgeGrid, Fastly, or Tier-1 transit API credentials.
- **In-Memory Model Armor Gateway:** The log screening layer implements Google Model Armor defense-in-depth patterns using compiled regex heuristic sanitizers, canary tokens, and credential masks in memory without external cloud API dependencies.
- **Inference Efficiency Metric:** The 94.2% efficiency figure represents the **Telemetry Tick Inference Suppression Rate** achieved by the statistical innovation gate during nominal playback, preventing redundant model calls on healthy ticks.
- **Demo Write Guard:** The `X-Continuity-Demo-Key` header provides demo write-guard friction on mutation endpoints against web crawlers and accidental internet traffic; enterprise deployments would integrate OAuth2/OIDC supervisor IAM.

---

## 6. What's Next for CONTINUITY

1. **Production CDN Control Plane Adapters:** Integrate live Akamai EdgeGrid and Fastly API control planes with hardware-enforced rate limiting.
2. **Distributed Cloud SQL PostgreSQL Storage:** Scale the SQLite WAL checkpoint store to multi-region Cloud SQL PostgreSQL for active-active high availability.
3. **Enterprise SSO / IAM Supervisor Governance:** Replace demo write keys with fine-grained Okta / Google Cloud IAM supervisor authorization tokens.
