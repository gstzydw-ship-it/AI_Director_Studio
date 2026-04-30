"""
原生视频分析测试 (尝试不同的 payload 格式和不使用代理)
"""
import base64
import os
import sys
import time
import httpx

# ── 代理配置 (尝试不使用代理，或者使用代理) ──
# 有些中转站对大体积的 base64 代理会断开连接 (SSL EOF)，我们这里尝试两种方式
PROXY_URL = "http://127.0.0.1:9674"
API_KEY = "sk-REDACTED"
BASE_URL = "https://ai.comfly.chat/v1"
MODEL = "gemini-2.5-flash"

VIDEO_PATH = r"E:\项目1\分镜图\jimeng-2026-04-07-5674-为时知渺人物形象参考 为徐斯礼人物形象参考 为执法人员形象参考 为派出所内的女孩....mp4"

def safe_print(text):
    try:
        print(text)
    except UnicodeEncodeError:
        sys.stdout.buffer.write(text.encode("utf-8", errors="replace"))
        sys.stdout.buffer.write(b"\n")
        sys.stdout.buffer.flush()

def make_request(use_proxy, format_type, video_b64):
    timeout = httpx.Timeout(300.0)
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json",
    }
    
    # 不同的中转站对上传视频的结构支持不同
    if format_type == "image_url":
        payload = {
            "model": MODEL,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "简要描述画面人物及运动方向。"},
                        {
                            "type": "image_url",
                            "image_url": {"url": f"data:video/mp4;base64,{video_b64}"}
                        }
                    ]
                }
            ]
        }
    elif format_type == "inlineData":
        payload = {
            "model": MODEL,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "简要描述画面人物及运动方向。"},
                        {
                            "type": "inlineData",
                            "inlineData": {"mimeType": "video/mp4", "data": video_b64}
                        }
                    ]
                }
            ]
        }

    proxies = {"http://": PROXY_URL, "https://": PROXY_URL} if use_proxy else None
    
    print(f"\n--- 测试: 以 {format_type} 格式({'通过代理' if use_proxy else '直连'}) ---")
    t0 = time.time()
    try:
        if proxies:
            client = httpx.Client(proxies=proxies, timeout=timeout)
        else:
            client = httpx.Client(timeout=timeout)
            
        with client as c:
            r = c.post(f"{BASE_URL}/chat/completions", headers=headers, json=payload)
        
        elapsed = time.time() - t0
        print(f"  HTTP: {r.status_code} ({elapsed:.1f}s)")
        if r.status_code == 200:
            result = r.json()["choices"][0]["message"]["content"]
            safe_print(f"  Result: {result[:50]}")
            return True
        else:
            safe_print(f"  Error: {r.text[:200]}")
            return False
    except Exception as e:
        safe_print(f"  Failed: {e}")
        return False

def main():
    if not os.path.exists(VIDEO_PATH):
        print(f"文件没找到: {VIDEO_PATH}")
        return

    print("读取视频转 Base64...")
    with open(VIDEO_PATH, "rb") as f:
        video_b64 = base64.b64encode(f.read()).decode()
    print(f"大小: {len(video_b64)/1024/1024:.2f} MB")

    # 我们测试使用不同的组合
    for use_proxy in [True, False]:
        for fmt in ["image_url", "inlineData"]:
            success = make_request(use_proxy, fmt, video_b64)
            if success:
                print("\n✅ 测试通过！")
                return

if __name__ == "__main__":
    main()

