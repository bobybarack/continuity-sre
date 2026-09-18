---

## Video direction

- palette system: Use `frame.md` roles exactly: canvas `#FFFFFF`, ink `#111827`, operational accent `#009966`, pale mint tint and border roles, and `#dc2626` only for outage evidence. Display, body, numerals, and chrome all use Geist by their defined roles.
- presenter system: The HeyGen Avatar v5 presenter is a compositor-level picture-in-picture carrier visible for the full film. Use a vertical rounded crop at roughly one-fifth of frame width with a soft neutral drop shadow as the sole shadow exception. It alternates right for Frames 1–4, left for Frames 5–7, and right for Frames 8–10; each shot places its primary readable content away from the presenter while backgrounds remain full-frame.
- motion grammar: The film current is LEFT. Ordinary boundaries use cut-the-curve LEFT; zoom-through is reserved for chapter reveals, and one rack-focus blur-cut marks the healthy-to-outage state change. Entrances settle on long-tail `power3`/`power4` motion, reveals land on the spoken cue across the later half of each frame, and all motion is deterministic and seek-safe.
- sustained-motion routes: Frames 1–3 and 9–10 use staged reveals or animated sequences; Frames 4–5 use sequenced UI life and a cursor-led causal action; Frame 6 uses diegetic agent working-state theater; Frame 7 uses an intentional camera journey; Frame 8 uses a same-anchor evidence-to-receipt pivot.
- rhythm: Scale hit, measured hold, controlled build, evidence tour, incident peak, reasoning suspense, failover release, proof hold, production disclosure, brand resolve. Frame 4 is the first deliberate breather; Frame 8 schedules a short stillness-before-proof comma; the final lockup holds dead still.
- caption model: Verbatim rail captions are an overlay, not a reserved band. Compose on the true frame center and use the full canvas; only keep critical small text out of the bottom-center caption line. Promote at most one scarce embedded peak per major chapter.
- negative list: No generic browser chrome, real captured cursor, third-party movie title, credential, unverified live claim, second accent hue, stock AI gradient, pie chart, dashboard wall, bounce-first entrance, idle breathing, independent floating cards, front-loaded slideshow timing, or crossfade seam.
format: 1920x1080
duration: 140s
message: "CONTINUITY turns live Grafana telemetry into an autonomous, evidence-backed remediation loop that protects premiere-night streams before viewers abandon them."
arc: "PAS with a live demo loop: stakes, failure, autonomous response, proof, accountability, production disclosure, close"
audience: "Google Cloud and Grafana Labs hackathon judges, principal architects, and technical evaluators"
mode: autonomous
music: "cinematic minimal technology pulse, restrained tension through the incident, confident resolution at the close"
captions: yes
---

## Frame 1 — Four Million Screens

- scene: A single viewer count escalates into a wall of playback windows before one buffer indicator stops the room.
- voiceover: "Premiere night. Four point two eight million viewers press play. Then a transit peer collapses. Screens freeze, buffers empty, and every second becomes visible."
- duration: 10s
- poster: 6s
- transition_in: cut
- status: animated
 - src: compositions/frames/01-four-million-screens.html
- type: hook
- persuasion: Stakes through scale
- beat: anticipation to alarm
- blueprint: dataviz-countup
- asset_candidates:

- focal: none — the viewer count is constructed typography and data motion
- roles: none
- sfx: low theater-room swell, restrained data ticks, single buffer-stop impact

Adapt: keep the count-up-and-spread signature; replace generic icons with playback tiles and make the transit failure the force that arrests the system.
Scene 1 (0.0–2.2s): `PREMIERE NIGHT` arrives alone in the upper-left via a waterfall entry, then a large center-left viewer counter starts at zero; asymmetric 70/30 around the presenter, three depth layers, no other claim yet.
Scene 2 (2.2–5.2s): on “four point two eight million,” the counter climbs to `4.28M` with value-scaled count-up (`counting-dynamic-scale`) while playback tiles expand from its center into a full-frame field; the number and field land as one event.
Scene 3 (5.2–8.0s): when the transit peer collapses, a sharp red route fracture draws across the field (`svg-path-draw`); tile buffer rings drain in a sequenced wave (`stat-bars-and-fills`) and the formerly advancing UI freezes on its spoken cue.
Scene 4 (8.0–10.0s): `EVERY SECOND BECOMES VISIBLE` builds in two left-anchored lines; the stopped field holds without breathing while a single red buffer indicator retains subtle diegetic jitter.

