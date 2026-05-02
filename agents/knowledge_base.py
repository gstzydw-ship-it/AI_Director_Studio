"""
向量知识库构建与检索模块
使用 numpy + OpenAI 兼容 Embedding API 实现纯 Python 向量检索
支持 BM25 关键词检索 + 向量语义检索的混合模式
（不依赖 ChromaDB / PyTorch / sentence-transformers）
"""

import os
import re
import json
import numpy as np
import yaml
from openai import OpenAI
try:
    import bm25s
    _HAS_BM25S = True
except ImportError:
    bm25s = None
    _HAS_BM25S = False
from typing import Dict, List, Any

from .utils import COMFLY_BASE_URL, get_config_path, get_knowledge_dir, get_cache_dir, load_yaml_config


def load_config():
    """加载配置文件。

    加入防御：文件缺失、非 UTF-8、YAML 语法错误时都优雅降级到空 dict，而不是让上游崩溃。
    """
    config_path = get_config_path()
    try:
        data = load_yaml_config(config_path)
    except yaml.YAMLError as exc:
        print(f"  [Config] WARN: YAML 解析失败 ({config_path}): {exc}")
        return {}
    except OSError as exc:
        print(f"  [Config] WARN: 无法读取配置 ({config_path}): {exc}")
        return {}
    return data if isinstance(data, dict) else {}


# ---------- Embedding 客户端 ----------

_embed_clients: dict[tuple[str, str], OpenAI] = {}


def _get_embed_client() -> OpenAI:
    """获取 OpenAI 兼容 Embedding 客户端，按 key/base_url 隔离缓存。

    尊重 vectordb.base_url 覆盖——若用户想把 embedding 走另一个中转站（例如阿里百炼或直连
    Moonshot），只要在 settings.local.yaml 里写清 base_url 就可生效。
    """
    config = load_config() or {}
    vdb_config = config.get("vectordb") or {}
    api_key = vdb_config.get("api_key") or ""
    base_url = vdb_config.get("base_url") or COMFLY_BASE_URL
    if not api_key:
        raise RuntimeError("vectordb.api_key 未配置，无法创建 Embedding 客户端。")
    cache_key = (api_key, base_url)
    if cache_key not in _embed_clients:
        _embed_clients[cache_key] = OpenAI(api_key=api_key, base_url=base_url)
    return _embed_clients[cache_key]


def _embedding_vectors_from_response(resp: Any) -> list[list[float]]:
    """兼容标准 SDK 对象、dict 以及 JSON 字符串形态的 embedding 响应。"""
    parsed = resp
    if isinstance(parsed, str):
        try:
            parsed = json.loads(parsed)
        except json.JSONDecodeError as exc:
            raise RuntimeError(
                f"Embedding API 返回了字符串而非标准对象，且不是合法 JSON: {parsed[:200]}"
            ) from exc

    data = getattr(parsed, "data", None)
    if data is None and isinstance(parsed, dict):
        data = parsed.get("data")

    if not isinstance(data, list):
        raise RuntimeError(
            "Embedding API 响应缺少 data 列表，无法解析向量；"
            f"实际类型={type(resp).__name__}"
        )

    vectors: list[list[float]] = []
    for item in data:
        embedding = getattr(item, "embedding", None)
        if embedding is None and isinstance(item, dict):
            embedding = item.get("embedding")
        if not isinstance(embedding, list):
            raise RuntimeError("Embedding API 响应项缺少 embedding 向量列表")
        vectors.append(embedding)
    return vectors



def _embed_texts(texts: list[str], model: str = None, batch_size: int = 20) -> list[list[float]]:
    """调用在线 API 获取文本 Embedding 向量"""
    if model is None:
        config = load_config()
        model = config["vectordb"]["embedding_model"]
    client = _get_embed_client()
    # OpenAI embedding API 单次最多 2048 条，按批处理
    all_embeddings = []
    for i in range(0, len(texts), batch_size):
        batch = texts[i:i + batch_size]
        resp = client.embeddings.create(input=batch, model=model)
        all_embeddings.extend(_embedding_vectors_from_response(resp))
    return all_embeddings


# ---------- Markdown 切片 ----------

def _strip_frontmatter(text: str) -> str:
    """Remove Obsidian/YAML frontmatter before retrieval or full-text injection."""
    text = text.lstrip("\ufeff")
    return re.sub(r"^---\s*\n.*?\n---\s*\n\s*", "", text, count=1, flags=re.DOTALL)


def _frontmatter_metadata(content: str) -> dict[str, Any]:
    content = content.lstrip("\ufeff")
    if not content.startswith("---"):
        return {}
    match = re.match(r"^---\s*\n(.*?)\n---\s*\n", content, flags=re.DOTALL)
    if not match:
        return {}
    try:
        parsed = yaml.safe_load(match.group(1)) or {}
    except Exception:
        return {}
    return parsed if isinstance(parsed, dict) else {}


def _normalise_agent_scope(value: Any) -> list[str]:
    if isinstance(value, str):
        return [item.strip() for item in re.split(r"[,，]", value) if item.strip()]
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    return []


def _iter_knowledge_files(knowledge_dir: str | None = None):
    root = os.path.abspath(knowledge_dir or get_knowledge_dir())
    skipped_dirs = {".obsidian", "_assets", "_indexes", "_templates"}
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in skipped_dirs and not d.startswith(".")]
        for filename in sorted(filenames):
            if not filename.endswith((".md", ".yaml", ".yml")):
                continue
            path = os.path.join(dirpath, filename)
            relpath = os.path.relpath(path, root).replace("\\", "/")
            yield relpath, path


