import os
os.environ["HTTP_PROXY"] = "http://127.0.0.1:9674"
os.environ["HTTPS_PROXY"] = "http://127.0.0.1:9674"
os.environ["NO_PROXY"] = "ai.comfly.chat,127.0.0.1,localhost"

from openai import OpenAI
import time

client = OpenAI(
    api_key="sk-REDACTED",
    base_url="https://ai.comfly.chat/v1",
    timeout=300
)

prompt = """Analyze the following screenplay scene and extract: dramatic task, main subject, speakers, info bombs, complete speech units, action segments, spatial relations, character states.

2-1 INT. Tianyu Group Lobby
Characters: Qiaoxi, Shang Beichen, Su Xiaoke, Yan Fei
Shang Beichen walks in, eyes scanning the crowd.
Yan Fei: Welcome, Mr. Pierce.
Shang Beichen: Meeting in ten minutes. Directors and above, be there.
Qiaoxi rushes into the elevator, crashes into Shang Beichen.
Shang Beichen: Long time no see, since when did you start throwing yourself at people?

Please output a structured YAML analysis card with all fields filled."""

print("Sending LONG prompt to claude-opus-4-6...")
start = time.time()
try:
    resp = client.chat.completions.create(
        model="claude-opus-4-6",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=4000
    )
    elapsed = time.time() - start
    content = resp.choices[0].message.content
    print(f"[SUCCESS] in {elapsed:.1f}s, response length: {len(content)} chars")
    print(content[:500])
except Exception as e:
    elapsed = time.time() - start
    print(f"[FAILED] in {elapsed:.1f}s: {str(e)}")