narrativeRole: Make the incident human before introducing infrastructure.
keyMessage: A premiere outage is an audience event, not merely a graph anomaly.

## Frame 2 — The Buffer Is the Clock

- scene: Three failure signals accumulate around a shrinking buffer countdown: VPF above 5%, latency above 400ms, and repeated 502 responses.
- voiceover: "A five-oh-two storm does not wait for a war room. Playback failures jump beyond five percent. Edge latency passes four hundred milliseconds. Forward buffer drops toward three seconds. Viewers do what dashboards cannot stop: they leave."
- duration: 14s
- poster: 9s
- transition_in: cut-the-curve LEFT
- status: animated
 - src: compositions/frames/02-buffer-clock.html
- type: pain_point
- persuasion: Pain agitation with measured evidence
- beat: urgency
- blueprint: dataviz-countup
- asset_candidates:

- focal: none — the buffer countdown and incident metrics are constructed data instruments
- roles: none
- sfx: clipped error ticks, low sub pulse, restrained downward riser

Adapt: keep the push-through data-instrument signature; use the viewer buffer as the clock and traverse three incident facts before the human consequence.
Scene 1 (0.0–3.1s): a large radial buffer instrument establishes left of the presenter; its ring drains toward `3.5s` as the spoken “five-oh-two storm” stamps once across its center (`stat-bars-and-fills`, `discrete-text-sequence`), layered-depth with one dominant clock.
Scene 2 (3.1–6.3s): the camera pushes through the ring into a single failure-rate card; `5.07% VPF` counts into place (`counting-dynamic-scale`) and crosses a thin SLA rule exactly as the narration says “beyond five percent.”
Scene 3 (6.3–9.4s): a lateral cut-the-curve inside the shot carries the eye to `409.1 ms EDGE LATENCY`; one vertical severity bar fills red (`stat-bars-and-fills`) while the earlier card recedes but remains context.
Scene 4 (9.4–11.7s): a Loki evidence strip types `HTTP 502 · 68% PACKET LOSS` (`discrete-text-sequence`) and locks below the instruments; the camera is now static and each value is readable.
Scene 5 (11.7–14.0s): playback tiles peel away left in three measured groups as `VIEWERS LEAVE` lands near-black at center-left (`kinetic-beat-slam`); the data holds behind it with no idle drift.

narrativeRole: Convert the outage into a race against the viewer's remaining buffer.
keyMessage: Human triage starts too late for stream continuity.

## Frame 3 — Closed Loop

- scene: CONTINUITY assembles at the center of a four-stage loop: observe, reason, act, prove.
- voiceover: "This is CONTINUITY: an autonomous stream continuity incident commander. It turns live evidence into a closed remediation loop, while keeping operators inside one command surface."
- duration: 12s
- poster: 8s
- transition_in: zoom-through
- status: animated
 - src: compositions/frames/03-closed-loop.html
- type: product_intro
- persuasion: Category definition
- beat: relief and control
- blueprint: constellation-hub
- asset_candidates: assets/continuity-baseline.png — healthy live command center with the complete monitoring surface

- focal: assets/continuity-baseline.png
- roles: assets/continuity-baseline.png = supporting surface, dimmed only enough for the loop labels to dominate
- sfx: clean four-step relay, low confirmation tone

Adapt: keep the hub-and-connectors signature; replace ecosystem satellites with the four operational stages and let the live product surface prove the hub is real.
Scene 1 (0.0–2.8s): the healthy command-center capture lands as a wide rounded surface spanning the left two-thirds, with the third-party title masked by `GLOBAL PREMIERE BROADCAST`; the single word `CONTINUITY` reveals above it on its spoken cue.
Scene 2 (2.8–6.0s): four nodes — `OBSERVE`, `REASON`, `ACT`, `PROVE` — arrive one at a time around a fixed center hub (`spring-pop-entrance`, smooth long-tail adaptation), each taking a distinct quadrant over the surface.
Scene 3 (6.0–9.3s): connector paths self-draw clockwise from the hub (`svg-path-draw`), closing the loop only when the voice says “closed remediation loop”; each completed segment receives one compact evidence label.
Scene 4 (9.3–12.0s): a controlled push-in resolves on the central CONTINUITY hub (`coordinate-target-zoom`) while the four stages stay sharp and the product surface softens by selective depth-of-field (`depth-of-field-blur`); hold on the complete loop.

