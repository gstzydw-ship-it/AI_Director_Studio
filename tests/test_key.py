"""Quick test: check if a given API key can access all configured models."""
import sys, httpx, json
if sys.platform == "win32":
    try: sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except: pass

API_KEY = "sk-REDACTED"
BASE_URL = "https://ai.comfly.chat/v1"

MODELS = [
    ("scene_analyst",           "gpt-5.4"),
    ("rhythm_rewrite_director", "gpt-5.4"),
    ("story_planner",           "gpt-5.5"),
    ("shot_director",           "gpt-5.4"),
    ("prompt_compiler",         "gpt-5.4"),
    ("quality_inspector",       "gpt-5.4"),
]

headers = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json",
}

for agent, model in MODELS:
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": "Say OK"}],
        "max_tokens": 10,
        "temperature": 0,
    }
    try:
        with httpx.Client(timeout=30.0) as client:
            r = client.post(f"{BASE_URL}/chat/completions", headers=headers, json=payload)
        if r.status_code == 200:
            text = r.json()["choices"][0]["message"]["content"].strip()
            print(f"  [OK]   {agent:30s} | {model:35s} | {r.status_code} | {text[:30]}")
        else:
            print(f"  [FAIL] {agent:30s} | {model:35s} | {r.status_code} | {r.text[:80]}")
    except Exception as e:
        print(f"  [FAIL] {agent:30s} | {model:35s} | ERROR: {e}")

