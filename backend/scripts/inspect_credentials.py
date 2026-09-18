import os
import json
import requests
from dotenv import load_dotenv

load_dotenv()

import functools
print = functools.partial(print, flush=True)

eleven_key = os.getenv("ELEVENLABS_API_KEY", "").strip()
voice_id = os.getenv("ELEVENLABS_VOICE_ID", "").strip()
heygen_key = os.getenv("HEYGEN_API_KEY", "").strip()
avatar_id = os.getenv("HEYGEN_AVATAR_ID", "").strip()

print("--- 1. ElevenLabs Inspection ---")
headers_el = {"xi-api-key": eleven_key}
r_el = requests.get("https://api.elevenlabs.io/v1/voices", headers=headers_el)
print("ElevenLabs Voices Status:", r_el.status_code)
if r_el.status_code == 200:
    voices = r_el.json().get("voices", [])
    print(f"Total Voices Available: {len(voices)}")
    matching_voice = None
    for v in voices:
        vid = v.get("voice_id")
        vname = v.get("name")
        vcat = v.get("category")
        if vid == voice_id or voice_id in vid:
            matching_voice = v
            print(f"-> MATCH FOUND: ID: {vid} | Name: {vname} | Category: {vcat}")
        elif vcat in ["cloned", "custom", "generated"]:
            print(f"-> Cloned/Custom Voice: ID: {vid} | Name: {vname} | Category: {vcat}")
    if not matching_voice:
        print(f"Target Voice ID '{voice_id}' was not found in the account voice list.")
        print("First 5 available voices in account:")
        for v in voices[:5]:
            print(f"   ID: {v.get('voice_id')} | Name: {v.get('name')}")
else:
    print("ElevenLabs Error:", r_el.text)

print("\n--- 2. HeyGen Inspection ---")
headers_hg = {"X-Api-Key": heygen_key}
r_user = requests.get("https://api.heygen.com/v1/user/remaining_quota", headers=headers_hg)
print(f"HeyGen Quota API: {r_user.status_code} - {r_user.text}")

r_av = requests.get("https://api.heygen.com/v2/avatars", headers=headers_hg)
print("HeyGen v2 Avatars Status:", r_av.status_code)
if r_av.status_code == 200:
    data = r_av.json().get("data", {})
    avatars = data.get("avatars", [])
    talking_photos = data.get("talking_photos", [])
    print(f"Avatars count: {len(avatars)} | Talking photos count: {len(talking_photos)}")
    
    matches = [a for a in avatars if avatar_id in str(a)]
    print(f"Matches for {avatar_id} in standard avatars: {len(matches)}")
    if matches:
        print(json.dumps(matches[0], indent=2))
        
    tp_matches = [p for p in talking_photos if avatar_id in str(p)]
    print(f"Matches for {avatar_id} in talking photos: {len(tp_matches)}")
    if tp_matches:
        print(json.dumps(tp_matches[0], indent=2))
        
    # Check custom avatar groups or avatar lists
    r_custom = requests.get("https://api.heygen.com/v2/avatar_groups", headers=headers_hg)
    if r_custom.status_code == 200:
        groups = r_custom.json().get("data", {}).get("avatar_group_list", [])
        print(f"Avatar Groups count: {len(groups)}")
        for g in groups:
            print(f"Group: {g.get('avatar_group_id')} | Name: {g.get('avatar_group_name')}")
            if avatar_id in str(g):
                print(f"-> Target matched in group: {g}")
