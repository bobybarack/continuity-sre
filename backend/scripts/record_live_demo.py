import asyncio
import os
import shutil
import subprocess
from playwright.async_api import async_playwright

RECORDINGS_DIR = "video-production/recordings"
OUTPUT_ASSETS = "video-production/assets"
os.makedirs(RECORDINGS_DIR, exist_ok=True)
os.makedirs(OUTPUT_ASSETS, exist_ok=True)

async def record_scenarios():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        
        # 1. Record Baseline Healthy Playback (12 seconds)
        print("Recording Take 1: Baseline Healthy...")
        ctx1 = await browser.new_context(
            record_video_dir=RECORDINGS_DIR,
            record_video_size={"width": 1920, "height": 1080},
            viewport={"width": 1920, "height": 1080}
        )
        page1 = await ctx1.new_page()
        await page1.goto("https://continuity-sre.pages.dev", wait_until="networkidle")
        await page1.wait_for_timeout(1000)
        # Ensure in normal mode
        await page1.click("button:has-text(\"Reset\")")
        await page1.wait_for_timeout(10000)
        video_path_1 = await page1.video.path()
        await ctx1.close()
        print("Take 1 video captured:", video_path_1)
        
        # 2. Record Outage / Chaos Injection (14 seconds)
        print("Recording Take 2: Chaos Outage...")
        ctx2 = await browser.new_context(
            record_video_dir=RECORDINGS_DIR,
            record_video_size={"width": 1920, "height": 1080},
            viewport={"width": 1920, "height": 1080}
        )
        page2 = await ctx2.new_page()
        await page2.goto("https://continuity-sre.pages.dev", wait_until="networkidle")
        await page2.wait_for_timeout(2000)
        await page2.click("button:has-text(\"Inject CDN Outage\")")
        await page2.wait_for_timeout(12000)
        video_path_2 = await page2.video.path()
        await ctx2.close()
        print("Take 2 video captured:", video_path_2)
        
        # 3. Record Autonomous Remediation & Traffic Failover (18 seconds)
        print("Recording Take 3: Autonomous Failover & Recovery...")
        ctx3 = await browser.new_context(
            record_video_dir=RECORDINGS_DIR,
            record_video_size={"width": 1920, "height": 1080},
            viewport={"width": 1920, "height": 1080}
        )
        page3 = await ctx3.new_page()
        await page3.goto("https://continuity-sre.pages.dev", wait_until="networkidle")
        await page3.wait_for_timeout(1500)
        await page3.click("button:has-text(\"Inject CDN Outage\")")
        await page3.wait_for_timeout(3000)
        # Trigger autonomous remediation
        await page3.click("button:has-text(\"Trigger Autonomous SRE Failover\")")
        await page3.wait_for_timeout(3000)
        # If auto-heal needed for complete green state:
        await page3.click("button:has-text(\"SRE Auto-Heal\")")
        await page3.wait_for_timeout(10000)
        video_path_3 = await page3.video.path()
        await ctx3.close()
        print("Take 3 video captured:", video_path_3)
        
        await browser.close()
        
        # Convert recordings to MP4 60fps
        conversions = [
            (video_path_1, f"{OUTPUT_ASSETS}/screen_baseline.mp4"),
            (video_path_2, f"{OUTPUT_ASSETS}/screen_outage.mp4"),
            (video_path_3, f"{OUTPUT_ASSETS}/screen_recovery.mp4")
        ]
        for src, dst in conversions:
            cmd = [
                "ffmpeg", "-y", "-i", src,
                "-vf", "fps=60,scale=1920:1080:flags=lanczos",
                "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "18",
                dst
            ]
            print(f"Converting {src} -> {dst}...")
            subprocess.run(cmd, check=True)
            print(f"  Successfully created {dst}")

asyncio.run(record_scenarios())
