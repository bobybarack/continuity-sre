import asyncio
import os
import subprocess
import time
from playwright.async_api import async_playwright

FRAMES_DIR = os.path.abspath("video-production/deliverable_frames")
BRAIN_DIR = os.path.abspath("/Users/radebe49/.gemini/antigravity-ide/brain/54cb15db-ffe6-4315-b709-fb0a3d59f97a")
BRAIN_DIR_CURR = os.path.abspath("/Users/radebe49/.gemini/antigravity-ide/brain/87bbf7bc-465c-47d4-8fec-5c74324ad8f0")
PORT = 8099

async def capture_light_frames():
    print("Starting Range Server...")
    proc = subprocess.Popen(["node", "video-production/range_server.js"])
    time.sleep(1.2)

    try:
        print("Launching Chromium...")
        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=True,
                args=["--autoplay-policy=no-user-gesture-required", "--disable-web-security"]
            )
            page = await browser.new_page(viewport={"width": 1920, "height": 1080})
            url = f"http://127.0.0.1:{PORT}/index_light.html"
            print(f"Navigating to {url}...")
            await page.goto(url, wait_until="domcontentloaded")
            await page.wait_for_timeout(1500)

            # Ensure stream canvas is rendered
            await page.evaluate("""
                renderStream();
            """)

            test_frames = [
                (15, "derek_01_baseline.png", False),
                (50, "derek_02_outage.png", False),
                (70, "derek_03_gemini_modal.png", True),
                (95, "derek_04_recovered.png", False),
                (125, "derek_05_pipeline.png", False),
            ]

            for t_sec, filename, is_modal in test_frames:
                print(f"Capturing {filename} at t={t_sec}s...")
                await page.evaluate(f"""
                    window.__updateState({t_sec});
                    const tl = window.__timelines['continuity_demo'];
                    if (tl) tl.seek({t_sec}, false);
                    renderStream();
                """)

                if is_modal:
                    await page.evaluate("""
                        const modal = document.getElementById('gemini-modal');
                        if (modal) {
                            modal.style.opacity = '1';
                            modal.style.transform = 'translateY(0)';
                            modal.style.pointerEvents = 'auto';
                        }
                        for (let i = 1; i <= 7; i++) {
                            const r = document.getElementById('term-row-' + i);
                            if (r) r.classList.add('visible');
                        }
                    """)
                else:
                    await page.evaluate("""
                        const modal = document.getElementById('gemini-modal');
                        if (modal) {
                            modal.style.opacity = '0';
                            modal.style.pointerEvents = 'none';
                        }
                    """)

                await page.wait_for_timeout(500)
                
                # Save to deliverable_frames
                dest1 = os.path.join(FRAMES_DIR, filename)
                await page.screenshot(path=dest1)
                print(f"  Saved deliverable frame: {dest1}")

                # Save to brain directory
                dest2 = os.path.join(BRAIN_DIR, filename)
                await page.screenshot(path=dest2)
                print(f"  Saved brain frame: {dest2}")

                # Save to current brain directory
                dest3 = os.path.join(BRAIN_DIR_CURR, filename)
                await page.screenshot(path=dest3)
                print(f"  Saved current brain frame: {dest3}")

            await browser.close()
            print("Successfully captured all 5 light mode derek frames!")
    finally:
        proc.terminate()
        proc.wait()
        print("Range server terminated.")

if __name__ == "__main__":
    asyncio.run(capture_light_frames())