narrativeRole: Name the product and land the promise before implementation detail.
keyMessage: CONTINUITY joins detection, diagnosis, action, and evidence into one loop.

## Frame 4 — Live Evidence

- scene: The healthy command center becomes the hero surface while its six monitored signals are called out one by one.
- voiceover: "At baseline, CONTINUITY watches player quality once per second: playback failures, CDN latency, DRM handshake time, active viewers, bitrate, and buffer health. Grafana Cloud Prometheus carries the signals. Loki carries the edge story."
- duration: 14s
- poster: 10s
- transition_in: cut-the-curve LEFT
- status: outline
- src: compositions/frames/04-live-evidence.html
- type: feature_showcase
- persuasion: Show-don't-tell proof
- beat: clarity
- blueprint: device-surface-showcase
- asset_candidates: assets/continuity-baseline.png — healthy live command center with Prometheus metrics, Loki ingest, and primary CDN routing visible

- focal: assets/continuity-baseline.png
- roles: assets/continuity-baseline.png = cutout hero surface
- sfx: quiet telemetry ticks, six soft callout locks

Adapt: keep the held-surface and screen-advance signature; use one real dashboard state and make the six monitored signals advance as callouts rather than fake screen swaps.
Scene 1 (0.0–3.0s): the healthy capture establishes as a large, straight-on rounded window occupying the left 74%, with `GLOBAL PREMIERE BROADCAST` masking the third-party title; `LIVE BASELINE · 1 HZ` appears as a small operational tag.
Scene 2 (3.0–8.2s): six callouts reveal strictly in narration order — playback failures, CDN latency, DRM handshake, active viewers, bitrate, buffer — as precise mint outline brackets that lock to their real UI regions (`dynamic-content-sequencing`); the camera remains still for legibility.
Scene 3 (8.2–11.3s): Prometheus is highlighted by a single left-to-right keyword glow (`asr-keyword-glow`), then a thin evidence rail connects the metric cards to a `GRAFANA CLOUD PROMETHEUS` source label.
Scene 4 (11.3–14.0s): Loki receives the same causal treatment beneath the surface, ending on `METRICS + EDGE STORY`; all callouts settle and the full live surface holds as the first visual breather.

narrativeRole: Establish the trustworthy baseline and the observability data sources.
keyMessage: The agent starts from live operational evidence, not a generic prompt.

## Frame 5 — Breach

- scene: The captured outage state replaces the healthy surface; red callouts trace the SLA breach, latency spike, buffer collapse, and 502 log.
- voiceover: "Now we inject a simulated collapse on the primary Fastly edge in US East. The failure rate crosses the SLA. Latency spikes. Loki surfaces repeated five-oh-two responses and sixty-eight percent packet loss. The stream begins to stall."
- duration: 16s
- poster: 11s
- transition_in: rack-focus blur-cut LEFT
- status: outline
- src: compositions/frames/05-breach.html
- type: feature_showcase
- persuasion: Negative contrast
- beat: tension
- blueprint: cursor-ui-demo
- asset_candidates: assets/continuity-baseline.png — healthy command center before the causal injection; assets/continuity-outage.png — live command center during the simulated CDN outage with red metrics and 502 evidence

- focal: assets/continuity-outage.png
- roles: assets/continuity-baseline.png = supporting pre-click surface; assets/continuity-outage.png = cutout hero failure state
- sfx: oversized cursor glide, tactile click, rack-focus snap, muted alarm bed

