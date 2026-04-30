"""快速测试 comfly.chat 视觉API - 单帧"""
import os
import cv2
import base64
import httpx
import time

os.environ["HTTP_PROXY"] = "http://127.0.0.1:9674"
os.environ["HTTPS_PROXY"] = "http://127.0.0.1:9674"

API_KEY = "sk-REDACTED"
BASE_URL = "https://ai.comfly.chat/v1"

# 抽取第一帧
cap = cv2.VideoCapture(r"E:\AI_Director_Studio_Full_Backup\output\segment1_v2.mp4")
ret, frame = cap.read()
cap.release()
frame = cv2.resize(frame, (360, 640))
_, buf = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 75])
b64 = base64.b64encode(buf.tobytes()).decode()
print(f"Frame: {len(buf)/1024:.0f} KB")

models_to_try = ["gpt-4o-mini", "gemini-2.0-flash", "gemini-2.5-flash-nothinking"]

for model in models_to_try:
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": [
            {"type": "text", "text": "Describe the person position and facing direction in this frame in 30 words."},
            {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64}"}}
        ]}],
        "temperature": 0.2,
        "max_tokens": 200,
    }
    timeout = httpx.Timeout(120.0, connect=15.0, read=120.0)
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json",
    }
    print(f"\nTrying {model}...")
    t0 = time.time()
    try:
        with httpx.Client(timeout=timeout) as c:
            r = c.post(f"{BASE_URL}/chat/completions", headers=headers, json=payload)
        elapsed = time.time() - t0
        print(f"  Status: {r.status_code} ({elapsed:.1f}s)")
        if r.status_code == 200:
            data = r.json()
            content = data["choices"][0]["message"]["content"]
            print(f"  Result: {content[:300]}")
            print("  SUCCESS!")
            break
        else:
            print(f"  Error: {r.text[:200]}")
    except Exception as e:
        print(f"  Failed: {e}")

