import re

with open("video-production/index.html", "r", encoding="utf-8") as f:
    content = f.read()

# Replace CSS styling to convert into clean Stripe / Linear Light Mode
light_css_overrides = """
    /* --- CONTINUITY LIGHT MODE THEME (STRIPE / LINEAR SPEC) --- */
    body {
      background: #f8fafc !important;
      color: #0f172a !important;
    }

    #root {
      background: #f8fafc !important;
    }

    .cyber-grid {
      background-image: radial-gradient(#cbd5e1 1px, transparent 1px) !important;
      background-size: 32px 32px !important;
      opacity: 0.5 !important;
    }

    /* Top Broadcast Header */
    .broadcast-header {
      background: rgba(255, 255, 255, 0.94) !important;
      border-bottom: 1px solid #e2e8f0 !important;
      box-shadow: 0 1px 4px rgba(0, 0, 0, 0.03) !important;
    }

    .brand-title {
      background: none !important;
      -webkit-text-fill-color: #0f172a !important;
      color: #0f172a !important;
    }

    .brand-subtitle {
      color: #0284c7 !important;
    }

    .target-stream-pill {
      background: #f1f5f9 !important;
      border: 1px solid #e2e8f0 !important;
      color: #334155 !important;
    }

    .model-badge {
      background: #f5f3ff !important;
      border: 1px solid #ddd6fe !important;
      color: #7c3aed !important;
    }

    .status-badge.normal {
      background: #ecfdf5 !important;
      border: 1px solid #a7f3d0 !important;
      color: #065f46 !important;
    }

    .status-badge.outage {
      background: #fef2f2 !important;
      border: 1px solid #fecaca !important;
      color: #991b1b !important;
      box-shadow: 0 0 15px rgba(239, 68, 68, 0.25) !important;
    }

    .status-badge.recovered {
      background: #ecfdf5 !important;
      border: 1px solid #a7f3d0 !important;
      color: #065f46 !important;
      box-shadow: 0 0 15px rgba(16, 185, 129, 0.25) !important;
    }

    /* Metric Cards */
    .metric-card {
      background: #ffffff !important;
      border: 1px solid #e2e8f0 !important;
      box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04) !important;
    }

    .metric-label {
      color: #64748b !important;
    }

    .metric-val {
      color: #0f172a !important;
    }

    .metric-val.green { color: #059669 !important; }
    .metric-val.red { color: #dc2626 !important; }
    .metric-val.blue { color: #0284c7 !important; }

    .metric-sub {
      color: #94a3b8 !important;
    }

    .pill-green {
      background: #ecfdf5 !important;
      color: #059669 !important;
      border: 1px solid #a7f3d0 !important;
    }

    .pill-red {
      background: #fef2f2 !important;
      color: #dc2626 !important;
      border: 1px solid #fecaca !important;
    }

    .pill-blue {
      background: #eff6ff !important;
      color: #2563eb !important;
      border: 1px solid #bfdbfe !important;
    }

    /* Middle Row Cards */
    .chart-panel, .player-panel {
      background: #ffffff !important;
      border: 1px solid #e2e8f0 !important;
      box-shadow: 0 4px 16px rgba(0, 0, 0, 0.04) !important;
    }

    .panel-title {
      color: #0f172a !important;
    }

    .panel-desc {
      color: #64748b !important;
    }

    .legend-item {
      color: #64748b !important;
    }

    .player-canvas-wrapper {
      border: 1px solid #e2e8f0 !important;
    }

    .buffer-track-label {
      color: #64748b !important;
    }

    .buffer-progress-bg {
      background: #f1f5f9 !important;
    }

    /* Lower Row Info Panels */
    .info-panel {
      background: #ffffff !important;
      border: 1px solid #e2e8f0 !important;
      box-shadow: 0 2px 10px rgba(0, 0, 0, 0.04) !important;
    }

    .sre-diag-box {
      background: #f8fafc !important;
      border: 1px solid #e2e8f0 !important;
      color: #334155 !important;
    }

    .sre-stat-cell {
      background: #f8fafc !important;
      border: 1px solid #e2e8f0 !important;
    }

    .sre-stat-title {
      color: #64748b !important;
    }

    .sre-stat-num {
      color: #059669 !important;
    }

    .cdn-item-header {
      color: #334155 !important;
    }

    .cdn-bar-bg {
      background: #f1f5f9 !important;
    }

    .log-stream-box {
      background: #f8fafc !important;
      border: 1px solid #e2e8f0 !important;
    }

    .log-line.green { color: #059669 !important; }
    .log-line.red { color: #dc2626 !important; font-weight: 600 !important; }
    .log-line.purple { color: #7c3aed !important; font-weight: 700 !important; }
    .log-line.cyan { color: #0284c7 !important; font-weight: 700 !important; }

    .chaos-suite-bar {
      background: #ffffff !important;
      border: 1px solid #e2e8f0 !important;
      box-shadow: 0 2px 10px rgba(0, 0, 0, 0.03) !important;
    }

    .chaos-icon-box {
      background: #ecfdf5 !important;
      border: 1px solid #a7f3d0 !important;
    }

    .chaos-icon-box svg {
      fill: #059669 !important;
    }

    .chaos-btn {
      background: #f8fafc !important;
      border: 1px solid #e2e8f0 !important;
      color: #334155 !important;
    }

    .chaos-btn.inject-outage {
      background: #fef2f2 !important;
      border-color: #fecaca !important;
      color: #dc2626 !important;
    }

    .chaos-btn.inject-outage.clicked {
      background: #ef4444 !important;
      border-color: #dc2626 !important;
      color: #ffffff !important;
      box-shadow: 0 0 15px rgba(239, 68, 68, 0.4) !important;
    }

    .chaos-btn.auto-heal {
      background: #ecfdf5 !important;
      border-color: #a7f3d0 !important;
      color: #059669 !important;
    }

    /* Executive Gemini 3.7 Flash Modal in Light Mode */
    #gemini-modal {
      background: rgba(255, 255, 255, 0.98) !important;
      border: 1px solid #cbd5e1 !important;
      box-shadow: 0 25px 60px -12px rgba(99, 102, 241, 0.18), 0 12px 28px -6px rgba(0, 0, 0, 0.08) !important;
    }

    .modal-header {
      border-bottom: 1px solid #f1f5f9 !important;
    }

    .modal-title {
      color: #0f172a !important;
    }

    .modal-sub {
      color: #7c3aed !important;
    }

    .modal-pill {
      background: #f8fafc !important;
      border: 1px solid #e2e8f0 !important;
    }

    .modal-pill-lbl {
      color: #64748b !important;
    }

    .modal-pill-val {
      color: #0f172a !important;
    }

    .modal-terminal-window {
      background: #f8fafc !important;
      border: 1px solid #e2e8f0 !important;
      color: #1e293b !important;
    }

    .term-prompt {
      color: #7c3aed !important;
    }

    /* Lower Third Dock in Light Mode */
    .lower-third-dock {
      background: rgba(255, 255, 255, 0.96) !important;
      border-top: 1px solid #e2e8f0 !important;
      box-shadow: 0 -4px 20px rgba(0, 0, 0, 0.03) !important;
    }

    .hud-card, .subtitle-card, .terminal-card {
      background: #f8fafc !important;
      border: 1px solid #e2e8f0 !important;
    }

    .hud-header {
      color: #64748b !important;
    }

    .hud-stat-num {
      color: #0f172a !important;
    }

    .subtitle-speaker-label {
      color: #0284c7 !important;
    }

    .subtitle-text {
      color: #0f172a !important;
    }

    .subtitle-text .highlight {
      color: #0284c7 !important;
      text-shadow: none !important;
    }

    .subtitle-text .highlight-red {
      color: #dc2626 !important;
      text-shadow: none !important;
    }

    .subtitle-text .highlight-purple {
      color: #7c3aed !important;
      text-shadow: none !important;
    }

    .terminal-card {
      color: #475569 !important;
    }

    .terminal-title {
      color: #0284c7 !important;
    }
  </style>
"""

# Insert overrides right before </head>
content = content.replace("</style>\n</head>", light_css_overrides + "\n</head>")

# Update SVG gradients for chart in light mode
content = content.replace('<stop offset="0%" stop-color="#22c55e" stop-opacity="0.35"/>', '<stop offset="0%" stop-color="#10b981" stop-opacity="0.25"/>')
content = content.replace('<stop offset="100%" stop-color="#22c55e" stop-opacity="0.0"/>', '<stop offset="100%" stop-color="#10b981" stop-opacity="0.0"/>')
content = content.replace('<stop offset="0%" stop-color="#ef4444" stop-opacity="0.45"/>', '<stop offset="0%" stop-color="#ef4444" stop-opacity="0.25"/>')

# Update gridlines stroke in chart
content = content.replace('stroke="#334155"', 'stroke="#e2e8f0"')
content = content.replace('stroke="#1e293b"', 'stroke="#f1f5f9"')

# Update text color in bottom terminal
content = content.replace('style="color:#cbd5e1;"', 'style="color:#475569;"')
content = content.replace('style="color:#4ade80;"', 'style="color:#059669;"')

with open("video-production/index_light.html", "w", encoding="utf-8") as f:
    f.write(content)

print("Created video-production/index_light.html successfully!")
