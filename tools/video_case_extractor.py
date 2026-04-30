"""
逐镜头拆片学习器 (Video Case Extractor)

从教学视频中提取逐镜头的导演决策案例，而不是通用规则。
产出格式为结构化 Markdown（内嵌 YAML），直接注入 knowledge/cases/ 供 Agent 检索。

与 batch_video_learner.py 的区别：
  - batch_video_learner  → 提取通用规则（"什么时候该怎么做"）
  - video_case_extractor → 提取具体案例（"导演实际拍了哪几个镜头，为什么"）

使用方法：
  python tools/video_case_extractor.py                    # 处理所有未提取的视频
  python tools/video_case_extractor.py --video "xxx.mp4"  # 处理单个视频
  python tools/video_case_extractor.py --rerun             # 重新处理所有视频
"""

import os
import sys
import base64
import yaml
import requests
import json
import time
import re
import argparse
from datetime import datetime

# ── 路径配置 ──────────────────────────────────────────────
# 自动定位项目根目录
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)

CASES_DIR = os.path.join(PROJECT_ROOT, "knowledge", "cases")
RECORD_JSON = os.path.join(PROJECT_ROOT, "knowledge", "case_extraction_records.json")
VIDEO_RECORDS_JSON = os.path.join(PROJECT_ROOT, "knowledge", "video_learning_records.json")
CONFIG_PATH = os.path.join(PROJECT_ROOT, "config", "settings.yaml")

COMFLY_BASE_URL = "https://ai.comfly.chat/v1"

# ── 提取 Prompt ──────────────────────────────────────────
CASE_EXTRACTION_PROMPT = """你是一位专业的电影分镜拆片分析师。请认真观看这段教学视频，完成以下两个任务：

## 任务一：逐镜头拆解

从视频中找出所有被展示或讲解的**拍摄案例片段**（不是理论讲解部分，而是有实际画面的示范片段）。
对每个案例片段，按时间顺序逐镜头拆解，记录：

- **镜头序号**（按出现顺序）
- **估计时长**（秒）
- **景别**：全景/中景/中近景/近景/特写/大特写
- **角度**：平视/仰拍/俯拍/过肩/主观POV/低机位
- **运镜**：固定/缓推/缓拉/摇摄/跟拍/手持/升格
- **构图要点**：人物在画面中的位置、前景遮挡、景深关系等
- **叙事功能**：这个镜头在叙事中的作用（建立空间、信息传递、情绪受击、关系揭示等）
- **切换原因**：为什么在这里切到下一个镜头

## 任务二：模式总结

分析这组镜头序列的整体模式：
- **场景类型标签**（如：冷战对峙、追逐紧张、日常压缩、告别离场、冲突爆发、悬念建立等）
- **核心视觉节奏**（如：稳→推→切→停 或 快切→慢推→定格）
- **导演意图总结**（2-3句话概括这组镜头序列为什么有效）
- **可复用模式**（用一句话概括可直接套用的模式，如"冷战戏=双人中景开场→过肩保留关系→短特写受击→关系景收尾"）

## 输出格式（严格 YAML）

```yaml
cases:
  - case_title: "案例标题（简短描述场景内容）"
    scene_type: "场景类型标签"
    emotional_arc: "情绪弧线（如：平静→紧张→爆发）"
    duration_estimate: "估计总时长（秒）"
    shots:
      - index: 1
        duration: "3s"
        scale: "中景"
        angle: "平视"
        movement: "固定"
        composition: "双人左右对称，中间空隙大"
        narrative_function: "建立空间关系，暗示心理距离"
        cut_reason: "角色A开口说话"
      - index: 2
        duration: "2s"
        scale: "近景"
        angle: "过肩"
        movement: "极慢推"
        composition: "角色B肩膀占画面左1/4"
        narrative_function: "对白传递+压力渐进"
        cut_reason: "需要看听者反应"
    pattern_summary:
      rhythm: "稳定→渐进→快切→留白"
      director_intent: "通过景别递进制造心理压迫，用短特写承接受击"
      reusable_pattern: "冷战戏=双人中景→过肩中近景→短特写受击→关系景收尾"
```

要求：
1. 只提取视频中有实际画面展示的案例，纯理论讲解部分跳过
2. 如果视频中包含多个案例片段，分别拆解，每个作为独立 case
3. 如果视频太短或只有理论没有示范画面，在 case_title 中标注"纯理论-无示范画面"
4. 景别、角度、运镜等字段请使用中文
5. 每个镜头的 narrative_function 必须说明**为什么**而不仅仅是**是什么**"""


