import os
os.environ["HTTP_PROXY"] = "http://127.0.0.1:9674"
os.environ["HTTPS_PROXY"] = "http://127.0.0.1:9674"
os.environ["NO_PROXY"] = "ai.comfly.chat,127.0.0.1,localhost"

from openai import OpenAI
import time

client = OpenAI(
    api_key="sk-REDACTED",
    base_url="https://ai.comfly.chat/v1",
    timeout=15
)

print("Sending chat request to ai.comfly.chat with claude-opus-4-6...")
start = time.time()
try:
    resp = client.chat.completions.create(
        model="claude-opus-4-6",
        messages=[{"role": "user", "content": "Say hi in 5 words"}],
        max_tokens=50
    )
    elapsed = time.time() - start
    print(f"[SUCCESS] in {elapsed:.1f}s: {resp.choices[0].message.content}")
except Exception as e:
    elapsed = time.time() - start
    print(f"[FAILED] in {elapsed:.1f}s: {str(e)}")

