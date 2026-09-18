import asyncio
import functools
import os
import subprocess
import time
from playwright.async_api import async_playwright

print = functools.partial(print, flush=True)

OUTPUT_DIR = os.path.abspath("video-production/rendered")
os.makedirs(OUTPUT_DIR, exist_ok=True)
FINAL_MP4 = os.path.abspath("video-production/CONTINUITY_Incident_Commander_Demo_1080p60.mp4")
AUDIO_VOICE = os.path.abspath("video-production/audio/narration_master.mp3")
AUDIO_AMBIENT = os.path.abspath("video-production/audio/ambient_bed.mp3")

PORT = 8099
TOTAL_DURATION = 143 # 143 seconds (2m 23s) matching Derek voice narration

async def render_pipeline():
    print("==================================================================")
    print("CONTINUITY: Broadcast Demo Video Render Pipeline")
    print("==================================================================")
    
    # 1. Start Range Server
    print("1. Starting Local Media Server...")
    proc = subprocess.Popen(["node", "video-production/range_server.js"])
    time.sleep(1.0)
    
    video_recording_path = None
    try:
        # 2. Launch Chromium with recording context
        print("2. Launching Headless Chromium with 1080p 60fps Recorder...")
        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=True,
                args=[
                    "--autoplay-policy=no-user-gesture-required",
                    "--disable-web-security",
                    "--disable-background-timer-throttling",
                    "--disable-backgrounding-occluded-windows",
                    "--disable-renderer-backgrounding",
                    "--enable-gpu-rasterization"
                ]
            )
            context = await browser.new_context(
                record_video_dir=OUTPUT_DIR,
                record_video_size={"width": 1920, "height": 1080},
                viewport={"width": 1920, "height": 1080}
            )
            page = await context.new_page()
            
            url = f"http://127.0.0.1:{PORT}/index.html"
            print(f"3. Loading Composition at {url}...")
            await page.goto(url, wait_until="domcontentloaded")
            await page.wait_for_timeout(2000)
            
            print("4. Starting Live Deterministic Playback...")
            # Unmute and start all videos and GSAP timeline in sync
            await page.evaluate("""
                const tl = window.__timelines['continuity_demo'];
                tl.time(0);
                tl.play();
                
                const vids = document.querySelectorAll('video');
                vids.forEach(v => {
                    v.currentTime = 0;
                    v.play().catch(() => {});
                });
            """)
            
            # Monitor progress every 10 seconds
            start_wall = time.time()
            for elapsed in range(0, TOTAL_DURATION + 2, 10):
                await page.wait_for_timeout(10000)
                current_time = await page.evaluate("window.__timelines['continuity_demo'].time()")
                pct = min(100, (current_time / TOTAL_DURATION) * 100)
                print(f"   [Rendering Progress] Playhead: {current_time:.1f}s / {TOTAL_DURATION}s ({pct:.1f}%)")
                if current_time >= TOTAL_DURATION:
                    break
                    
            print("5. Composition playback completed. Finalizing video capture...")
            video_recording_path = await page.video.path()
            await context.close()
            await browser.close()
            print(f"   Raw capture saved to: {video_recording_path}")
            
    finally:
        proc.terminate()
        proc.wait()
        print("   Media server stopped.")
        
    if not video_recording_path or not os.path.exists(video_recording_path):
        raise RuntimeError("Video recording file was not generated.")
        
    # 3. Master Audio Muxing & Normalization via FFmpeg
    print("6. Muxing Master Audio Stems, Normalizing to -14 LUFS, and Encoding 1080p 60fps MP4...")
    ffmpeg_cmd = [
        "ffmpeg", "-y",
        "-i", video_recording_path,
        "-i", AUDIO_VOICE,
        "-i", AUDIO_AMBIENT,
        "-filter_complex",
        "[1:a]volume=1.0[v];[2:a]volume=0.14[bg];[v][bg]amix=inputs=2:duration=first[amix];[amix]loudnorm=I=-14:TP=-1.5:LRA=11[aout]",
        "-map", "0:v",
        "-map", "[aout]",
        "-c:v", "libx264",
        "-preset", "medium",
        "-crf", "17",
        "-pix_fmt", "yuv420p",
        "-r", "60",
        "-c:a", "aac",
        "-b:a", "256k",
        "-ar", "48000",
        "-t", str(TOTAL_DURATION),
        FINAL_MP4
    ]
    
    subprocess.run(ffmpeg_cmd, check=True)
    print("7. Encoding completed successfully!")
    print(f"   FINAL MASTER DELIVERABLE: {FINAL_MP4}")
    
    # 4. Probe deliverable
    probe_cmd = [
        "ffprobe", "-v", "quiet",
        "-print_format", "json",
        "-show_format", "-show_streams",
        FINAL_MP4
    ]
    res = subprocess.run(probe_cmd, capture_output=True, text=True, check=True)
    print("\n--- DELIVERABLE TECHNICAL VERIFICATION ---")
    import json
    info = json.loads(res.stdout)
    fmt = info.get("format", {})
    print(f"File Size: {int(fmt.get('size', 0)) / (1024*1024):.2f} MB")
    print(f"Duration: {float(fmt.get('duration', 0)):.2f} seconds")
    print(f"Bitrate: {int(fmt.get('bit_rate', 0)) / 1000:.1f} kbps")
    for s in info.get("streams", []):
        print(f"Stream {s.get('index')}: {s.get('codec_type')} ({s.get('codec_name')}) - {s.get('width', '')}x{s.get('height', '')} @ {s.get('r_frame_rate', '')} fps")
    print("==================================================================")

if __name__ == "__main__":
    asyncio.run(render_pipeline())
