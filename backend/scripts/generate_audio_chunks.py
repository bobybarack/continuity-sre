import os
import requests
from dotenv import load_dotenv

load_dotenv()

ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY", "").strip()
VOICE_ID = "RwG7d6QnCEZFIiJML8BA" # Custom voice 'narrate' in the user account
OUTPUT_DIR = "video-production/audio"

os.makedirs(OUTPUT_DIR, exist_ok=True)

chunks = [
    {
        "filename": "audio_chunk_1.mp3",
        "text": (
            "After months of nonstop engineering work, Friday night was the one release I had blocked off all summer: "
            "the midnight premiere of Spider-Man: Brand New Day. "
            "But five minutes in, four million viewers hit a frozen screen: Error 502. "
            "For 40 agonizing minutes, human SREs scrambled across dozens of dashboard tabs trying to isolate the failure. "
            "In Hollywood, continuity is the sacred craft of making sure no flaw breaks the cinematic illusion. "
            "In streaming, continuity is zero downtime. "
            "That is why I built CONTINUITY: an autonomous incident commander powered by Google Cloud Gemini 3.7 Flash."
        )
    },
    {
        "filename": "audio_chunk_2.mp3",
        "text": (
            "When an edge transit link collapses on our primary Fastly POP, Prometheus telemetry immediately catches the breach: "
            "video playback failures surge past 5%, and player buffers collapse to under three seconds. "
            "CONTINUITY activates instantly. Ingesting live Prometheus metric streams and Loki edge logs, the Google Cloud Gemini 3.7 Flash "
            "reasoning engine diagnoses the root cause in just 1.28 seconds: an upstream transit peering drop on ASN 3356. "
            "Without waiting for a human on-call engineer, the agent autonomously executes a traffic failover, rerouting 80% of egress "
            "to our secondary Akamai edge and logging the incident signature for Grafana Cloud telemetry. "
            "Mean Time to Resolution: 1.28 seconds. Millions in subscriber churn prevented."
        )
    },
    {
        "filename": "audio_chunk_3.mp3",
        "text": (
            "Now, here is the secret behind what you are watching right now: this entire demo video was autonomously scripted, voiced, "
            "and edited by our AI agent, Antigravity. "
            "To guarantee broadcast audio fidelity, Antigravity synthesized my cloned voice using ElevenLabs, splitting the teleprompter "
            "into precise sixty-second chunks to completely eliminate acoustic drift and model fatigue. "
            "The voice stems were coupled with my digital twin avatar via HeyGen, and the entire production was assembled using HyperFrames, "
            "HeyGen's open-source HTML-to-video framework, rendering seekable GSAP motion graphics, telemetry cards, and multi-track audio "
            "at 60 frames per second. "
            "Self-healing infrastructure. Self-producing media. This is CONTINUITY."
        )
    }
]

headers = {
    "xi-api-key": ELEVENLABS_API_KEY,
    "Content-Type": "application/json"
}

for i, chunk in enumerate(chunks, 1):
    path = os.path.join(OUTPUT_DIR, chunk["filename"])
    print(f"Synthesizing Chunk {i} -> {chunk['filename']}...")
    payload = {
        "text": chunk["text"],
        "model_id": "eleven_multilingual_v2",
        "voice_settings": {
            "stability": 0.50,
            "similarity_boost": 0.80,
            "style": 0.15,
            "use_speaker_boost": True
        }
    }
    resp = requests.post(
        f"https://api.elevenlabs.io/v1/text-to-speech/{VOICE_ID}",
        headers=headers,
        json=payload
    )
    if resp.status_code == 200:
        with open(path, "wb") as f:
            f.write(resp.content)
        print(f"  Successfully saved {path} ({len(resp.content)} bytes)")
    else:
        print(f"  Failed: status {resp.status_code}, error: {resp.text}")

print("Audio generation complete.")
