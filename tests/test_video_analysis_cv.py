"""
测试 Gemini 2.5 Flash 视频分析（OpenCV 抽帧版）
用 OpenCV 从视频抽取关键帧 -> 多图发送给 Gemini
无需 ffmpeg
"""
import base64
import io
import os
import sys
import time

import cv2
import httpx

# ── 代理配置（从 test_proxy.py 同步）──
os.environ["HTTP_PROXY"] = "http://127.0.0.1:9674"
os.environ["HTTPS_PROXY"] = "http://127.0.0.1:9674"
os.environ["NO_PROXY"] = "ai.comfly.chat,127.0.0.1"

# ── 配置 ──────────────────────────────────────────
API_KEY = "sk-REDACTED"
BASE_URL = "https://ai.comfly.chat/v1"
MODEL = "gpt-4o-mini"  # gemini-2.5-flash has 429 quota issues, fallback to gpt-4o-mini

VIDEO_PATH = r"E:\AI_Director_Studio_Full_Backup\output\segment1_v2.mp4"

ANALYSIS_PROMPT = (
    "你是视频空间连续性分析师。以下是一段AI生成视频的多个关键帧截图，按时间顺序排列。\n\n"
    "请仔细分析这些帧的时序变化，重点关注：\n"
    "1. 【运动方向】人物从画面的哪个方向出现？朝哪个方向移动？运动轨迹是什么？\n"
    "2. 【空间轴线】关键空间锚点（门/入口/电梯/走廊等）分别在画面的什么方向？\n"
    "3. 【最终状态】最后一帧中人物的位置、朝向、姿态\n"
    "4. 【续接约束】如果要续接下一段视频，首帧的人物必须从什么位置/朝向/姿态开始？"
    "特别注意运动方向的连续性——如果人物朝右走，下一段应该继续朝右而不是突然朝左。\n\n"
    "请用中文要点式输出，不超过400字。"
)

timeout = httpx.Timeout(300.0, connect=30.0, read=300.0, write=30.0)
headers = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json",
}


def extract_frames_opencv(video_path, num_frames=5, max_px=512):
    """用 OpenCV 从视频中均匀抽取关键帧"""
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        print(f"  ERROR: Cannot open video: {video_path}")
        return []

    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    fps = cap.get(cv2.CAP_PROP_FPS)
    duration = total_frames / fps if fps > 0 else 0
    w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

    print(f"  Video info: {w}x{h}, {fps:.1f}fps, {total_frames} frames, {duration:.1f}s")

    # 均匀抽帧的帧号
    frame_indices = [int(i * (total_frames - 1) / (num_frames - 1)) for i in range(num_frames)]

    frames = []
    for i, idx in enumerate(frame_indices):
        cap.set(cv2.CAP_PROP_POS_FRAMES, idx)
        ret, frame = cap.read()
        if not ret:
            print(f"  Frame {i+1}: FAILED at frame #{idx}")
            continue

        # 缩放
        fh, fw = frame.shape[:2]
        if max(fw, fh) > max_px:
            scale = max_px / max(fw, fh)
            frame = cv2.resize(frame, (int(fw * scale), int(fh * scale)))

        # 编码为 JPEG
        _, buf = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
        b64 = base64.b64encode(buf.tobytes()).decode("utf-8")
        ts = idx / fps if fps > 0 else 0
        frames.append((b64, ts))
        size_kb = len(buf) / 1024
        print(f"  Frame {i+1}: t={ts:.1f}s, frame#{idx} ({size_kb:.0f} KB)")

    cap.release()
    return frames


def send_frames_to_gemini(frames):
    """将多帧图片发送给 Gemini 进行分析"""
    content_parts = []
    frame_desc = "\n".join(f"- Frame {i+1}: t={ts:.1f}s" for i, (_, ts) in enumerate(frames))
    content_parts.append({
        "type": "text",
        "text": f"Time-ordered video frames ({len(frames)} total):\n{frame_desc}\n\n{ANALYSIS_PROMPT}"
    })
    for b64, _ts in frames:
        content_parts.append({
            "type": "image_url",
            "image_url": {"url": f"data:image/jpeg;base64,{b64}"}
        })

    payload = {
        "model": MODEL,
        "messages": [{"role": "user", "content": content_parts}],
        "temperature": 0.2,
    }

    total_size = sum(len(b) for b, _ in frames) / 1024
    print(f"\n  Sending {len(frames)} frames to {MODEL} ({total_size:.0f} KB total)...")
    t0 = time.time()
    with httpx.Client(timeout=timeout) as client:
        resp = client.post(f"{BASE_URL}/chat/completions", headers=headers, json=payload)
    elapsed = time.time() - t0
    print(f"  HTTP {resp.status_code} ({elapsed:.1f}s)")

    if resp.status_code == 200:
        result = resp.json()
        content = result["choices"][0]["message"]["content"]
        return content
    else:
        print(f"  Error: {resp.text[:500]}")
        return None


def main():
    print("=" * 60)
    print("  Gemini 2.5 Flash 视频分析测试 (OpenCV)")
    print("=" * 60)

    if not os.path.exists(VIDEO_PATH):
        print(f"\nFile not found: {VIDEO_PATH}")
        return

    size_mb = os.path.getsize(VIDEO_PATH) / 1024 / 1024
    print(f"\nVideo: {os.path.basename(VIDEO_PATH)}")
    print(f"Size:  {size_mb:.1f} MB")
    print(f"Model: {MODEL}")
    print(f"API:   {BASE_URL}")

    # 抽帧
    print("\n--- Extracting frames with OpenCV ---")
    frames = extract_frames_opencv(VIDEO_PATH, num_frames=5, max_px=512)

    if not frames:
        print("\nNo frames extracted!")
        return

    print(f"\nExtracted {len(frames)} frames successfully!")

    # 发送给 Gemini
    print("\n--- Sending to Gemini 2.5 Flash ---")
    try:
        result = send_frames_to_gemini(frames)
    except Exception as e:
        print(f"\nRequest failed: {e}")
        import traceback
        traceback.print_exc()
        return

    if result:
        print("\n" + "=" * 60)
        print("  Analysis Result:")
        print("=" * 60)
        try:
            print(result)
        except UnicodeEncodeError:
            sys.stdout.buffer.write(result.encode("utf-8"))
            sys.stdout.buffer.write(b"\n")
        print("\n" + "=" * 60)
        print("  ✅ Test PASSED!")
        print("=" * 60)
    else:
        print("\n  ❌ Test FAILED!")


if __name__ == "__main__":
    main()

