import asyncio
import functools
import os
import subprocess
import time
from playwright.async_api import async_playwright

print = functools.partial(print, flush=True)

SNAPSHOTS_DIR = os.path.abspath("video-production/snapshots")
os.makedirs(SNAPSHOTS_DIR, exist_ok=True)
PORT = 8099

async def capture_snapshots():
    print("Starting Node Range Server...")
    proc = subprocess.Popen(["node", "video-production/range_server.js"])
    time.sleep(1.0)

    try:
        print("Launching Playwright Chromium...")
        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=True,
                args=["--autoplay-policy=no-user-gesture-required", "--disable-web-security"]
            )
            page = await browser.new_page(viewport={"width": 1920, "height": 1080})
            url = f"http://127.0.0.1:{PORT}/index.html"
            print(f"Navigating to {url}...")
            await page.goto(url, wait_until="domcontentloaded")
            await page.wait_for_timeout(1000)

            test_points = [
                (5, "snapshot_t05_baseline.png"),
                (36, "snapshot_t36_outage_alert.png"),
                (58, "snapshot_t58_gemini_rca.png"),
                (80, "snapshot_t80_failover_pipeline.png"),
                (95, "snapshot_t95_hyperframes_stack.png")
            ]

            for t_sec, filename in test_points:
                print(f"Seeking to t={t_sec}s...")
                await page.evaluate(f"""
                    window.__updateState({t_sec});
                    window.__timelines['continuity_demo'].seek({t_sec}, false);
                    const vids = document.querySelectorAll('video');
                    vids.forEach(v => {{
                        const start = parseFloat(v.getAttribute('data-start') || 0);
                        const dur = parseFloat(v.getAttribute('data-duration') || 0);
                        if ({t_sec} >= start && {t_sec} <= start + dur) {{
                            v.currentTime = {t_sec} - start;
                        }}
                    }});
                """)
                await page.wait_for_timeout(400)
                dst = os.path.join(SNAPSHOTS_DIR, filename)
                await page.screenshot(path=dst)
                print(f"  Successfully saved {dst}")

            await browser.close()
            print("Completed all snapshots.")
    finally:
        proc.terminate()
        proc.wait()

if __name__ == "__main__":
    asyncio.run(capture_snapshots())