Adapt: keep the locked-stage state-tour signature; one oversized cursor action causes the healthy-to-outage swap, after which evidence reveals without further clicks.
Scene 1 (0.0–3.0s): the baseline capture holds full and straight-on behind the left-side presenter; a 7cqw black cursor enters physically from below on one vector and lands tip-first on `INJECT CDN OUTAGE` (`oversized-cursor`, `cursor-click-ripple`).
Scene 2 (3.0–5.0s): the cursor and target compress together; on the exact click frame a rack-focus blur spikes and swaps baseline to outage at peak blur, then resolves sharp (`press-release-spring`, rack-focus blur-cut). The cursor accelerates off the lower edge rather than fading.
Scene 3 (5.0–9.2s): as “failure rate” and “latency” are spoken, red brackets snap onto the real metric cards in sequence; no camera move competes with the values.
Scene 4 (9.2–12.8s): the real Loki row receives a horizontal evidence highlight and a constructed label `HTTP 502 · 68% PACKET LOSS`; a red route line to the Fastly edge draws on (`svg-path-draw`).
Scene 5 (12.8–16.0s): a buffer indicator drains toward stall while `SLA BREACH` stamps once over the surface; everything else holds still so the incident state reads cleanly.

narrativeRole: Prove the product recognizes a concrete, reproducible incident.
keyMessage: The failure signature is visible across metrics, logs, and viewer experience at once.

## Frame 6 — Reasoning in Context

- scene: Prometheus metrics, active chaos state, and a Loki 502 event converge into a reasoning theater that resolves on the diagnosed Fastly edge and ASN 3356 transit path.
- voiceover: "CONTINUITY invokes Gemini Enterprise with the metric vector, the active chaos state, and the latest edge log. The reasoning chain isolates an edge transit failure affecting the Fastly point of presence and transit ASN three three five six, then selects the exact remediation action."
- duration: 17s
- poster: 12s
- transition_in: cut-the-curve LEFT
- status: outline
- src: compositions/frames/06-reasoning-in-context.html
- type: feature_showcase
- persuasion: Transparent technical reasoning
- beat: intrigue to certainty
- blueprint: agent-progress-theater
- asset_candidates: assets/continuity-outage.png — live incident state providing the metric and log evidence used by the reasoning loop

- focal: assets/continuity-outage.png
- roles: assets/continuity-outage.png = background evidence surface, selectively dimmed behind the reasoning theater
- sfx: one ignition click echo, finite machine ticks, three resolving check tones

Adapt: keep the trigger-to-working-state-to-mutating-receipt signature; remove generic “thinking” filler and expose the actual input context, diagnosis, and selected action.
Scene 1 (0.0–3.2s): the outage capture sits as a full-frame evidence plane under a translucent central reasoning card; three input chips arrive only as named — `METRIC VECTOR`, `CHAOS STATE`, `LATEST LOKI EVENT` — with short-path staged entries.
Scene 2 (3.2–7.4s): a finite Gemini working indicator performs the computation while the chips connect inward; status text steps through `CORRELATE SIGNALS`, `ISOLATE FAULT DOMAIN`, and `SELECT REMEDIATION`.
Scene 3 (7.4–11.8s): the receipt expands downward (`anchored-layout-expand`) and reveals `FASTLY POP · US EAST`, then `TRANSIT ASN 3356`; numbered badges mutate into drawn checks one by one (`svg-path-draw`).
Scene 4 (11.8–15.0s): after a 0.5-second dramatic comma, the action row `SHIFT_TRAFFIC_TO_AKAMAI` expands into the focal slot; the diagnosis rows dim but remain auditable.
Scene 5 (15.0–17.0s): one controlled push tightens on the selected action and the exact incident context; the working indicator dies at resolution and the receipt holds static.

narrativeRole: Show how the diagnosis is grounded and how an action is selected.
keyMessage: Gemini reasons over incident context; it does not guess from a single alert.

## Frame 7 — Execute the Failover

- scene: A mechanical traffic-routing diagram moves egress from Fastly 100/0 to Fastly 20/Akamai 80, then hands off to the recovered product surface.
- voiceover: "No ticket handoff. No human approval queue. CONTINUITY executes shift traffic to Akamai. Primary egress drops to twenty percent. Secondary egress scales to eighty. Playback returns, and the incident record preserves the full reasoning trace."
- duration: 15s
- poster: 10s
- transition_in: cut-the-curve LEFT
- status: outline
- src: compositions/frames/07-execute-failover.html
- type: feature_showcase
- persuasion: Friction removal through action
- beat: power and release
- blueprint: camera-journey
- asset_candidates: assets/continuity-recovery.png — recovered live command center with 20/80 traffic split and restored playback