def chunk_markdown(text: str, chunk_size: int = 800, chunk_overlap: int = 100) -> list[dict]:
    """
    将 Markdown 文件按标题层级切分为片段。
    优先按 ## / ### 标题切分，若单个 section 超过 chunk_size 则再按段落切分。
    """
    text = _strip_frontmatter(text)
    sections = re.split(r'\n(?=##\s)', text)
    chunks = []

    for section in sections:
        if not section.strip():
            continue
        title_match = re.match(r'^(#{1,4})\s+(.+)', section.strip())
        title = title_match.group(2).strip() if title_match else ""

        if len(section) <= chunk_size:
            chunks.append({"text": section.strip(), "title": title})
        else:
            paragraphs = section.split("\n\n")
            current_chunk = ""
            for para in paragraphs:
                if len(current_chunk) + len(para) > chunk_size and current_chunk:
                    chunks.append({"text": current_chunk.strip(), "title": title})
                    overlap_text = current_chunk[-chunk_overlap:] if len(current_chunk) > chunk_overlap else ""
                    current_chunk = overlap_text + "\n\n" + para
                else:
                    current_chunk += "\n\n" + para if current_chunk else para
            if current_chunk.strip():
                chunks.append({"text": current_chunk.strip(), "title": title})

    return chunks


def _runtime_retrieval_enabled(content: str) -> bool:
    """
    Return False when a Markdown frontmatter block or YAML header explicitly
    says runtime_retrieval: false.
    """
    metadata: dict[str, Any] | None = _frontmatter_metadata(content)

    if not metadata:
        header = "\n".join(content.splitlines()[:20])
        try:
            parsed = yaml.safe_load(header) or {}
            metadata = parsed if isinstance(parsed, dict) else {}
        except Exception:
            metadata = {}

    return (metadata or {}).get("runtime_retrieval") is not False


RULE_REGISTRY_FILENAME = "rule_registry.yaml"
GLOBAL_RULE_PRIORITIES = {"P0", "P1"}
SOURCE_PREFERENCE_BM25_BOOST = 0.2
SOURCE_PREFERENCE_VECTOR_BOOST = 0.06
SOURCE_PREFERENCE_RRF_BOOST = 0.01
_rule_registry_cache: dict | None = None


def load_rule_registry() -> dict:
    """Load the canonical rule registry used for lightweight retrieval routing."""
    global _rule_registry_cache
    if _rule_registry_cache is not None:
        return _rule_registry_cache

    registry_path = os.path.join(get_knowledge_dir(), RULE_REGISTRY_FILENAME)
    if not os.path.exists(registry_path):
        _rule_registry_cache = {}
        return _rule_registry_cache

    try:
        with open(registry_path, "r", encoding="utf-8") as f:
            registry = yaml.safe_load(f) or {}
    except (yaml.YAMLError, OSError) as exc:
        print(f"  [Registry] WARN: 规则注册表加载失败 ({registry_path}): {exc}")
        registry = {}

    _rule_registry_cache = registry if isinstance(registry, dict) else {}
    return _rule_registry_cache


# ---------- Agent → 知识文件映射 ----------

COMMON_KNOWLEDGE_FILES = [
    "00_知识库优先级与冲突裁决规则.md",
    # rule_registry.yaml 不再全量注入（29K chars / ~7400 tokens），
    # 改由 get_smart_knowledge() → query_rule_registry() 按需检索。
]

AGENT_KNOWLEDGE_MAP = {
    "rhythm_rewrite_director": [
        "09_节奏总控与剧本改写规则.md",
        "15_故事节奏控制规则.md",
        "24_戏剧微粒识别与节奏触发规则.md",
        "06_连续性与安全规则.md",
    ],
    "scene_analyst": [
        "11_场景分析输入卡与导演意图提取.md",
        "15_故事节奏控制规则.md",
        "06_连续性与安全规则.md",
    ],
    "story_planner": [
        "05_剧本拆分与15秒片段规划规则.md",
        "11_场景分析输入卡与导演意图提取.md",
        "15_故事节奏控制规则.md",
        "24_戏剧微粒识别与节奏触发规则.md",
        "06_连续性与安全规则.md",
    ],
    "shot_director": [
        "01_导演分镜总手册.md",
        "02_焦段景深与景别画幅策略.md",
        "03_镜头切换与推进规则.md",
        "04_对白与表演镜头规则.md",
        "06_连续性与安全规则.md",
        "14_动作描述精细化控制规则.md",
        "15_故事节奏控制规则.md",
        "18_情绪锚点与逐段交互与仰拍限制补丁.md",
        "20_镜头库与机位库.md",
        "21_镜头调用规则与多机位模板.md",
        "22_多机位分镜与镜头多样性规则.md",
        "28_全场景分镜与转场案例库.md",
    ],
    "shot_director_layout": [
        "25_镜头摆位主分镜骨架规则.md",
        "02_焦段景深与景别画幅策略.md",
        "04_对白与表演镜头规则.md",
        "06_连续性与安全规则.md",
        "21_镜头调用规则与多机位模板.md",
        "22_多机位分镜与镜头多样性规则.md",
        "28_全场景分镜与转场案例库.md",
    ],
    "shot_director_blocking": [
        "26_动作调度与受击覆盖规则.md",
        "04_对白与表演镜头规则.md",
        "06_连续性与安全规则.md",
        "14_动作描述精细化控制规则.md",
        "18_情绪锚点与逐段交互与仰拍限制补丁.md",
        "21_镜头调用规则与多机位模板.md",
        "28_全场景分镜与转场案例库.md",
    ],
    "shot_director_guard": [
        "27_规则守门与最小修复规则.md",
        "04_对白与表演镜头规则.md",
        "02_焦段景深与景别画幅策略.md",
        "06_连续性与安全规则.md",
        "08_错误纠偏与判例库.md",
        "17_结果质检与回溯修正规则.md",
    ],
    "prompt_compiler": [
        "06_连续性与安全规则.md",
        "07_Seedance输出词典与模型适配.md",
    ],
    "quality_inspector": [
        "03_镜头切换与推进规则.md",
        "04_对白与表演镜头规则.md",
        "05_剧本拆分与15秒片段规划规则.md",
        "06_连续性与安全规则.md",
        "08_错误纠偏与判例库.md",
        "15_故事节奏控制规则.md",
        "17_结果质检与回溯修正规则.md",
        "24_戏剧微粒识别与节奏触发规则.md",
        "20_镜头库与机位库.md",
        "21_镜头调用规则与多机位模板.md",
        "22_多机位分镜与镜头多样性规则.md",
    ],
}

