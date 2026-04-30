"""
测试 Gemini 2.5 Flash 多帧视频分析
使用 ffmpeg 抽帧 -> 多图发送给 Gemini
"""
import base64
import io
import json
import os
import subprocess
import sys
import tempfile
import time

import httpx

API_KEY = "sk-REDACTED"
BASE_URL = "https://ai.comfly.chat/v1"
MODEL = "gemini-2.5-flash"

VIDEO_PATH = r"E:\项目1\分镜图\jimeng-2026-04-07-5674-为时知渺人物形象参考 为徐斯礼人物形象参考 为执法人员形象参考 为派出所内的女孩....mp4"

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

timeout = httpx.Timeout(120.0, connect=30.0, read=120.0, write=30.0)
headers = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json",
}


def extract_frames_ffmpeg(video_path, num_frames=5, max_px=512):
    """Use ffmpeg to extract evenly spaced frames from a video."""
    # Get video duration first
    probe_cmd = [
        "ffprobe", "-v", "quiet", "-print_format", "json",
        "-show_format", "-show_streams", video_path
    ]
    try:
        result = subprocess.run(probe_cmd, capture_output=True, text=True, timeout=10)
        info = json.loads(result.stdout)
        duration = float(info["format"]["duration"])
        print(f"  Video duration: {duration:.1f}s")
    except Exception as e:
        print(f"  Cannot probe video: {e}")
        duration = 6.0  # fallback guess

    # Calculate timestamps for evenly spaced frames
    timestamps = [i * duration / (num_frames - 1) for i in range(num_frames)]
    # Clamp last timestamp slightly before end
    timestamps[-1] = max(0, duration - 0.1)

    frames = []
    with tempfile.TemporaryDirectory() as tmpdir:
        for i, ts in enumerate(timestamps):
            out_path = os.path.join(tmpdir, f"frame_{i:02d}.jpg")
            cmd = [
                "ffmpeg", "-y", "-ss", f"{ts:.2f}",
                "-i", video_path,
                "-frames:v", "1",
                "-vf", f"scale='min({max_px},iw)':min'({max_px},ih)':force_original_aspect_ratio=decrease",
                "-q:v", "3",
                out_path
            ]
            try:
                subprocess.run(cmd, capture_output=True, timeout=10)
            except Exception:
                pass

            if os.path.exists(out_path):
                with open(out_path, "rb") as f:
                    b64 = base64.b64encode(f.read()).decode("utf-8")
                frames.append((b64, ts))
                size_kb = os.path.getsize(out_path) / 1024
                print(f"  Frame {i+1}: t={ts:.1f}s ({size_kb:.0f} KB)")
            else:
                print(f"  Frame {i+1}: FAILED at t={ts:.1f}s")

    return frames


def extract_frames_pillow(video_path, num_frames=5, max_px=512):
    """Fallback: use PIL to extract first/last frame from video (limited)."""
    from PIL import Image

    # Try to use PIL to open first frame only
    try:
        img = Image.open(video_path)
        print(f"  PIL opened video: {img.size}")
        buf = io.BytesIO()
        w, h = img.size
        if max(w, h) > max_px:
            ratio = max_px / max(w, h)
            img = img.resize((int(w*ratio), int(h*ratio)), Image.LANCZOS)
        if img.mode != "RGB":
            img = img.convert("RGB")
        img.save(buf, format="JPEG", quality=80)
        return [(base64.b64encode(buf.getvalue()).decode("utf-8"), 0.0)]
    except Exception as e:
        print(f"  PIL cannot read video: {e}")
        return []


def send_frames_to_gemini(frames):
    """Send multiple frames to Gemini as multi-image content."""
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
    if not os.path.exists(VIDEO_PATH):
        print(f"File not found: {VIDEO_PATH}")
        return

    size_mb = os.path.getsize(VIDEO_PATH) / 1024 / 1024
    print(f"Video: {os.path.basename(VIDEO_PATH)}")
    print(f"Size: {size_mb:.1f} MB")
    print(f"Model: {MODEL}")
    print(f"API: {BASE_URL}")

    # Try ffmpeg first
    print("\n--- Extracting frames with ffmpeg ---")
    frames = extract_frames_ffmpeg(VIDEO_PATH, num_frames=5, max_px=512)

    if not frames:
        print("\n--- ffmpeg failed, trying PIL ---")
        frames = extract_frames_pillow(VIDEO_PATH)

    if not frames:
        print("\nNo frames extracted. Please install ffmpeg.")
        return

    print(f"\nExtracted {len(frames)} frames successfully!")

    # Send to Gemini
    print("\n--- Sending to Gemini 2.5 Flash ---")
    try:
        result = send_frames_to_gemini(frames)
    except Exception as e:
        print(f"Request failed: {e}")
        return

    if result:
        print("\n" + "=" * 60)
        print("Analysis Result:")
        print("=" * 60)
        # Use sys.stdout.buffer for Unicode safety
        try:
            print(result)
        except UnicodeEncodeError:
            sys.stdout.buffer.write(result.encode("utf-8"))
            sys.stdout.buffer.write(b"\n")
        print("\nTest PASSED!")
    else:
        print("\nTest FAILED!")


if __name__ == "__main__":
    main()

