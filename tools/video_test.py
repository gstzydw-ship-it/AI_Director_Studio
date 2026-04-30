import base64
import yaml
import requests
import json
import os
import sys

COMFLY_BASE_URL = "https://ai.comfly.chat/v1"

def main():
    config_path = r"E:\AI_Director_Studio_Pack_20260416\AI_Director_Studio\config\settings.yaml"
    with open(config_path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    v_config = config["agent_models"]["video_analyst"]
    api_key = v_config["api_key"]
    base_url = f"{COMFLY_BASE_URL}/chat/completions"
    
    # 直接强制指定使用截图中的验证型号
    model = "gemini-3.1-flash-lite-preview"

    video_path = r"E:\学习合集\douyin_video_pending_2026-04-02_26.mp4"

    if not os.path.exists(video_path):
        print(f"未找到视频文件: {video_path}")
        return

    print(f"[INFO] 正在读取视频: {video_path}")
    with open(video_path, "rb") as f:
        video_b64 = base64.b64encode(f.read()).decode('utf-8')

    print(f"[INFO] 视频加载完毕。Base64 大小: {len(video_b64) / 1024 / 1024:.2f} MB")

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    prompt = """你是一位电影分镜大师。请认真观看并听取这段视频中的画面与教学解说。
请结合画面中展示的具体景别递进、机位调度，以及讲解词，为您手下的执行导演提炼出 3-5 条顶级的、能直接用于微短剧高压强情节拍摄的【分镜规则】与【情绪压迫感调度手法】。

输出请使用 Markdown 格式，要求：
1. 必须精准描述出什么情况用什么景别
2. 重点突出，话术可以直接作为导演手册的硬性指令或准则。"""

    payload = {
        "model": model,
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:video/mp4;base64,{video_b64}"
                        }
                    }
                ]
            }
        ],
        "temperature": 0.2
    }

    print(f"[INFO] 正在发送至大模型 {model} (这可能需要一分钟左右)...")
    try:
        # 显式绕过本地代理，防止 Clash/V2ray 截断 9MB 这么大的 Base64
        response = requests.post(
            base_url, 
            headers=headers, 
            json=payload,
            proxies={"http": None, "https": None}
        )
        if response.status_code == 200:
            result = response.json()
            content = result["choices"][0]["message"]["content"]
            print("\n" + "="*50)
            print("======== 大模型提取结果 ========")
            print("="*50 + "\n")
            # 因为控制台可能乱码，安全起见我们存到文件里
            out_path = r"E:\AI_Director_Studio_Pack_20260416\AI_Director_Studio\knowledge\测试提取_单片运行测试.md"
            with open(out_path, "w", encoding="utf-8") as f:
                f.write(content)
            print(f"[OK] 已经保存提取到的分镜知识到: {out_path}")
            # 同时也打印一下，忽略特殊字符
            print(content.encode('gbk', 'ignore').decode('gbk'))
        else:
            print(f"[ERROR] 响应错误码: {response.status_code}")
            print(f"[ERROR] 详情: {response.text}")
            print("\n注：如果报 413 Payload Too Large，说明该中转 API 无法承受 9MB 左右的单次请求。")
    except Exception as e:
        print(f"[ERROR] 代码异常: {e}")

if __name__ == "__main__":
    main()