CRITICAL_KNOWLEDGE_MAP = {
    "scene_analyst": [
        # 场景分析师不需要全文注入，靠 hybrid 检索即可
    ],
    "rhythm_rewrite_director": [
        "09_节奏总控与剧本改写规则.md",   # 核心职责文件，必须全文
        "24_戏剧微粒识别与节奏触发规则.md",  # 节奏触发中枢
    ],
    "story_planner": [
        "05_剧本拆分与15秒片段规划规则.md",  # 拆片核心依赖
        "24_戏剧微粒识别与节奏触发规则.md",  # 戏剧微粒与 Hook 判断
        "06_连续性与安全规则.md",          # 连续状态合同
    ],
    "shot_director": [
        "02_焦段景深与景别画幅策略.md",   # 镜头设计核心查表
        "04_对白与表演镜头规则.md",       # 对白覆盖与反应切镜
        "06_连续性与安全规则.md",          # 安全约束必须全文
        "21_镜头调用规则与多机位模板.md",  # 机位调用与执行模板
    ],
    "shot_director_layout": [
        "25_镜头摆位主分镜骨架规则.md",   # 一号机位摆位导演的职责合同
        "02_焦段景深与景别画幅策略.md",   # 景别/焦段/画幅主规则
        "04_对白与表演镜头规则.md",       # 发言单元覆盖蓝图
        "06_连续性与安全规则.md",          # 接缝与状态安全
        "21_镜头调用规则与多机位模板.md",  # 主镜头骨架模板
    ],
    "shot_director_blocking": [
        "26_动作调度与受击覆盖规则.md",   # 二号动作调度导演的职责合同
        "06_连续性与安全规则.md",          # 受击接续需要连续性保障
        "14_动作描述精细化控制规则.md",   # 动作描述精度
        "04_对白与表演镜头规则.md",       # 对白落点规则
    ],
    "shot_director_guard": [
        "27_规则守门与最小修复规则.md",   # 三号守门导演的职责合同
        "04_对白与表演镜头规则.md",       # 对白覆盖守门
        "06_连续性与安全规则.md",          # 连续性违规检查
        "17_结果质检与回溯修正规则.md",   # 质检标准参考
        "08_错误纠偏与判例库.md",         # 常见错误案例
    ],
    "prompt_compiler": [
        "06_连续性与安全规则.md",          # 状态合同翻译与禁止项
        "07_Seedance输出词典与模型适配.md",  # 输出模板，必须全文
        "rules/prompt_compiler/PROMPT-HARD-CONSTRAINT-DEDUP-001.md",  # 约束集中，禁止污染时间轴
        "rules/prompt_compiler/PROMPT-DIRECTOR-JARGON-TRANSLATION-001.md",  # 导演口语转可见画面语言
    ],
    "quality_inspector": [
        "17_结果质检与回溯修正规则.md",    # 质检核心文件
        "05_剧本拆分与15秒片段规划规则.md",  # 片段边界校验
        "06_连续性与安全规则.md",          # 连续性与禁忌校验
        "24_戏剧微粒识别与节奏触发规则.md",  # 戏剧微粒与 Hook 回查
        "rules/quality_inspector/QC-PACING-SAFETY-CHECKLIST-001.md",  # 节奏质检清单
    ],
}

for _files in AGENT_KNOWLEDGE_MAP.values():
    for _common_file in reversed(COMMON_KNOWLEDGE_FILES):
        if _common_file not in _files:
            _files.insert(0, _common_file)

for _files in CRITICAL_KNOWLEDGE_MAP.values():
    for _common_file in reversed(COMMON_KNOWLEDGE_FILES):
        if _common_file not in _files:
            _files.insert(0, _common_file)