- focal: assets/continuity-recovery.png
- roles: assets/continuity-recovery.png = cutout payoff surface
- sfx: routed whoosh, two mechanical lock clicks, clean recovery chime

Adapt: keep the motivated multi-leg camera signature; the traffic control is the launch point and the recovered live surface is the consequence the camera travels to.
Scene 1 (0.0–3.1s): a large route manifold establishes to the right of the left-side presenter: `FASTLY 100` over `AKAMAI 0`; a hard green command label `SHIFT_TRAFFIC_TO_AKAMAI` locks underneath.
Scene 2 (3.1–6.0s): “No ticket handoff” and “No human approval queue” arrive as two crossed-out queue tokens, then clear on the same leftward current; the route lever becomes the sole focal control.
Scene 3 (6.0–9.5s): the camera dives through the control as the two numeric shares move in opposite value directions but one visual flow — Fastly to `20%`, Akamai to `80%` (`counting-dynamic-scale`, `stat-bars-and-fills`); the green path visibly redirects at the hinge.
Scene 4 (9.5–12.8s): the journey lands on the recovered command-center capture, straight-on and large; the real `20/80` split and restored state receive brief mint brackets while off-focus route geometry recedes.
Scene 5 (12.8–15.0s): `PLAYBACK RESTORED` draws in above the surface, followed by `REASONING TRACE PRESERVED`; the camera comes fully to rest and the recovered state holds.

narrativeRole: Deliver the autonomous action payoff and make the recovery visually undeniable.
keyMessage: CONTINUITY changes the system, not merely the alert status.

## Frame 8 — The Receipt

- scene: The recovered interface slides aside for a concise incident receipt: annotation ID, action, traffic split, and measured MTTR with benchmark labeling.
- voiceover: "The last step is accountability. CONTINUITY writes a timestamped annotation into Grafana Cloud, returns an incident record, and measures the actual resolution time. A prior benchmarked run completed in one point two eight seconds; the live record remains the source of truth."
- duration: 15s
- poster: 10s
- transition_in: cut-the-curve LEFT
- status: outline
- src: compositions/frames/08-the-receipt.html
- type: benefit_highlight
- persuasion: Verifiable accountability
- beat: trust
- blueprint: video-text-pivot
- asset_candidates: assets/continuity-recovery.png — recovered command center with live RCA, measured MTTR, traffic split, and resolved edge log

- focal: assets/continuity-recovery.png
- roles: assets/continuity-recovery.png = supporting live record and then reduced evidence tile
- sfx: paper-stamp impact, four receipt-row locks, restrained proof chime

Adapt: keep the show-to-yield-to-text signature; substitute the static live product capture for video and let it hand its screen weight to an incident receipt.
Scene 1 (0.0–3.4s): the recovered capture holds center-left at full visual weight with the real incident record visible; a small `LIVE RECORD` label draws on and nothing else competes.
Scene 2 (3.4–7.3s): the capture slides and scales into a right-side evidence tile while a large receipt fills its vacated anchor — `GRAFANA ANNOTATION`, `SHIFT_TRAFFIC_TO_AKAMAI`, `FASTLY 20 · AKAMAI 80` — each row arriving on the spoken phrase (`dynamic-content-sequencing`).
Scene 3 (7.3–10.7s): a 0.5-second stillness-before-proof comma precedes the measured-time row; `LIVE RUN · 12.41s` lands as the primary record, with `PRIOR BENCHMARK · 1.28s` visually subordinate and explicitly labeled.
Scene 4 (10.7–13.2s): `SOURCE OF TRUTH` types into the shared center in near-black while a thin mint rule links it back to the live record; the receipt remains co-visible.
Scene 5 (13.2–15.0s): a solid mint `AUDITABLE` pill stamps beneath the line, its silhouette landing before a single finite glow; the evidence and labels hold completely still.

narrativeRole: Turn autonomy into an auditable operational record.
keyMessage: Every remediation ends with evidence humans can inspect.

## Frame 9 — Production Disclosure

