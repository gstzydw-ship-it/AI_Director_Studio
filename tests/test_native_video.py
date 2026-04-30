"""
原生视频分析测试脚本 (Native Video Analysis)
不使用 OpenCV 抽帧，而是直接将 MP4 视频转为 base64 发送给 comfly.chat。
"""
import base64
import os
import sys
import time
import httpx

# ── 代理配置 ──
os.environ["HTTP_PROXY"] = "http://127.0.0.1:9674"
os.environ["HTTPS_PROXY"] = "http://127.0.0.1:9674"
os.environ["NO_PROXY"] = "ai.comfly.chat,127.0.0.1"

# ── 配置 ──
API_KEY = "sk-REDACTED"
BASE_URL = "https://ai.comfly.chat/v1"
MODEL = "gemini-2.5-flash"

VIDEO_PATH = r"E:\项目1\分镜图\jimeng-2026-04-07-5674-为时知渺人物形象参考 为徐斯礼人物形象参考 为执法人员形象参考 为派出所内的女孩....mp4"

PROMPT = (
    "请分析一下这段视频，重点说明画面中人物的位置、姿态和运动情况。"
    "用中文简明扼要地回复即可。"
)

timeout = httpx.Timeout(300.0, connect=30.0, read=300.0, write=300.0)
headers = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json",
}

def safe_print(text):
    try:
        print(text)
    except UnicodeEncodeError:
        sys.stdout.buffer.write(text.encode("utf-8", errors="replace"))
        sys.stdout.buffer.write(b"\n")
        sys.stdout.buffer.flush()

def main():
    print("==================================================")
    print("  Gemini 原生视频分析测试 (Native Video Base64)")
    print("==================================================")

    if not os.path.exists(VIDEO_PATH):
        print(f"Error: 找不到视频文件 -> {VIDEO_PATH}")
        # Search for similar files just in case
        folder = os.path.dirname(VIDEO_PATH)
        if os.path.exists(folder):
            print("\nDirectory contents matching 'jimeng-2026-04-07-5674':")
            for f in os.listdir(folder):
                if "5674" in f:
                    print(f"  - {f}")
        return

    size_mb = os.path.getsize(VIDEO_PATH) / 1024 / 1024
    print(f"File: {os.path.basename(VIDEO_PATH)}")
    print(f"Size: {size_mb:.2f} MB")
    
    print("\n[1] 正在读取视频文件转为 Base64...")
    t0 = time.time()
    with open(VIDEO_PATH, "rb") as f:
        video_b64 = base64.b64encode(f.read()).decode("utf-8")
    print(f"  完毕，耗时 {time.time()-t0:.1f}s, Base64长度: {len(video_b64)/1024/1024:.2f} MB\n")

    # 构造兼容 OpenAI Vision 格式的 Payload (大部分中转站支持用 image_url / url 传递 data:video/mp4;base64)
    payload = {
        "model": MODEL,
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": PROMPT},
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:video/mp4;base64,{video_b64}"
                        }
                    }
                ]
            }
        ],
        "temperature": 0.2,
        "max_tokens": 1024
    }

    print(f"[2] 发送请求到 {BASE_URL} ({MODEL})...")
    t0 = time.time()
    try:
        with httpx.Client(timeout=timeout) as c:
            r = c.post(f"{BASE_URL}/chat/completions", headers=headers, json=payload)
        
        elapsed = time.time() - t0
        print(f"  HTTP 状态码: {r.status_code} (耗时 {elapsed:.1f}s)")
        
        if r.status_code == 200:
            result = r.json()["choices"][0]["message"]["content"]
            safe_print("\n>>> 分析结果:")
            safe_print(result)
            safe_print("\n✅ 原生视频测试成功!")
        else:
            safe_print(f"\n❌ 请求失败 ({r.status_code}):")
            safe_print(r.text[:1000])
            
    except Exception as e:
        safe_print(f"\n❌ 异常错误: {e}")

if __name__ == "__main__":
    main()

