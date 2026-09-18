---
workflow: product-launch-video
flow: automation
storyboard: no
message: "CONTINUITY turns live Grafana telemetry into an autonomous, evidence-backed remediation loop that protects premiere-night streams before viewers abandon them."
destination: devpost-youtube
aspect: 1920x1080
language: en
audience: "Google Cloud and Grafana Labs hackathon judges, principal architects, and technical evaluators"
length: 140s
angle: "A high-stakes premiere-night failure unfolds in real time, then the product proves detection, diagnosis, failover, annotation, and recovery on-screen."
narration: yes
voice: "user-elevenlabs-clone"
captions: yes
vo_mode: restructured
capture: yes
---

## Intent

Create a polished, emotionally engaging product demo for CONTINUITY: Autonomous Stream Continuity Incident Commander. The opening should make a Hollywood premiere-night outage feel immediate and costly, then pivot into a clear live demonstration of CONTINUITY detecting a playback SLA breach through Grafana Cloud Prometheus and Loki, using Gemini Enterprise to diagnose a transit peer collapse, executing Fastly-to-Akamai traffic failover, and annotating the live Grafana dashboard. The finish should briefly reveal that the video itself was produced through an ElevenLabs voice-clone, HeyGen Avatar v5, and HyperFrames pipeline.

The piece must feel human-edited, technically credible, and ready to upload without another review pass. The avatar remains visible throughout as either a left-side presenter card or a rounded vertical crop with a restrained drop shadow.

## Assets

- https://continuity-sre.pages.dev — production command-center interface and primary screen-recording source.
- https://github.com/bobybarack/continuity-sre — public architecture and implementation reference.
- https://continuity-api-121300560395.us-central1.run.app/docs — production API and endpoint verification source.
- HeyGen avatar configured through the provided environment credentials — on-camera presenter, Avatar v5.
- ElevenLabs voice clone configured through the provided environment credentials — English narration, generated in sub-60-second segments.

## Customizations

- Keep the presenter visible through the complete edit; alternate between a vertical right-side crop and a smaller corner card when product footage needs more room.
- Use real CONTINUITY interface captures for the incident sequence, including outage injection, red telemetry state, Gemini investigation, failover recovery, and post-mortem evidence.
- Animate a concise metric story: baseline, VPF breach, 502/Loki evidence, transit peer diagnosis, 80% Akamai egress shift, restored playback, and measured MTTR.
- Use premium motion graphics, source-traceable technical callouts, captions, subtle sound design, and a restrained cinematic music bed.
- Treat the 1.28-second claim as a measured demo result, not a universal guarantee; show the exact runtime evidence if the live system reproduces it.
- Mention the production pipeline only in the closing beat so the product remains the hero.

## Notes

- Target duration is 2:20, safely inside the requested 1:45–2:50 range and the workflow's three-minute cap.
- Do not state unsupported partner-track rules or implementation details. Resolve discrepancies between the live system, repository, and submission copy in favor of directly verified behavior.
- Do not expose credentials, access tokens, or environment values in frames, captions, logs, metadata, or source control.
- No emojis in project source, captions, narration, logs, or on-screen copy.