- scene: Three clean production cards connect narration, avatar performance, and final edit without resembling the CONTINUITY runtime architecture.
- voiceover: "This demonstration is itself automated. The narration uses my ElevenLabs voice clone in sub-minute segments to protect vocal consistency. Each segment drives HeyGen Avatar version five, while HyperFrames composes the product capture, captions, motion, and final mix."
- duration: 16s
- poster: 11s
- transition_in: cut-the-curve LEFT
- status: outline
- src: compositions/frames/09-production-disclosure.html
- type: social_proof
- persuasion: Transparent production provenance
- beat: curiosity and craft
- blueprint: grid-card-assemble
- asset_candidates:

- focal: none — the three production stages are constructed provenance cards
- roles: none
- sfx: three clean assembly ticks, short camera shutter for avatar stage, restrained edit-lock tone

Adapt: keep the card-assembly signature but build a left-to-right provenance chain instead of an interchangeable grid; the cards continue to populate after arrival.
Scene 1 (0.0–3.3s): `THIS DEMO IS ALSO AUTOMATED` assembles in two lines at upper-left; a thin provenance rail draws across the full frame behind the right-side presenter.
Scene 2 (3.3–7.0s): the `ELEVENLABS` card arrives first and populates `VOICE CLONE` then `SUB-MINUTE SEGMENTS`; a waveform fill traverses once and stops (`stat-bars-and-fills`, `discrete-text-sequence`).
Scene 3 (7.0–10.8s): the `HEYGEN` card locks into the next rail position and fills `AVATAR v5`; a portrait-frame outline draws around its mark (`svg-path-draw`) and the card state flips to `GENERATED`.
Scene 4 (10.8–14.0s): the `HYPERFRAMES` card arrives and populates `CAPTURE`, `CAPTIONS`, `MOTION`, `MIX` one by one; each item takes a real slot rather than appearing as decoration.
Scene 5 (14.0–16.0s): the rail resolves into one stamped provenance line `VOICE → AVATAR → FINAL CUT`; the three cards hold in a balanced asymmetric field without floating or breathing.

narrativeRole: Satisfy the requested production disclosure without confusing editing tools with the product's runtime dependencies.
keyMessage: The demo was built through a deliberate, quality-controlled AI media pipeline.

## Frame 10 — Keep the Story Playing

- scene: The four-stage loop collapses into the CONTINUITY wordmark, then resolves on a spare closing line and project URL.
- voiceover: "CONTINUITY turns observability from a place you look into a system that acts. Protect the premiere. Preserve the audience. Keep the story playing."
- duration: 11s
- poster: 7s
- transition_in: cut-the-curve LEFT
- status: outline
- src: compositions/frames/10-keep-playing.html
- type: cta
- persuasion: Future pacing
- beat: confidence and inevitability
- blueprint: logo-assemble-lockup
- asset_candidates:

- focal: none — the CONTINUITY lockup is constructed from the four loop segments
- roles: none
- sfx: four-part magnetic assembly, restrained final impact, clean two-note resolve

Adapt: keep the literal parts-build signature; assemble the four operational verbs into a custom continuity ring, then pull the wordmark from the ring and finish on a dead-static lockup.
Scene 1 (0.0–2.5s): four labeled segments — `OBSERVE`, `REASON`, `ACT`, `PROVE` — enter from the leftward film current at different depths and begin interlocking around a fixed empty center.
Scene 2 (2.5–5.4s): the segments complete a circular mark; a mint path draws once around the ring and the center resolves to a clean `C` without bounce.
Scene 3 (5.4–8.0s): the mark slides a short distance left as `CONTINUITY` pulls out to the right with a restrained motion-blur trail; below, `OBSERVABILITY THAT ACTS` reveals left-to-right.
Scene 4 (8.0–9.6s): three short clauses land on one shared baseline in time with the voice — `PROTECT THE PREMIERE`, `PRESERVE THE AUDIENCE`, `KEEP THE STORY PLAYING` — using a hard in-place sequence.
Scene 5 (9.6–11.0s): the final clause remains with the centered lockup and project URL; every decorative element clears, the progress strip completes, and the last frame holds dead still before a short fade to canvas.

narrativeRole: End on the category shift and the audience outcome.
keyMessage: CONTINUITY keeps high-stakes streams running by acting on observability.
