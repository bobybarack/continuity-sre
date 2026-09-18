# Asset Descriptions

One line per file. Read this instead of opening every image individually.

To find a specific brand or icon, **grep this file for the brand name in the description text** (e.g. `grep -i 'autodesk' asset-descriptions.md`). The Gemini Vision captions identify what's actually in each file — that's the agent's selector.

The `logo-<hash>.svg` filename prefix is a cheap structural hint (DOM said this SVG was inside a `<header>`, home-link `<a>`, or had an aria-label matching the page brand). It is NOT a content claim — many `logo-*` files are nav icons or decorative shapes. Trust the captions, not the filename prefix.

- favicon.ico — 25KB, favicon
- icon-icon-256x256.ico — 25KB, icon icon 256x256
- continuity-baseline.png — Full-page 1920px capture of the live CONTINUITY command center in healthy baseline state: sub-one-percent playback failures, healthy buffer, Fastly at 100%, and Grafana telemetry ingest visible.
- continuity-outage.png — Full-page 1920px capture of the live CONTINUITY command center during a simulated critical CDN outage: playback failures above the SLA, edge latency above 400ms, buffer near 3 seconds, and Loki 502 evidence visible.
- continuity-recovery.png — Full-page 1920px capture of the live CONTINUITY command center after autonomous remediation: playback recovered, traffic split Fastly 20% / Akamai 80%, RCA text, measured MTTR, and restored edge log visible.
- svgs/logo-f025084e.svg — logo f025084e
- svgs/svg-048083d0.svg — This is a black-outlined lightning bolt icon on a white background.
- svgs/svg-0635dff2.svg — This is a black, minimalist icon of a computer processor chip with two diagonal lines inside the square body.
- svgs/svg-1d801866.svg — This is a black and white icon depicting a stylized database or storage drive consisting of two stacked cylinders.
- svgs/svg-27051e25.svg — This is a black circular arrow icon used to represent a refresh or reload action.
- svgs/svg-62db6285.svg — A black checkmark icon enclosed within a circle.
- svgs/svg-6882db10.svg — This is a black pause icon consisting of two vertical rounded rectangles.
- svgs/svg-aa863695.svg — This is a black, four-pointed star icon with a smaller, secondary star element to its lower left.
- svgs/svg-ac661c13.svg — svg ac661c13
- svgs/svg-cd25ce09.svg — This is a black, minimalist icon of a notification bell centered on a white background.
- svgs/svg-fea4a1e8.svg — This black, outline-style icon depicts two four-pointed stars, one larger than the other.
- fonts/4fa387ec64143e14-s.2tuy5pz7dlieh.woff2 — font file
- fonts/53b9e256198e5412-s.390ncx5urfkfu.woff2 — font file
- fonts/5ce348bf30bf5439-s.31988l_ccedte.woff2 — font file
- fonts/6306c77e7c8268e4-s.2dbetqa9o8jxf.woff2 — font file
- fonts/7178b3e590c64307-s.21jp631_3pja2.woff2 — font file
- fonts/797e433ab948586e-s.p.0r6juujl39pe6.woff2 — font file
- fonts/7d817b4c03b0c5f1-s.1uyisp29ctx0d.woff2 — font file
- fonts/8a480f0b521d4e75-s.1qq4vpdcun5oj.woff2 — font file
- fonts/bbc41e54d2fcbd21-s.1rgnod-3esatf.woff2 — font file
- fonts/caa3a2e1cccd8315-s.p.0wgildi0cnwt9.woff2 — font file
- fonts/fef07dbb0973bf53-s.3p2_lha1f2xer.woff2 — font file
