import asyncio
import os
import subprocess
import time
from playwright.async_api import async_playwright

FRAMES_DIR = os.path.abspath("video-production/deliverable_frames")
BRAIN_DIR_CURR = "/Users/radebe49/.gemini/antigravity-ide/brain/87bbf7bc-465c-47d4-8fec-5c74324ad8f0"
BRAIN_DIR_OLD = "/Users/radebe49/.gemini/antigravity-ide/brain/54cb15db-ffe6-4315-b709-fb0a3d59f97a"
os.makedirs(FRAMES_DIR, exist_ok=True)
os.makedirs(BRAIN_DIR_CURR, exist_ok=True)
os.makedirs(BRAIN_DIR_OLD, exist_ok=True)

PORT = 3333

async def capture_app_frames():
    print(f"Starting HTTP server for frontend/out on port {PORT}...")
    server_proc = subprocess.Popen(
        ["python3", "-m", "http.server", str(PORT)],
        cwd=os.path.abspath("frontend/out"),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    time.sleep(1.5)

    stages = [
        ("baseline", "derek_01_baseline.png"),
        ("outage", "derek_02_outage.png"),
        ("gemini_modal", "derek_03_gemini_modal.png"),
        ("recovered", "derek_04_recovered.png"),
        ("pipeline", "derek_05_pipeline.png"),
    ]

    try:
        print("Launching Chromium via Playwright...")
        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=True,
                args=[
                    "--autoplay-policy=no-user-gesture-required",
                    "--disable-web-security",
                    "--hide-scrollbars",
                ],
            )
            context = await browser.new_context(
                viewport={"width": 1920, "height": 1080},
                device_scale_factor=1,
            )
            page = await context.new_page()

            for stage, filename in stages:
                url = f"http://127.0.0.1:{PORT}/?stage={stage}"
                print(f"\nCapturing stage '{stage}' -> {filename}...")
                await page.goto(url, wait_until="networkidle")
                await page.wait_for_timeout(1800)

                # Ensure demo state is active
                await page.evaluate(f"""
                    if (window.__setDemoState) {{
                        window.__setDemoState('{stage}');
                    }}
                """)
                await page.wait_for_timeout(800)

                # Capture deliverable frame
                dest_frames = os.path.join(FRAMES_DIR, filename)
                await page.screenshot(path=dest_frames)
                size_kb = os.path.getsize(dest_frames) / 1024
                print(f"  [SAVED] {dest_frames} ({size_kb:.1f} KB)")

                # Copy to current brain dir
                dest_brain_curr = os.path.join(BRAIN_DIR_CURR, filename)
                await page.screenshot(path=dest_brain_curr)
                print(f"  [SAVED] {dest_brain_curr}")

                # Copy to old brain dir
                dest_brain_old = os.path.join(BRAIN_DIR_OLD, filename)
                await page.screenshot(path=dest_brain_old)
                print(f"  [SAVED] {dest_brain_old}")

            await browser.close()
            print("\nSuccessfully captured all 5 current app dashboard frames!")
    finally:
        server_proc.terminate()
        server_proc.wait()
        print("HTTP server stopped.")

if __name__ == "__main__":
    asyncio.run(capture_app_frames())