def get_agent_knowledge_files(agent_name: str, critical_only: bool = False) -> list[str]:
    source = CRITICAL_KNOWLEDGE_MAP if critical_only else AGENT_KNOWLEDGE_MAP
    files = list(source.get(agent_name, []))

    # Auto-include all rule cards from rules/<agent_name>/ as critical.
    # Rule cards are small (1-2KB), designed as hard constraints, and must always
    # be injected. RAG retrieval consistently fails to surface them because they
    # lose RRF ranking to larger generic documents.
    if critical_only:
        knowledge_dir = get_knowledge_dir()
        agent_rules_dir = os.path.join(knowledge_dir, "rules", agent_name)
        if os.path.isdir(agent_rules_dir):
            for fname in sorted(os.listdir(agent_rules_dir)):
                relpath = f"rules/{agent_name}/{fname}"
                if relpath not in files and fname.endswith(".md"):
                    filepath = os.path.join(agent_rules_dir, fname)
                    try:
                        with open(filepath, "r", encoding="utf-8") as f:
                            content = f.read()
                        if _runtime_retrieval_enabled(content):
                            files.append(relpath)
                    except OSError:
                        continue
        # Also include shared rule cards from rules/shared/
        shared_rules_dir = os.path.join(knowledge_dir, "rules", "shared")
        if os.path.isdir(shared_rules_dir):
            for fname in sorted(os.listdir(shared_rules_dir)):
                relpath = f"rules/shared/{fname}"
                if relpath not in files and fname.endswith(".md"):
                    filepath = os.path.join(shared_rules_dir, fname)
                    try:
                        with open(filepath, "r", encoding="utf-8") as f:
                            content = f.read()
                        if _runtime_retrieval_enabled(content):
                            files.append(relpath)
                    except OSError:
                        continue

        # Cross-folder critical injection by frontmatter agent_scope.
        # A rule card under rules/<owner>/ may declare agent_scope listing OTHER
        # agents (e.g. PROMPT-AXIS-LOCK lives in rules/prompt_compiler/ but
        # also scopes shot_director and quality_inspector). Without this pass
        # those rules only land in the owner's critical knowledge, leaving
        # other in-scope agents to rely on RAG retrieval, which is unreliable.
        rules_root = os.path.join(knowledge_dir, "rules")
        if os.path.isdir(rules_root):
            for sub in sorted(os.listdir(rules_root)):
                # Already handled above by the per-agent + shared passes.
                if sub in (agent_name, "shared"):
                    continue
                sub_dir = os.path.join(rules_root, sub)
                if not os.path.isdir(sub_dir):
                    continue
                for fname in sorted(os.listdir(sub_dir)):
                    if not fname.endswith(".md"):
                        continue
                    relpath = f"rules/{sub}/{fname}"
                    if relpath in files:
                        continue
                    filepath = os.path.join(sub_dir, fname)
                    try:
                        with open(filepath, "r", encoding="utf-8") as f:
                            content = f.read()
                    except OSError:
                        continue
                    if not _runtime_retrieval_enabled(content):
                        continue
                    metadata = _frontmatter_metadata(content)
                    if not metadata:
                        continue
                    scope = set(_normalise_agent_scope(metadata.get("agent_scope")))
                    if agent_name in scope:
                        files.append(relpath)
        return files

    knowledge_dir = get_knowledge_dir()
    runtime_files: list[str] = []
    for relpath in files:
        filepath = os.path.join(knowledge_dir, relpath)
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read()
        except OSError:
            continue
        if _runtime_retrieval_enabled(content):
            runtime_files.append(relpath)
    files = runtime_files

    for relpath, filepath in _iter_knowledge_files():
        if relpath in files:
            continue
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read()
        except OSError:
            continue
        metadata = _frontmatter_metadata(content)
        if not metadata or not _runtime_retrieval_enabled(content):
            continue
        scope = set(_normalise_agent_scope(metadata.get("agent_scope")))
        if agent_name in scope or "shared" in scope:
            files.append(relpath)
    return files


def load_knowledge_documents(agent_name: str, filenames: list[str] | None = None) -> list[dict[str, str]]:
    knowledge_dir = get_knowledge_dir()
    docs: list[dict[str, str]] = []
    for filename in filenames or get_agent_knowledge_files(agent_name):
        filepath = os.path.join(knowledge_dir, filename)
        if not os.path.exists(filepath):
            continue
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()
        if not _runtime_retrieval_enabled(content):
            continue
        content = _strip_frontmatter(content)
        docs.append({"filename": filename, "content": content})
    return docs


# ---------- 向量库（纯 Python 实现） ----------

# 向量库文件路径
def _vectordb_path() -> str:
    config = load_config() or {}
    vdb_config = config.get("vectordb") or {}
    # 设置默认 persist_directory，防止配置缺失时 KeyError
    persist_dir = vdb_config.get("persist_directory") or "./vectordb/chroma_data"
    return os.path.join(
        get_cache_dir(),
        persist_dir,
        "vectordb.json"
    )


# 全局缓存
_vectordb_cache: dict | None = None


