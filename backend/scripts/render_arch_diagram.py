import asyncio
import os
import subprocess
import time
from playwright.async_api import async_playwright

BRAIN_DIR_OLD = "/Users/radebe49/.gemini/antigravity-ide/brain/54cb15db-ffe6-4315-b709-fb0a3d59f97a"
BRAIN_DIR_CURR = "/Users/radebe49/.gemini/antigravity-ide/brain/87bbf7bc-465c-47d4-8fec-5c74324ad8f0"
WORKSPACE_DIR = "/Users/radebe49/7DAYRUN/premiereshield-grafana"

async def render():
    proc = subprocess.Popen(["node", "video-production/range_server.js"])
    time.sleep(1.2)
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page(viewport={"width": 1920, "height": 1280})
            url = "http://127.0.0.1:8099/arch_diagram_light.html"
            print(f"Navigating to {url}...")
            await page.goto(url, wait_until="networkidle")
            await page.wait_for_timeout(1000)

            # Targets
            targets = [
                os.path.join(BRAIN_DIR_OLD, "devpost_arch_diagram_1789128542473.jpg"),
                os.path.join(WORKSPACE_DIR, "devpost_arch_diagram_1789128542473.jpg"),
                os.path.join(BRAIN_DIR_CURR, "devpost_arch_diagram_1789128542473.jpg"),
                os.path.join(BRAIN_DIR_CURR, "arch_diagram_light_10s_flow.jpg"),
            ]

            for target in targets:
                os.makedirs(os.path.dirname(target), exist_ok=True)
                await page.screenshot(path=target, quality=95, type="jpeg")
                print(f"Saved diagram screenshot: {target}")

            await browser.close()
    finally:
        proc.terminate()
        proc.wait()
        print("Range server terminated.")

if __name__ == "__main__":
    asyncio.run(render())
