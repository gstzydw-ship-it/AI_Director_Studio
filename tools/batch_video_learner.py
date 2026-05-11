import os
import base64
import yaml
import requests
import json
import time

COMFLY_BASE_URL = "https://ai.comfly.chat/v1"

KNOWLEDGE_KBASE = r"E:\AI_Director_Studio_Pack_20260416\AI_Director_Studio\knowledge\23_视频教学提取_全场景分镜与转场库.md"
RECORD_JSON = r"E:\AI_Director_Studio_Pack_20260416\AI_Director_Studio\knowledge\video_learning_records.json"
VIDEO_DIR = r"E:\学习合集"
CONFIG_PATH = r"E:\AI_Director_Studio_Pack_20260416\AI_Director_Studio\config\settings.yaml"

def load_records():
    if os.path.exists(RECORD_JSON):
        with open(RECORD_JSON, "r", encoding="utf-8") as f:
            return json.load(f)
    return []

def save_record(records, new_record):
    records.append(new_record)
    with open(RECORD_JSON, "w", encoding="utf-8") as f:
        json.dump(records, f, ensure_ascii=False, indent=2)

def append_to_kbase(title, content):
    # 如果文件不存在，加一个头部
    if not os.path.exists(KNOWLEDGE_KBASE):
        with open(KNOWLEDGE_KBASE, "w", encoding="utf-8") as f:
            f.write("# 视频教学提炼：全场景分镜与转场库\n\n")
            f.write("此百科全书由视觉大模型看懂教学视频后自动生成，含有最高密度的微短剧分镜法则。\n\n")

    with open(KNOWLEDGE_KBASE, "a", encoding="utf-8") as f:
        f.write(f"\n\n## 【案例来源】{title}\n\n")
        f.write(content)
        f.write("\n\n---\n")

def main():
    print("[INFO] 开始批量视听学习任务...")
    
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    v_config = config["agent_models"]["video_analyst"]
    api_key = v_config["api_key"]
    base_url = f"{COMFLY_BASE_URL}/chat/completions"
    
    model = "gemini-3.1-flash-lite-preview"

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    records = load_records()
    
    # 寻找所有视频
    videos = []
    for root, _, files in os.walk(VIDEO_DIR):
        for file in files:
            if file.lower().endswith(".mp4"):
                videos.append(os.path.join(root, file))

    print(f"[INFO] 共发现 {len(videos)} 个视频，已处理记录中有 {len(records)} 个。")

    for i, v_path in enumerate(videos):
        if v_path in records:
            continue
            
        filename = os.path.basename(v_path)
        print(f"\n({i+1}/{len(videos)}) 正在提炼: {filename}")
        
        try:
            with open(v_path, "rb") as f:
                video_b64 = base64.b64encode(f.read()).decode('utf-8')
        except Exception as e:
            print(f"   [ERROR] 读取文件失败 {filename}: {e}")
            continue

        prompt = """你是一位电影级的分镜与调度大师。请认真观看这段视频的画面，并认真听取视频中的教学解说词。
请结合画面中直观展示的具体运镜轨迹、景别变化、机位调度，以及相应的讲解核心，为人工作业的微短剧执行导演提炼出 1-3 条顶尖的、可复用落地的【金牌分镜规则】或【视觉转场手法】。

输出格式必须严格符合：
1. 不要口水话和寒暄，直接用 Markdown 列表形式输出规则条目。
2. 每条规则包含两部分：【适用场景条件】和【具体执行指令】。
3. 执行指令必须能当做镜头剧本里的一句话（例如：机位放在角色后方过肩，镜头向面部缓推）。"""

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
            "temperature": 0.3
        }

        retries = 3
        success = False
        for r in range(retries):
            try:
                # 显式绕过代理，把超时放宽到 600 秒
                response = requests.post(base_url, headers=headers, json=payload, proxies={"http": None, "https": None}, timeout=600)
                if response.status_code == 200:
                    try:
                        resp_json = response.json()
                        content = resp_json["choices"][0]["message"].get("content", "")
                    except Exception as e:
                        print(f"   [ERROR] JSON 解析异常: {e}, 返回内容为: {response.text[:200]}")
                        content = None
                    
                    if not content:
                        print(f"   [WARN] 第 {r+1} 次请求返回的 content 为空 (可能触发了安全拦截): \n{response.text[:500]}")
                        time.sleep(5)
                        continue
                    
                    # 避免控制台乱码导致崩溃
                    safe_content = content[:30].strip().encode('gbk', 'ignore').decode('gbk')
                    try:
                        print(f"   [OK] 成功提取分镜法则！缩影: {safe_content}...")
                    except Exception:
                        print(f"   [OK] 成功提取分镜法则！")
                    
                    append_to_kbase(filename, content)
                    save_record(records, v_path)
                    success = True
                    break
                else:
                    code = response.status_code
                    text = response.text
                    print(f"   [WARN] 响应异常 {code}: {text[:100]}")
                    time.sleep(5)
            except requests.exceptions.ReadTimeout:
                print(f"   [WARN] 第 {r+1} 次请求超时断流 (已等待600秒) ！")
                time.sleep(5)
            except Exception as e:
                import traceback
                print(f"   [WARN] 第 {r+1} 次请求发生未知代码异常断流: {e}")
                traceback.print_exc()
                time.sleep(10)
        
        if not success:
            print(f"   [ERROR] 放弃处理 [{filename}]，已超过最大重试次数。将在下次运行重试。")

    print("\n[DONE] 批量处理完毕或中途手动结束！")
    print("[INFO] 任务已完成！(已为了您的早晨工作安全，注释掉了自动关机代码)")
    # os.system("shutdown /s /t 60")

if __name__ == "__main__":
    main()