def _load_vectordb() -> dict:
    """加载向量库到内存（带缓存），容错解析损坏的 JSON 文件。"""
    global _vectordb_cache
    if _vectordb_cache is not None:
        return _vectordb_cache

    db_path = _vectordb_path()
    if not os.path.exists(db_path):
        raise FileNotFoundError(
            f"向量库文件不存在: {db_path}\n请先执行 python main.py build-db 构建向量库"
        )

    try:
        with open(db_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError as exc:
        raise RuntimeError(
            f"向量库 JSON 损坏 ({db_path}): {exc}\n请执行 python main.py build-db --rebuild 强制重建。"
        ) from exc
    except OSError as exc:
        raise RuntimeError(f"向量库文件读取失败 ({db_path}): {exc}") from exc

    if not isinstance(data, dict) or "embeddings" not in data:
        raise RuntimeError(
            f"向量库结构异常（缺少 embeddings 字段），路径 {db_path}。请执行 python main.py build-db --rebuild 重建。"
        )

    # 将 embedding 转为 numpy 数组以加速检索
    data["embeddings"] = np.array(data["embeddings"], dtype=np.float32)
    _vectordb_cache = data
    return data


def build_vectordb(knowledge_dir: str = None, force_rebuild: bool = False):
    """
    构建向量知识库。
    每个知识文件的切片都会标注来源文件和所属 Agent，
    便于 RAG 检索时按 Agent 过滤。
    """
    global _vectordb_cache
    config = load_config()
    vdb_config = config["vectordb"]

    if knowledge_dir is None:
        knowledge_dir = get_knowledge_dir()

    db_path = _vectordb_path()
    persist_dir = os.path.dirname(db_path)

    if os.path.exists(db_path) and not force_rebuild:
        print("向量库已存在，跳过构建。使用 --rebuild 强制重建。")
        return

    print("[INFO] 开始构建向量知识库...")
    print(f"  knowledge dir: {knowledge_dir}")
    print(f"  persist dir:   {persist_dir}")
    print(f"  embedding:     {vdb_config['embedding_model']} via {vdb_config.get('base_url', '')}")

    # 构建文件 → Agent 反向映射；Obsidian 规则卡优先使用 frontmatter.agent_scope。
    file_to_agents = {}
    for agent, files in AGENT_KNOWLEDGE_MAP.items():
        for f in files:
            if f not in file_to_agents:
                file_to_agents[f] = []
            file_to_agents[f].append(agent)

    # 遍历知识文件，切片
    all_documents = []
    all_metadatas = []
    total_chunks = 0

    for filename, filepath in _iter_knowledge_files(knowledge_dir):
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()
        if not _runtime_retrieval_enabled(content):
            print(f"  [SKIP] {filename}: runtime_retrieval=false")
            continue
        metadata = _frontmatter_metadata(content)

        chunks = chunk_markdown(
            content,
            chunk_size=vdb_config["chunk_size"],
            chunk_overlap=vdb_config["chunk_overlap"]
        )

        agents = _normalise_agent_scope(metadata.get("agent_scope")) or file_to_agents.get(filename, ["all"])

        for i, chunk in enumerate(chunks):
            all_documents.append(chunk["text"])
            all_metadatas.append({
                "source_file": filename,
                "chunk_index": i,
                "title": chunk["title"],
                "agents": ",".join(agents),
                "rule_id": str(metadata.get("rule_id", "")),
                "priority": str(metadata.get("priority", "")),
                "status": str(metadata.get("status", "")),
                "rule_type": str(metadata.get("rule_type", "")),
            })

        total_chunks += len(chunks)
        print(f"  [OK] {filename}: {len(chunks)} chunks -> Agent: {', '.join(agents)}")

    # 调用在线 API 获取所有片段的 Embedding
    print(f"\n[INFO] 正在获取 {len(all_documents)} 个片段的 Embedding...")
    all_embeddings = _embed_texts(all_documents, model=vdb_config["embedding_model"])
    print(f"  [OK] Embedding 维度: {len(all_embeddings[0])}")

    # 持久化到 JSON 文件
    os.makedirs(persist_dir, exist_ok=True)
    db_data = {
        "documents": all_documents,
        "metadatas": all_metadatas,
        "embeddings": [list(e) for e in all_embeddings],
    }
    with open(db_path, "w", encoding="utf-8") as f:
        json.dump(db_data, f, ensure_ascii=False)

    _vectordb_cache = None  # 清缓存
    print(f"\n[DONE] 向量库构建完成！共 {total_chunks} 个片段，已保存到 {db_path}")


def query_knowledge(
    query: str,
    agent_name: str = None,
    n_results: int = 5,
    preferred_sources: list[str] | set[str] | tuple[str, ...] | None = None,
) -> list[dict]:
    """
    RAG 检索：根据查询检索相关知识片段。
    使用 cosine similarity 排序。
    """
    db = _load_vectordb()

    # 获取查询向量
    query_emb = np.array(_embed_texts([query])[0], dtype=np.float32)

    # 计算 cosine similarity
    embeddings = db["embeddings"]
    # 归一化
    query_norm = query_emb / (np.linalg.norm(query_emb) + 1e-10)
    emb_norms = embeddings / (np.linalg.norm(embeddings, axis=1, keepdims=True) + 1e-10)
    similarities = emb_norms @ query_norm

    # 按 Agent 过滤，避免其他 Agent 专属规则漂入当前检索。
    candidate_indices = np.arange(len(similarities))
    if agent_name:
        allowed_sources = _normalize_source_basenames(get_agent_knowledge_files(agent_name))
        filtered = []
        for idx, meta in enumerate(db["metadatas"]):
            source_name = os.path.basename(str(meta.get("source_file", "")))
            if source_name not in allowed_sources:
                continue
            agents = [a.strip() for a in str(meta.get("agents", "")).split(",") if a.strip()]
            if "all" in agents or agent_name in agents:
                filtered.append(idx)
        candidate_indices = np.array(filtered, dtype=np.int64)

    if len(candidate_indices) == 0:
        return []

    preferred_source_names = _normalize_source_basenames(preferred_sources)
    candidate_scores = similarities[candidate_indices].copy()
    if preferred_source_names:
        for pos, idx in enumerate(candidate_indices):
            meta = db["metadatas"][idx]
            candidate_scores[pos] += _source_preference_boost(
                meta.get("source_file", ""),
                preferred_source_names,
                SOURCE_PREFERENCE_VECTOR_BOOST,
            )

    # 取 top-N
    top_indices = candidate_indices[np.argsort(candidate_scores)[::-1][:n_results]]

    knowledge_pieces = []
    for idx in top_indices:
        meta = db["metadatas"][idx]
        source_boost = _source_preference_boost(
            meta.get("source_file", ""),
            preferred_source_names,
            SOURCE_PREFERENCE_VECTOR_BOOST,
        )
        knowledge_pieces.append({
            "text": db["documents"][idx],
            "source": meta.get("source_file", ""),
            "title": meta.get("title", ""),
            "relevance": float(similarities[idx] + source_boost),
            "base_relevance": float(similarities[idx]),
            "source_boost": source_boost,
        })

    return knowledge_pieces


def get_full_knowledge_for_agent(agent_name: str, critical_only: bool = False) -> str:
    """
    获取某个 Agent 的全部知识文件内容（用于 System Prompt fallback）。
    当 RAG 不可用时，直接注入完整知识文件。
    """
    knowledge_dir = get_knowledge_dir()
    files = get_agent_knowledge_files(agent_name, critical_only=critical_only)

    contents = []
    for filename in files:
        filepath = os.path.join(knowledge_dir, filename)
        if os.path.exists(filepath):
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read()
            if not _runtime_retrieval_enabled(content):
                continue
            contents.append(f"--- {filename} ---\n{content}")

    return "\n\n".join(contents)


# ---------- BM25 关键词检索 ----------

def _tokenize_chinese(text: str) -> list[str]:
    """
    简易中文分词：按标点/空格切分 + 2-gram / 3-gram 覆盖。
    """
    # 去除 markdown 标记
    text = re.sub(r'[#*`\-\|>]', ' ', text)
    # 按非中文/非字母数字切分为词块
    blocks = re.findall(r'[\u4e00-\u9fff]+|[A-Za-z0-9]+', text)
    tokens: list[str] = []
    for block in blocks:
        if re.match(r'[A-Za-z0-9]+', block):
            tokens.append(block.lower())
        else:
            # 中文块：生成 2-gram 和 3-gram
            tokens.append(block)  # 整块也保留
            for n in (2, 3):
                for i in range(len(block) - n + 1):
                    tokens.append(block[i:i + n])
    return tokens


def _rule_search_text(rule: dict) -> str:
    fields = [
        "id",
        "title",
        "owner_agent",
        "priority",
        "applies_when",
        "instruction",
        "avoid_when",
    ]
    parts = [str(rule.get(field, "")) for field in fields]
    parts.extend(str(item) for item in rule.get("source_rules", []) or [])
    parts.extend(str(item) for item in rule.get("conflicts_with", []) or [])
    return "\n".join(part for part in parts if part)


def _rule_source_basenames(rule: dict) -> set[str]:
    return {os.path.basename(str(source)) for source in rule.get("source_files", []) or []}


def _normalize_source_basenames(sources: list[str] | set[str] | tuple[str, ...] | None) -> set[str]:
    if not sources:
        return set()
    return {os.path.basename(str(source)) for source in sources if str(source).strip()}


def _source_preference_boost(source: str, preferred_sources: set[str], amount: float) -> float:
    if not preferred_sources:
        return 0.0
    return amount if os.path.basename(str(source)) in preferred_sources else 0.0


def _source_runtime_retrieval_enabled(source: str) -> bool:
    source_path = os.path.join(get_knowledge_dir(), os.path.basename(str(source)))
    if not os.path.exists(source_path):
        return False

    with open(source_path, "r", encoding="utf-8") as f:
        content = f.read()
    return _runtime_retrieval_enabled(content)


def preferred_sources_from_registry_results(registry_results: list[dict]) -> set[str]:
    sources: set[str] = set()
    for result in registry_results:
        for source in result.get("source_files", []) or []:
            if _source_runtime_retrieval_enabled(source):
                sources.add(os.path.basename(str(source)))
    return sources


def _rule_visible_to_agent(rule: dict, agent_name: str | None) -> bool:
    if not agent_name:
        return True

    if rule.get("owner_agent") == agent_name:
        return True

    if rule.get("priority") in GLOBAL_RULE_PRIORITIES:
        return True

    if agent_name == "quality_inspector":
        return True

    agent_files = set(get_agent_knowledge_files(agent_name))
    return bool(agent_files & _rule_source_basenames(rule))


def _score_registry_rule(rule: dict, query_tokens: set[str], agent_name: str | None) -> float:
    rule_tokens = set(_tokenize_chinese(_rule_search_text(rule)))
    overlap = query_tokens & rule_tokens
    if not overlap:
        return 0.0

    score = len(overlap) / max(len(query_tokens), 1)
    priority = str(rule.get("priority", ""))
    priority_boosts = {
        "P0": 0.55,
        "P1": 0.45,
        "P2": 0.25,
        "P3": 0.2,
        "P4": 0.15,
        "P5": 0.1,
    }
    score += priority_boosts.get(priority, 0)

    if agent_name and rule.get("owner_agent") == agent_name:
        score += 0.75
    elif priority in GLOBAL_RULE_PRIORITIES:
        score += 0.25

    if agent_name:
        agent_files = set(get_agent_knowledge_files(agent_name))
        if agent_files & _rule_source_basenames(rule):
            score += 0.2

    return score


def _format_registry_rule(rule: dict) -> str:
    lines = [
        f"[{rule.get('id', '')}] {rule.get('title', '')}",
        f"owner_agent: {rule.get('owner_agent', '')} | priority: {rule.get('priority', '')}",
        f"适用场景: {rule.get('applies_when', '')}",
        f"执行指令: {rule.get('instruction', '')}",
    ]
    if rule.get("avoid_when"):
        lines.append(f"例外边界: {rule.get('avoid_when')}")
    if rule.get("source_files"):
        lines.append("来源文件: " + ", ".join(str(item) for item in rule.get("source_files", [])))
    return "\n".join(lines)


def query_rule_registry(
    query: str,
    agent_name: str | None = None,
    n_results: int = 4,
) -> list[dict]:
    """Return the most relevant canonical rule cards before broad RAG retrieval."""
    query_tokens = set(_tokenize_chinese(query))
    if not query_tokens:
        return []

    registry = load_rule_registry()
    rules = registry.get("rules", [])
    if not isinstance(rules, list):
        return []

    scored_rules = []
    for rule in rules:
        if not isinstance(rule, dict):
            continue
        if not _rule_visible_to_agent(rule, agent_name):
            continue

        score = _score_registry_rule(rule, query_tokens, agent_name)
        if score <= 0:
            continue

        scored_rules.append((score, rule))

    scored_rules.sort(key=lambda item: item[0], reverse=True)

    results = []
    for score, rule in scored_rules[:n_results]:
        results.append({
            "text": _format_registry_rule(rule),
            "source": RULE_REGISTRY_FILENAME,
            "title": rule.get("title", ""),
            "relevance": score,
            "rule_id": rule.get("id", ""),
            "owner_agent": rule.get("owner_agent", ""),
            "priority": rule.get("priority", ""),
            "source_files": rule.get("source_files", []),
        })
    return results


def get_rule_registry_context(
    query: str,
    agent_name: str | None = None,
    n_results: int = 4,
) -> tuple[str, list[dict]]:
    results = query_rule_registry(query, agent_name=agent_name, n_results=n_results)
    if not results:
        return "", []

    parts = ["--- rule_registry.yaml (规则注册表命中) ---"]
    parts.extend(item["text"] for item in results)
    return "\n\n".join(parts), results


# BM25 索引缓存：agent_name -> (retriever, chunks_meta)
_bm25_index_cache: dict[str, tuple] = {}


def build_bm25_index(agent_name: str):
    """
    为指定 agent 的知识文件构建 BM25 索引（带缓存）。
    返回三元组 (retriever, chunks, vocab)：
        - retriever: bm25s.BM25 对象；若无可检索内容则为 None
        - chunks: list[dict]，每项含 text/source/title
        - vocab: dict[token -> int]，供查询侧做 id 映射
    """
    if agent_name in _bm25_index_cache:
        return _bm25_index_cache[agent_name]

    knowledge_dir = get_knowledge_dir()
    config = load_config()
    vdb_config = config.get("vectordb", {})
    chunk_size = vdb_config.get("chunk_size", 800)
    chunk_overlap = vdb_config.get("chunk_overlap", 100)

    files = get_agent_knowledge_files(agent_name)
    all_chunks: list[dict] = []

    for filename in files:
        filepath = os.path.join(knowledge_dir, filename)
        if not os.path.exists(filepath):
            continue
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()
        if not _runtime_retrieval_enabled(content):
            continue
        chunks = chunk_markdown(content, chunk_size=chunk_size, chunk_overlap=chunk_overlap)
        for chunk in chunks:
            all_chunks.append({
                "text": chunk["text"],
                "title": chunk.get("title", ""),
                "source": filename,
            })

    if not all_chunks:
        # 统一为三元组，保证调用方解包格式稳定
        _bm25_index_cache[agent_name] = (None, [], {})
        return None, [], {}

    # 使用自定义中文分词对每个 chunk 分词
    corpus_tokens = [_tokenize_chinese(c["text"]) for c in all_chunks]

    # 构建 vocab 并转为 bm25s 期望的 Tokenized 格式
    vocab = {}
    corpus_ids = []
    for tokens in corpus_tokens:
        ids = []
        for t in tokens:
            if t not in vocab:
                vocab[t] = len(vocab)
            ids.append(vocab[t])
        corpus_ids.append(np.array(ids, dtype=np.int32))

    tokenized = bm25s.tokenize(["dummy"], stemmer=None)  # 获取 Tokenized 类型
    tokenized_corpus = type(tokenized)(ids=corpus_ids, vocab=vocab)

    # 构建 BM25 索引
    retriever = bm25s.BM25()
    retriever.index(tokenized_corpus)

    _bm25_index_cache[agent_name] = (retriever, all_chunks, vocab)
    return retriever, all_chunks, vocab


def query_knowledge_bm25(
    query: str,
    agent_name: str,
    n_results: int = 10,
    preferred_sources: list[str] | set[str] | tuple[str, ...] | None = None,
) -> list[dict]:
    """
    BM25 关键词检索：返回与 query 最相关的知识片段。
    """
    if not _HAS_BM25S:
        return []

    result = build_bm25_index(agent_name)
    if result[0] is None:
        return []
    retriever, chunks, vocab = result

    # 使用自定义中文分词
    query_tokens = _tokenize_chinese(query)
    query_ids = np.array([vocab.get(t, -1) for t in query_tokens], dtype=np.int32)
    query_ids = query_ids[query_ids >= 0]  # 过滤未知词

    if len(query_ids) == 0:
        return []

    # 构造 Tokenized 对象
    tokenized = bm25s.tokenize(["dummy"], stemmer=None)
    tokenized_query = type(tokenized)(ids=[query_ids], vocab=vocab)

    preferred_source_names = _normalize_source_basenames(preferred_sources)
    n = min(max(n_results, n_results * 3), len(chunks))
    results, scores = retriever.retrieve(tokenized_query, k=n)

    pieces = []
    for i in range(n):
        idx = int(results[0, i])
        score = float(scores[0, i])
        if score <= 0:
            continue
        chunk = chunks[idx]
        source_boost = _source_preference_boost(
            chunk["source"],
            preferred_source_names,
            SOURCE_PREFERENCE_BM25_BOOST,
        )
        pieces.append({
            "text": chunk["text"],
            "source": chunk["source"],
            "title": chunk["title"],
            "relevance": score + source_boost,
            "base_relevance": score,
            "source_boost": source_boost,
        })
    pieces.sort(key=lambda item: item["relevance"], reverse=True)
    return pieces[:n_results]


def query_knowledge_hybrid(
    query: str,
    agent_name: str = None,
    n_results: int = 8,
    bm25_k: int = 10,
    vector_k: int = 10,
    preferred_sources: list[str] | set[str] | tuple[str, ...] | None = None,
) -> list[dict]:
    """
    混合检索：BM25 关键词 + 向量语义 → RRF 融合排序。
    Reciprocal Rank Fusion (RRF): score = Σ 1/(k + rank)，k=60。
    """
    rrf_k = 60  # RRF 常数
    preferred_source_names = _normalize_source_basenames(preferred_sources)

    # ---- BM25 路 ----
    bm25_results = []
    if _HAS_BM25S:
        try:
            bm25_results = query_knowledge_bm25(
                query,
                agent_name,
                n_results=bm25_k,
                preferred_sources=preferred_source_names,
            )
        except Exception:
            pass

    # ---- 向量路 ----
    vector_results = []
    try:
        vector_results = query_knowledge(
            query,
            agent_name,
            n_results=vector_k,
            preferred_sources=preferred_source_names,
        )
    except Exception:
        pass

    # ---- RRF 融合 ----
    # 用 text 内容作为去重 key
    text_to_score: dict[str, float] = {}
    text_to_meta: dict[str, dict] = {}

    for rank, item in enumerate(bm25_results):
        key = item["text"].strip()
        rrf_score = 1.0 / (rrf_k + rank + 1)
        rrf_score += _source_preference_boost(
            item.get("source", ""),
            preferred_source_names,
            SOURCE_PREFERENCE_RRF_BOOST,
        )
        text_to_score[key] = text_to_score.get(key, 0) + rrf_score
        if key not in text_to_meta:
            text_to_meta[key] = item

    for rank, item in enumerate(vector_results):
        key = item["text"].strip()
        rrf_score = 1.0 / (rrf_k + rank + 1)
        rrf_score += _source_preference_boost(
            item.get("source", ""),
            preferred_source_names,
            SOURCE_PREFERENCE_RRF_BOOST,
        )
        text_to_score[key] = text_to_score.get(key, 0) + rrf_score
        if key not in text_to_meta:
            text_to_meta[key] = item

    # 按 RRF 分数排序
    sorted_keys = sorted(text_to_score.keys(), key=lambda k: text_to_score[k], reverse=True)

    results = []
    for key in sorted_keys[:n_results]:
        meta = text_to_meta[key]
        results.append({
            "text": meta["text"],
            "source": meta.get("source", ""),
            "title": meta.get("title", ""),
            "relevance": text_to_score[key],
            "source_boost": _source_preference_boost(
                meta.get("source", ""),
                preferred_source_names,
                SOURCE_PREFERENCE_RRF_BOOST,
            ),
        })
    return results


def get_smart_knowledge(agent_name: str, context_hint: str = "") -> str:
    """
    智能知识获取主接口。
    根据 config 中 retrieval_mode 决定检索策略：
      - full:   全文注入（现有行为）
      - bm25:   BM25 关键词检索
      - hybrid: BM25 + 向量混合检索（推荐）

    当检索结果不足 min_chunks_fallback 个时，自动 fallback 到全文注入。
    """
    config = load_config()
    kb_config = config.get("knowledge", {})
    mode = kb_config.get("retrieval_mode", "full")
    final_top_k = kb_config.get("final_top_k", 8)
    min_fallback = kb_config.get("min_chunks_fallback", 3)
    registry_top_k = kb_config.get("registry_top_k", 4)

    # 全文模式直接返回
    if mode == "full" or not context_hint.strip():
        return get_full_knowledge_for_agent(agent_name), {
            "retrieval_mode": mode,
            "used_full_fallback": True,
            "matched_sources": get_agent_knowledge_files(agent_name),
            "critical_sources": get_agent_knowledge_files(agent_name, critical_only=True),
            "result_count": 0,
            "registry_result_count": 0,
            "registry_rule_ids": [],
            "registry_preferred_sources": [],
            "context_hint": context_hint,
        }

    registry_text, registry_results = get_rule_registry_context(
        query=context_hint,
        agent_name=agent_name,
        n_results=registry_top_k,
    )
    registry_rule_ids = [item.get("rule_id", "") for item in registry_results if item.get("rule_id")]
    registry_preferred_sources = sorted(preferred_sources_from_registry_results(registry_results))

    # 检索
    results = []
    try:
        if mode == "hybrid":
            bm25_k = kb_config.get("bm25_top_k", 10)
            vector_k = kb_config.get("vector_top_k", 10)
            results = query_knowledge_hybrid(
                query=context_hint,
                agent_name=agent_name,
                n_results=final_top_k,
                bm25_k=bm25_k,
                vector_k=vector_k,
                preferred_sources=registry_preferred_sources,
            )
        elif mode == "bm25":
            results = query_knowledge_bm25(
                query=context_hint,
                agent_name=agent_name,
                n_results=final_top_k,
                preferred_sources=registry_preferred_sources,
            )
        else:
            full_text = get_full_knowledge_for_agent(agent_name)
            return full_text, {
                "retrieval_mode": mode,
                "used_full_fallback": True,
                "matched_sources": get_agent_knowledge_files(agent_name),
                "critical_sources": get_agent_knowledge_files(agent_name, critical_only=True),
                "result_count": 0,
                "registry_result_count": len(registry_results),
                "registry_rule_ids": registry_rule_ids,
                "registry_preferred_sources": registry_preferred_sources,
                "context_hint": context_hint,
            }
    except Exception as e:
        print(f"[WARN] 知识检索失败 ({mode}): {e}，回退全文注入。")
        full_text = get_full_knowledge_for_agent(agent_name)
        return full_text, {
            "retrieval_mode": mode,
            "used_full_fallback": True,
            "matched_sources": get_agent_knowledge_files(agent_name),
            "critical_sources": get_agent_knowledge_files(agent_name, critical_only=True),
            "result_count": 0,
            "registry_result_count": len(registry_results),
            "registry_rule_ids": registry_rule_ids,
            "registry_preferred_sources": registry_preferred_sources,
            "context_hint": context_hint,
            "error": str(e),
        }

    # 结果不足，fallback 全文
    if len(results) < min_fallback:
        print(f"[INFO] 检索结果仅 {len(results)} 条 < {min_fallback}，回退全文注入。")
        full_text = get_full_knowledge_for_agent(agent_name)
        return full_text, {
            "retrieval_mode": mode,
            "used_full_fallback": True,
            "matched_sources": sorted({item.get("source", "") for item in results if item.get("source")}),
            "critical_sources": get_agent_knowledge_files(agent_name, critical_only=True),
            "result_count": len(results),
            "registry_result_count": len(registry_results),
            "registry_rule_ids": registry_rule_ids,
            "registry_preferred_sources": registry_preferred_sources,
            "context_hint": context_hint,
        }

    # 拼接检索到的知识片段
    parts = []
    seen_sources = set()
    if registry_text:
        parts.append(registry_text)
        seen_sources.add(RULE_REGISTRY_FILENAME)
    for item in results:
        source = item.get("source", "")
        if source and source not in seen_sources:
            parts.append(f"--- {source} (精选片段) ---")
            seen_sources.add(source)
        parts.append(item["text"])
    return "\n\n".join(parts), {
        "retrieval_mode": mode,
        "used_full_fallback": False,
        "matched_sources": sorted(seen_sources),
        "critical_sources": get_agent_knowledge_files(agent_name, critical_only=True),
        "result_count": len(results),
        "registry_result_count": len(registry_results),
        "registry_rule_ids": registry_rule_ids,
        "registry_preferred_sources": registry_preferred_sources,
        "context_hint": context_hint,
    }


if __name__ == "__main__":
    import sys
    force = "--rebuild" in sys.argv
    build_vectordb(force_rebuild=force)
