"""测试 Gemini streaming 模式"""
import os, httpx, time, sys, json

os.environ["HTTP_PROXY"] = "http://127.0.0.1:9674"
os.environ["HTTPS_PROXY"] = "http://127.0.0.1:9674"

API_KEY = "sk-REDACTED"
BASE_URL = "https://ai.comfly.chat/v1"

timeout = httpx.Timeout(300.0, connect=30.0, read=300.0, write=30.0)
headers = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json",
}


def test_streaming(model):
    """用 SSE streaming 模式测试"""
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": "Say hello in Chinese, max 10 words."}],
        "temperature": 0.2,
        "max_tokens": 50,
        "stream": True,  # 关键：stream 模式
    }

    print(f"\nTesting {model} (streaming)...", flush=True)
    t0 = time.time()
    try:
        with httpx.Client(timeout=timeout) as c:
            with c.stream("POST", f"{BASE_URL}/chat/completions", headers=headers, json=payload) as resp:
                print(f"  Connected: HTTP {resp.status_code} ({time.time()-t0:.1f}s)")
                if resp.status_code != 200:
                    print(f"  Error: {resp.read().decode()[:200]}")
                    return False

                full_content = ""
                for line in resp.iter_lines():
                    if not line or not line.startswith("data: "):
                        continue
                    data = line[6:]
                    if data.strip() == "[DONE]":
                        break
                    try:
                        chunk = json.loads(data)
                        delta = chunk.get("choices", [{}])[0].get("delta", {})
                        content = delta.get("content", "")
                        if content:
                            full_content += content
                    except json.JSONDecodeError:
                        pass

                elapsed = time.time() - t0
                print(f"  Result ({elapsed:.1f}s): {full_content}")
                return True

    except Exception as e:
        elapsed = time.time() - t0
        print(f"  FAILED ({elapsed:.1f}s): {e}")
        return False


def test_non_streaming(model):
    """对比：非 stream 模式"""
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": "Say hello in Chinese, max 10 words."}],
        "temperature": 0.2,
        "max_tokens": 50,
        "stream": False,
    }

    print(f"\nTesting {model} (non-streaming)...", flush=True)
    t0 = time.time()
    try:
        with httpx.Client(timeout=timeout) as c:
            r = c.post(f"{BASE_URL}/chat/completions", headers=headers, json=payload)
        elapsed = time.time() - t0
        print(f"  HTTP {r.status_code} ({elapsed:.1f}s)")
        if r.status_code == 200:
            msg = r.json()["choices"][0]["message"]["content"]
            print(f"  Result: {msg}")
            return True
        else:
            print(f"  Error: {r.text[:200]}")
            return False
    except Exception as e:
        print(f"  FAILED ({time.time()-t0:.1f}s): {e}")
        return False


print("=" * 50)
print("  Gemini Streaming vs Non-Streaming Test")
print("=" * 50)

# 先测 gpt-4o-mini 作为对照
test_non_streaming("gpt-4o-mini")

# 测 Gemini streaming
ok_stream = test_streaming("gemini-2.5-flash")

# 测 Gemini non-streaming
ok_nostream = test_non_streaming("gemini-2.5-flash")

print("\n" + "=" * 50)
print(f"  Gemini streaming:     {'PASS' if ok_stream else 'FAIL'}")
print(f"  Gemini non-streaming: {'PASS' if ok_nostream else 'FAIL'}")
print("=" * 50)

