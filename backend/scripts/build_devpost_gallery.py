import os
import subprocess
from PIL import Image, ImageDraw, ImageFont

GALLERY_DIR = os.path.abspath("devpost-gallery")
BRAIN_GALLERY_DIR = "/Users/radebe49/.gemini/antigravity-ide/brain/54cb15db-ffe6-4315-b709-fb0a3d59f97a/devpost_gallery"
CURRENT_BRAIN_GALLERY_DIR = "/Users/radebe49/.gemini/antigravity-ide/brain/87bbf7bc-465c-47d4-8fec-5c74324ad8f0/devpost_gallery"
os.makedirs(GALLERY_DIR, exist_ok=True)
os.makedirs(BRAIN_GALLERY_DIR, exist_ok=True)
os.makedirs(CURRENT_BRAIN_GALLERY_DIR, exist_ok=True)

# Target 3:2 Dimensions: 1920 x 1280
TARGET_W = 1920
TARGET_H = 1280

def get_font(size, bold=False):
    font_paths = [
        "/System/Library/Fonts/SFProText-Bold.otf" if bold else "/System/Library/Fonts/SFProText-Regular.otf",
        "/System/Library/Fonts/HelveticaNeue.ttc",
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf" if bold else "/System/Library/Fonts/Supplemental/Arial.ttf",
    ]
    for p in font_paths:
        if os.path.exists(p):
            try:
                return ImageFont.truetype(p, size)
            except Exception:
                pass
    return ImageFont.load_default()

font_title = get_font(26, bold=True)
font_sub = get_font(17, bold=False)
font_tag = get_font(14, bold=True)
font_meta = get_font(16, bold=False)
font_meta_bold = get_font(16, bold=True)