def load_config():
    """加载项目配置。"""
    config_path = CONFIG_PATH
    # 优先检查 private/settings.local.yaml
    private_path = os.path.join(os.path.dirname(CONFIG_PATH), "private", "settings.local.yaml")
    if os.path.exists(private_path):
        config_path = private_path

    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def load_records():
    """加载已处理记录。"""
    if os.path.exists(RECORD_JSON):
        with open(RECORD_JSON, "r", encoding="utf-8") as f:
            return json.load(f)
    return []


def save_records(records):
    """保存处理记录。"""
    with open(RECORD_JSON, "w", encoding="utf-8") as f:
        json.dump(records, f, ensure_ascii=False, indent=2)


def get_video_list():
    """从 video_learning_records.json 获取已知视频列表。"""
    if not os.path.exists(VIDEO_RECORDS_JSON):
        print(f"[ERROR] 视频记录文件不存在: {VIDEO_RECORDS_JSON}")
        return []
    with open(VIDEO_RECORDS_JSON, "r", encoding="utf-8") as f:
        return json.load(f)


def sanitize_filename(name: str) -> str:
    """将视频文件名转为合法的文件名。"""
    # 去掉路径和扩展名
    name = os.path.splitext(os.path.basename(name))[0]
    # 替换非法字符
    name = re.sub(r'[\\/:*?"<>|]', '_', name)
    # 截断过长的名称
    if len(name) > 60:
        name = name[:60]
    return name


def extract_yaml_from_response(content: str) -> str:
    """从 LLM 响应中提取 YAML 内容。"""
    # 尝试提取 ```yaml ... ``` 块
    yaml_match = re.search(r'```ya?ml\s*\n(.*?)```', content, re.DOTALL)
    if yaml_match:
        return yaml_match.group(1).strip()
    # 如果没有代码块，尝试直接解析
    if content.strip().startswith("cases:"):
        return content.strip()
    return content


def save_case_markdown(video_filename: str, yaml_content: str, raw_response: str):
    """将提取结果保存为 Markdown 文件到 knowledge/cases/ 目录。"""
    os.makedirs(CASES_DIR, exist_ok=True)

    safe_name = sanitize_filename(video_filename)
    output_path = os.path.join(CASES_DIR, f"CASE_{safe_name}.md")

    # 尝试解析 YAML 提取场景类型标签
    scene_types = []
    try:
        parsed = yaml.safe_load(yaml_content)
        if isinstance(parsed, dict) and "cases" in parsed:
            for case in parsed["cases"]:
                if isinstance(case, dict) and "scene_type" in case:
                    scene_types.append(case["scene_type"])
    except Exception:
        pass

    scene_type_str = ", ".join(scene_types) if scene_types else "综合"

    # 构造带 frontmatter 的 Markdown
    frontmatter = f"""---
rule_id: CASE-{safe_name[:30].upper()}
title: "视频拆片案例：{os.path.splitext(os.path.basename(video_filename))[0]}"
doc_type: case_library
rule_type: shot_sequence_case
agent_scope:
  - shot_director
  - shot_director_layout
  - shot_director_blocking
priority: reference
status: active
runtime_retrieval: true
scene_types:
  - {scene_type_str}
source_video: "{video_filename}"
extraction_date: "{datetime.now().strftime('%Y-%m-%d')}"
extraction_model: "gemini-3.1-pro-preview-thinking-high"
---"""

    content = f"""{frontmatter}

# 视频拆片案例：{os.path.splitext(os.path.basename(video_filename))[0]}

> 本文件由 video_case_extractor.py 自动生成，从教学视频中提取逐镜头的导演决策案例。

## 结构化案例数据

```yaml
{yaml_content}
```

## 原始分析

{raw_response}
"""

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(content)

    print(f"   [SAVE] 案例已保存: {output_path}")
    return output_path


