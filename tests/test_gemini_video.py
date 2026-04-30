"""
完整测试 Gemini 2.5 Flash 视频分析
测试两种方式：
1. 多帧抽样（OpenCV 抽帧 → 多图）
2. 原生视频（整个 MP4 base64 直传）
"""
import base64
import os
import sys
import time

import cv2
import httpx

# ── 代理 ──
os.environ["HTTP_PROXY"] = "http://127.0.0.1:9674"
os.environ["HTTPS_PROXY"] = "http://127.0.0.1:9674"
os.environ["NO_PROXY"] = "ai.comfly.chat,127.0.0.1"

# ── 配置 ──
API_KEY = "sk-REDACTED"
BASE_URL = "https://ai.comfly.chat/v1"
MODEL = "gemini-2.5-flash"
VIDEO_PATH = r"E:\AI_Director_Studio_Full_Backup\output\segment1_v2.mp4"

PROMPT = (
    "你是视频空间连续性分析师。请分析这段视频/画面，重点关注：\n"
    "1. 【运动方向】人物朝哪个方向移动？\n"
    "2. 【空间轴线】关键空间锚点的位置\n"
    "3. 【最终状态】最后的位置、朝向、姿态\n"
    "4. 【续接约束】下一段视频首帧应从什么位置/朝向开始？\n"
    "用中文要点式输出，不超过300字。"
)

timeout = httpx.Timeout(300.0, connect=30.0, read=300.0, write=30.0)
headers = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json",
}


def safe_print(text):
    """GBK 终端安全打印"""
    try:
        print(text)
    except UnicodeEncodeError:
        sys.stdout.buffer.write(text.encode("utf-8", errors="replace"))
        sys.stdout.buffer.write(b"\n")
        sys.stdout.buffer.flush()


def extract_frames(video_path, num_frames=5, max_px=512):
    """用 OpenCV 抽帧"""
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        print("  ERROR: Cannot open video")
        return []

    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    fps = cap.get(cv2.CAP_PROP_FPS)
    dur = total / fps if fps > 0 else 0
    w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    print(f"  Video: {w}x{h}, {fps:.0f}fps, {total} frames, {dur:.1f}s")

    indices = [int(i * (total - 1) / (num_frames - 1)) for i in range(num_frames)]
    frames = []
    for i, idx in enumerate(indices):
        cap.set(cv2.CAP_PROP_POS_FRAMES, idx)
        ret, frame = cap.read()
        if not ret:
            continue
        fh, fw = frame.shape[:2]
        if max(fw, fh) > max_px:
            s = max_px / max(fw, fh)
            frame = cv2.resize(frame, (int(fw * s), int(fh * s)))
        _, buf = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
        b64 = base64.b64encode(buf.tobytes()).decode()
        ts = idx / fps if fps > 0 else 0
        frames.append((b64, ts))
        print(f"  Frame {i+1}: t={ts:.1f}s ({len(buf)/1024:.0f}KB)")
    cap.release()
    return frames


# ═══════════════════════════════════════════════
# 测试1: 多帧方式（OpenAI 兼容格式）
# ═══════════════════════════════════════════════
def test_multiframe(frames):
    print("\n" + "=" * 60)
    print("  TEST 1: Multi-frame (OpenAI compatible format)")
    print("=" * 60)

    content_parts = []
    desc = "\n".join(f"- Frame {i+1}: t={ts:.1f}s" for i, (_, ts) in enumerate(frames))
    content_parts.append({
        "type": "text",
        "text": f"Time-ordered video frames ({len(frames)} total):\n{desc}\n\n{PROMPT}",
    })
    for b64, _ in frames:
        content_parts.append({
            "type": "image_url",
            "image_url": {"url": f"data:image/jpeg;base64,{b64}"},
        })

    payload = {
        "model": MODEL,
        "messages": [{"role": "user", "content": content_parts}],
        "temperature": 0.2,
        "max_tokens": 1024,
    }

    total_kb = sum(len(b) for b, _ in frames) / 1024
    print(f"\n  Sending {len(frames)} frames ({total_kb:.0f} KB)...")
    t0 = time.time()
    try:
        with httpx.Client(timeout=timeout) as c:
            r = c.post(f"{BASE_URL}/chat/completions", headers=headers, json=payload)
        elapsed = time.time() - t0
        print(f"  HTTP {r.status_code} ({elapsed:.1f}s)")
        if r.status_code == 200:
            result = r.json()["choices"][0]["message"]["content"]
            safe_print(f"\n  Result:\n{result}")
            return True
        else:
            safe_print(f"  Error: {r.text[:500]}")
            return False
    except Exception as e:
        print(f"  Exception: {e}")
        return False


# ═══════════════════════════════════════════════
# 测试2: 原生视频方式（Gemini inlineData 格式）
# ═══════════════════════════════════════════════
def test_native_video(video_path):
    print("\n" + "=" * 60)
    print("  TEST 2: Native video (base64 MP4 via OpenAI format)")
    print("=" * 60)

    size_mb = os.path.getsize(video_path) / 1024 / 1024
    print(f"\n  Video size: {size_mb:.1f} MB")

    # 读取视频文件并 base64 编码
    with open(video_path, "rb") as f:
        video_b64 = base64.b64encode(f.read()).decode()
    print(f"  Base64 length: {len(video_b64) / 1024:.0f} KB")

    # 方式A: 用 image_url 格式传递 video（一些代理支持）
    payload = {
        "model": MODEL,
        "messages": [{
            "role": "user",
            "content": [
                {"type": "text", "text": PROMPT},
                {
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:video/mp4;base64,{video_b64}"
                    },
                },
            ],
        }],
        "temperature": 0.2,
        "max_tokens": 1024,
    }

    print(f"  Sending native video to {MODEL}...")
    t0 = time.time()
    try:
        with httpx.Client(timeout=timeout) as c:
            r = c.post(f"{BASE_URL}/chat/completions", headers=headers, json=payload)
        elapsed = time.time() - t0
        print(f"  HTTP {r.status_code} ({elapsed:.1f}s)")
        if r.status_code == 200:
            result = r.json()["choices"][0]["message"]["content"]
            safe_print(f"\n  Result:\n{result}")
            return True
        else:
            safe_print(f"  Error: {r.text[:500]}")
            return False
    except Exception as e:
        print(f"  Exception: {e}")
        return False


def main():
    print("=" * 60)
    print("  Gemini 2.5 Flash Video Analysis Test")
    print("=" * 60)

    if not os.path.exists(VIDEO_PATH):
        print(f"File not found: {VIDEO_PATH}")
        return

    size_mb = os.path.getsize(VIDEO_PATH) / 1024 / 1024
    print(f"Video: {os.path.basename(VIDEO_PATH)} ({size_mb:.1f} MB)")
    print(f"Model: {MODEL}")
    print(f"API:   {BASE_URL}")

    # 抽帧
    print("\n--- Extracting frames ---")
    frames = extract_frames(VIDEO_PATH, num_frames=5, max_px=512)
    if not frames:
        print("Frame extraction failed!")
        return

    # 测试1: 多帧
    ok1 = test_multiframe(frames)

    # 测试2: 原生视频
    ok2 = test_native_video(VIDEO_PATH)

    # 结果汇总
    print("\n" + "=" * 60)
    print("  SUMMARY")
    print("=" * 60)
    print(f"  Multi-frame:   {'PASS' if ok1 else 'FAIL'}")
    print(f"  Native video:  {'PASS' if ok2 else 'FAIL'}")
    print("=" * 60)


if __name__ == "__main__":
    main()