def create_slide_3_2(base_img_path, category_tag, slide_title, subtitle, meta_left, meta_right, output_paths):
    # Pure Light Canvas (Stripe / Linear Slate-50)
    canvas = Image.new("RGB", (TARGET_W, TARGET_H), (248, 250, 252))
    draw = ImageDraw.Draw(canvas)
    
    # Top Header Bar (Height: 90px)
    draw.rectangle([(0, 0), (TARGET_W, 90)], fill=(255, 255, 255))
    draw.line([(0, 90), (TARGET_W, 90)], fill=(226, 232, 240), width=1)
    
    # Category Tag Pill
    bbox = font_tag.getbbox(category_tag)
    text_w = bbox[2] - bbox[0]
    tag_w = max(180, text_w + 32)
    draw.rounded_rectangle([(32, 24), (32 + tag_w, 66)], radius=6, fill=(240, 249, 255), outline=(186, 230, 253), width=1)
    draw.text((32 + (tag_w - text_w) // 2, 34), category_tag, fill=(2, 132, 199), font=font_tag)
    
    # Slide Title & Subtitle
    title_x = 32 + tag_w + 24
    draw.text((title_x, 20), slide_title, fill=(15, 23, 42), font=font_title)
    draw.text((title_x, 54), subtitle, fill=(100, 116, 139), font=font_sub)
    
    # Brand logo indicator on top right with official transparent emblem
    logo_path = "frontend/public/continuity-logo-dark.png"
    if os.path.exists(logo_path):
        logo_icon = Image.open(logo_path).convert("RGBA").resize((32, 32), Image.Resampling.LANCZOS)
        canvas.paste(logo_icon, (TARGET_W - 275, 29), logo_icon)
        draw.text((TARGET_W - 232, 32), "CONTINUITY SRE", fill=(15, 23, 42), font=font_title)
    else:
        draw.text((TARGET_W - 240, 32), "CONTINUITY SRE", fill=(15, 23, 42), font=font_title)
    
    # Check if base image exists and load with alpha support
    if os.path.exists(base_img_path):
        base_raw = Image.open(base_img_path)
        if base_raw.mode == "RGBA":
            white_bg = Image.new("RGBA", base_raw.size, (255, 255, 255, 255))
            base_img = Image.alpha_composite(white_bg, base_raw).convert("RGB")
        else:
            base_img = base_raw.convert("RGB")

        if base_img.size == (TARGET_W, TARGET_H):
            for p in output_paths:
                os.makedirs(os.path.dirname(p), exist_ok=True)
                base_img.save(p, "PNG", optimize=True)
                file_size_mb = os.path.getsize(p) / (1024 * 1024)
                print(f"Direct 3:2 Slide: {os.path.basename(p)} ({TARGET_W}x{TARGET_H}, {file_size_mb:.2f} MB)")
            return
        
        # Otherwise, scale 16:9 (1920x1080) and frame with header/footer
        base_img = base_img.resize((1920, 1080), Image.Resampling.LANCZOS)
        canvas.paste(base_img, (0, 90))
    else:
        draw.rectangle([(0, 90), (TARGET_W, 1170)], fill=(241, 245, 249))
        draw.text((TARGET_W//2 - 100, 600), "Asset Preview", fill=(100, 116, 139), font=font_title)
        
    # Bottom Footer Bar (Height: 110px)
    draw.rectangle([(0, 1170), (TARGET_W, TARGET_H)], fill=(255, 255, 255))
    draw.line([(0, 1170), (TARGET_W, 1170)], fill=(226, 232, 240), width=1)
    
    # Meta tags / Telemetry readouts
    draw.text((36, 1205), meta_left, fill=(100, 116, 139), font=font_meta)
    draw.text((TARGET_W - 550, 1205), meta_right, fill=(5, 150, 105), font=font_meta_bold)
    
    # Save to all destination paths
    for p in output_paths:
        os.makedirs(os.path.dirname(p), exist_ok=True)
        canvas.save(p, "PNG", optimize=True)
        file_size_mb = os.path.getsize(p) / (1024 * 1024)
        print(f"Created: {os.path.basename(p)} ({canvas.size[0]}x{canvas.size[1]}, 3:2, {file_size_mb:.2f} MB)")

def main():
    print("Building Light-Mode 3:2 Devpost Image Gallery...")
    brain_dir_old = "/Users/radebe49/.gemini/antigravity-ide/brain/54cb15db-ffe6-4315-b709-fb0a3d59f97a"
    brain_dir_curr = "/Users/radebe49/.gemini/antigravity-ide/brain/87bbf7bc-465c-47d4-8fec-5c74324ad8f0"
    deliverables_dir = os.path.abspath("video-production/deliverable_frames")
    
    slides = [
        {
            "img": "devpost_arch_diagram_1789128542473.jpg",
            "tag": "SYSTEM TOPOLOGY",
            "title": "Autonomous Incident Response Architecture",
            "sub": "Real-time Telemetry Ingestion -> Gemini 3.7 Flash Reasoning -> Automated Multi-CDN Failover",
            "left": "OpenMetrics Prometheus Exporter | Loki Log Stream | Google GenAI SDK | Multi-CDN",
            "right": "Automated Mean Time to Resolution: 1.28s",
            "out": "01_CONTINUITY_System_Architecture.png"
        },
        {
            "img": os.path.join(deliverables_dir, "derek_01_baseline.png"),
            "tag": "STAGE 01: BASELINE",
            "title": "Live 4K Stream Ingest & Observability HUD",
            "sub": "Spider-Man: Brand New Day (World Premiere) - 4.28M Viewers - Fastly Edge POP 100% Primary",
            "left": "Bitrate: 14.8 Mbps HDR | Forward Buffer: 28.5s | SLA: 99.98% | CDN Latency: 48ms",
            "right": "Status: SLA Operational (VPF: 0.15%)",
            "out": "02_Command_Center_Baseline_4K.png"
        },
        {
            "img": os.path.join(deliverables_dir, "derek_02_outage.png"),
            "tag": "STAGE 02: OUTAGE",
            "title": "Simulated Transit Collapse & Buffer Stall Alert",
            "sub": "Injected upstream transit failure on Fastly Edge POP us-east-2 triggering immediate playback freeze",
            "left": "Buffer Collapse: 2.9s Critical | Error 502 Bad Gateway | Packet Loss: 68%",
            "right": "Alert: Critical Edge Outage Active",
            "out": "03_Chaos_Simulation_Edge_Collapse.png"
        },
        {
            "img": "video-production/screenshots/cycle_02_outage.png",
            "tag": "STAGE 03: METRICS",
            "title": "Prometheus SLA Breach Vector Ingestion",
            "sub": "Video Playback Failure (VPF) rate surges past the 1.00% red dashed SLA threshold to 5.08%",
            "left": "Metric: streaming_playback_failure_ratio | Scraping Interval: 1.0s | Exporter: Prometheus Mimir",
            "right": "Threshold Breach: +4.93% Over SLA Target",
            "out": "04_Prometheus_SLA_Breach_VPF_Spike.png"
        },
        {
            "img": os.path.join(deliverables_dir, "derek_03_gemini_modal.png"),
            "tag": "STAGE 04: AI SRE",
            "title": "Gemini 3.7 Flash Autonomous Reasoning Terminal",
            "sub": "Ingests Prometheus QoS vectors & Loki structured logs to isolate root cause: ASN 3356 transit drop",
            "left": "Model: Google Cloud Gemini 3.7 Flash | Triage Duration: 1.28s | Policy: SHIFT_TRAFFIC_TO_AKAMAI",
            "right": "Root Cause Diagnosed: Level 3 Transit Drop",
            "out": "05_Autonomous_Gemini_Reasoning_Terminal.png"
        },
        {
            "img": os.path.join(deliverables_dir, "derek_04_recovered.png"),
            "tag": "STAGE 05: FAILOVER",
            "title": "Automated Multi-CDN Egress Traffic Reallocation",
            "sub": "Autonomous traffic shift dynamically throttles Fastly to 20% and scales Akamai Edge CDN to 80%",
            "left": "Egress Policy: Akamai 80% / Fastly 20% | BGP Bypass Active | 4K Playback Unfrozen",
            "right": "Status: Failover Restored (Dual Route)",
            "out": "06_Automated_Traffic_Failover_Akamai.png"
        },
        {
            "img": "video-production/screenshots/inspect_04_recovered.png",
            "tag": "STAGE 06: RECOVERY",
            "title": "Telemetry Restabilization & Zero Viewer Churn",
            "sub": "Failure rate plunges from 5.08% back to 0.18%, forward buffer depth recovers from 2.9s to 27.8s",
            "left": "Resolved SLA: 99.98% | CDN Latency: 44ms nominal | Churn Prevented: $1,450,000+",
            "right": "Telemetry Restabilized (All Green)",
            "out": "07_Telemetry_Restabilization_Recovered.png"
        },
        {
            "img": os.path.join(deliverables_dir, "derek_03_gemini_modal.png"),
            "tag": "DEEP REASONING",
            "title": "Loki Structured Log Correlation & Root Cause Analysis",
            "sub": "Real-time parsing of 502 Bad Gateway log lines with upstream transit peer ASN lookup",
            "left": "Datasource: Grafana Cloud Loki | Log Stream: fastly_edge_pop_access_log | Error: connection refused",
            "right": "ASN 3356 Transit Drop Isolated",
            "out": "08_Loki_Structured_Log_Stream_502.png"
        },
        {
            "img": os.path.join(deliverables_dir, "derek_05_pipeline.png"),
            "tag": "INFRASTRUCTURE",
            "title": "Autonomous Agentic Production Pipeline",
            "sub": "End-to-end execution: Antigravity orchestration, ElevenLabs voice cloning, and HyperFrames 60fps video",
            "left": "Voice Model: Derek Clone | Framework: HeyGen HyperFrames | Video Codec: 1080p60 H.264",
            "right": "Self-Healing Infrastructure & Media",
            "out": "09_Agentic_Production_Pipeline.png"
        },
        {
            "img": "video-production/thumbnails/thumb_split_failover_1789104058331.jpg",
            "tag": "TECHNICAL HERO",
            "title": "Dual-Path Traffic Failover Topology",
            "sub": "High-contrast technical visualization of the 1.28-second autonomous egress rerouting mechanism",
            "left": "Primary Route: Fastly POP iad-01 (Packet Loss) | Secondary Route: Akamai Edge CDN (Healthy)",
            "right": "1.28s Mean Time to Resolution",
            "out": "10_Dual_Path_Failover_Concept.png"
        },
        {
            "img": "video-production/thumbnails/thumb_severed_fiber_1789104039805.jpg",
            "tag": "INCIDENT DRAMA",
            "title": "The Anatomy of Premiere Night Error 502",
            "sub": "Undersea fiber optic transit failure causing cascading streaming stalls across millions of households",
            "left": "Failure Mode: Transit Peering Loss | Impact: Global Buffer Freeze | Target: Zero Downtime",
            "right": "The $1.4M Premiere Disaster",
            "out": "11_Severed_Fiber_Error_502.png"
        },
        {
            "img": "video-production/assets/brand_board_light_16_9.png",
            "tag": "BRAND IDENTITY",
            "title": "CONTINUITY Official Emblem & Design System",
            "sub": "Precision engineering shield with cinema infinity loop symbolizing unbroken streaming continuity",
            "left": "Typography: Plus Jakarta Sans & SF Pro | Palette: Obsidian, Pure White, Laser Cyan, Emerald",
            "right": "Master 2048x2048 Vector Identity",
            "out": "12_CONTINUITY_Brand_Identity.png"
        }
    ]
    
    for s in slides:
        img_path = s["img"]
        # Search candidate locations
        candidates = [
            img_path,
            os.path.join(deliverables_dir, os.path.basename(img_path)),
            os.path.join(brain_dir_curr, os.path.basename(img_path)),
            os.path.join(brain_dir_old, os.path.basename(img_path)),
            os.path.abspath(os.path.basename(img_path)),
        ]
        resolved_img = None
        for c in candidates:
            if os.path.exists(c):
                resolved_img = c
                break
                
        if not resolved_img:
            print(f"Warning: Could not find image for {s['out']}: {img_path}")
            resolved_img = img_path
            
        out1 = os.path.join(GALLERY_DIR, s["out"])
        out2 = os.path.join(BRAIN_GALLERY_DIR, s["out"])
        out3 = os.path.join(CURRENT_BRAIN_GALLERY_DIR, s["out"])
        create_slide_3_2(
            base_img_path=resolved_img,
            category_tag=s["tag"],
            slide_title=s["title"],
            subtitle=s["sub"],
            meta_left=s["left"],
            meta_right=s["right"],
            output_paths=[out1, out2, out3]
        )
        
    print(f"\nAll {len(slides)} Devpost gallery images generated successfully in light mode!")

if __name__ == "__main__":
    main()