def process_video(video_path: str, api_key: str, model: str) -> bool:
    """处理单个视频，提取逐镜头案例。"""
    filename = os.path.basename(video_path)
    url = f"{COMFLY_BASE_URL}/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    # 读取并编码视频
    try:
        file_size = os.path.getsize(video_path)
        if file_size > 100 * 1024 * 1024:  # 100MB 限制
            print(f"   [SKIP] 文件过大 ({file_size // 1024 // 1024}MB)，跳过")
            return False

        with open(video_path, "rb") as f:
            video_b64 = base64.b64encode(f.read()).decode("utf-8")
    except Exception as e:
        print(f"   [ERROR] 读取文件失败: {e}")
        return False

    payload = {
        "model": model,
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": CASE_EXTRACTION_PROMPT},
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:video/mp4;base64,{video_b64}"},
                    },
                ],
            }
        ],
        "temperature": 0.2,
        "max_tokens": 16384,
    }

    retries = 3
    for attempt in range(retries):
        try:
            print(f"   [REQ] 第 {attempt + 1}/{retries} 次请求 ({model})...")
            response = requests.post(
                url,
                headers=headers,
                json=payload,
                proxies={"http": None, "https": None},
                timeout=900,  # 15 分钟超时，Gemini 视频分析需要更长时间
            )

            if response.status_code == 200:
                resp_json = response.json()
                content = resp_json["choices"][0]["message"].get("content", "")

                if not content:
                    print(f"   [WARN] 返回内容为空（可能触发安全拦截）")
                    time.sleep(10)
                    continue

                # 提取 YAML 部分
                yaml_content = extract_yaml_from_response(content)

                # 验证 YAML 可解析
                try:
                    parsed = yaml.safe_load(yaml_content)
                    if not isinstance(parsed, dict) or "cases" not in parsed:
                        print(f"   [WARN] YAML 结构不符合预期，保存原始内容")
                except yaml.YAMLError as e:
                    print(f"   [WARN] YAML 解析失败: {e}，保存原始内容")

                # 保存结果
                save_case_markdown(filename, yaml_content, content)
                return True

            elif response.status_code == 429:
                wait = 30
                print(f"   [WAIT] 触发限流，等待 {wait}s...")
                time.sleep(wait)
            else:
                print(f"   [WARN] HTTP {response.status_code}: {response.text[:200]}")
                time.sleep(10)

        except requests.exceptions.ReadTimeout:
            print(f"   [WARN] 请求超时 (900s)")
            time.sleep(15)
        except requests.exceptions.ConnectionError as e:
            print(f"   [WARN] 连接错误: {e}")
            time.sleep(15)
        except Exception as e:
            print(f"   [ERROR] 未知异常: {e}")
            import traceback
            traceback.print_exc()
            time.sleep(15)

    return False


def main():
    parser = argparse.ArgumentParser(description="逐镜头拆片学习器")
    parser.add_argument("--video", type=str, help="处理指定视频文件路径")
    parser.add_argument("--rerun", action="store_true", help="重新处理所有视频")
    parser.add_argument("--model", type=str, default=None, help="覆盖使用的模型名称")
    parser.add_argument("--dry-run", action="store_true", help="只显示待处理列表，不实际执行")
    args = parser.parse_args()

    print("=" * 60)
    print("  逐镜头拆片学习器 (Video Case Extractor)")
    print("  从教学视频中提取导演决策案例")
    print("=" * 60)

    # 加载配置
    config = load_config()
    v_config = config["agent_models"]["video_analyst"]
    api_key = v_config["api_key"]
    model = args.model or v_config.get("model", "gemini-3.1-pro-preview-thinking-high")

    print(f"\n[CONFIG] model={model}")
    print(f"[CONFIG] cases_dir={CASES_DIR}")

    # 确定待处理视频列表
    if args.video:
        if not os.path.exists(args.video):
            print(f"[ERROR] 视频文件不存在: {args.video}")
            sys.exit(1)
        videos = [args.video]
    else:
        videos = get_video_list()

    if not videos:
        print("[ERROR] 没有找到待处理的视频")
        sys.exit(1)

    # 加载已处理记录
    records = [] if args.rerun else load_records()
    pending = [v for v in videos if v not in records]

    print(f"\n[INFO] 共 {len(videos)} 个视频，已处理 {len(records)} 个，待处理 {len(pending)} 个")

    if args.dry_run:
        print("\n[DRY-RUN] 待处理视频列表:")
        for i, v in enumerate(pending, 1):
            print(f"  {i}. {os.path.basename(v)}")
        return

    if not pending:
        print("[INFO] 所有视频已处理完毕！")
        return

    # 创建 cases 目录
    os.makedirs(CASES_DIR, exist_ok=True)

    # 逐个处理
    success_count = 0
    fail_count = 0

    for i, v_path in enumerate(pending, 1):
        filename = os.path.basename(v_path)
        print(f"\n{'─' * 50}")
        print(f"[{i}/{len(pending)}] 正在拆片: {filename}")
        print(f"{'─' * 50}")

        if not os.path.exists(v_path):
            print(f"   [SKIP] 文件不存在: {v_path}")
            fail_count += 1
            continue

        success = process_video(v_path, api_key, model)

        if success:
            records.append(v_path)
            save_records(records)
            success_count += 1
            print(f"   [OK] 拆片完成")
        else:
            fail_count += 1
            print(f"   [FAIL] 拆片失败，将在下次运行重试")

        # 请求间隔，避免限流
        if i < len(pending):
            wait = 5
            print(f"   [WAIT] 等待 {wait}s 后继续...")
            time.sleep(wait)

    print(f"\n{'=' * 60}")
    print(f"  拆片完成！成功 {success_count} / 失败 {fail_count} / 总计 {len(pending)}")
    print(f"  案例文件目录: {CASES_DIR}")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    main()
