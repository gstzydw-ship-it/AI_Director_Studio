"""
向量知识库构建与检索模块
使用 numpy + OpenAI 兼容 Embedding API 实现纯 Python 向量检索
支持 BM25 关键词检索 + 向量语义检索的混合模式
（不依赖 ChromaDB / PyTorch / sentence-transformers）
"""

import os
import re
import json
import stat
import time
import warnings
from datetime import datetime
import numpy as np
import yaml
from openai import OpenAI
try:
    import bm25s
    _HAS_BM25S = True
except ImportError:
    bm25s = None
    _HAS_BM25S = False
from typing import Dict, List, Any, Callable

from .request_context import request_session_id
from .utils import COMFLY_BASE_URL, get_config_path, get_knowledge_dir, get_cache_dir, get_output_dir, load_yaml_config


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

_embed_clients: dict[tuple[str, str, float, int], OpenAI] = {}


def _coerce_positive_float(value: Any, default: float) -> float:
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return default
    return parsed if parsed > 0 else default


def _coerce_non_negative_int(value: Any, default: int) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return default
    return parsed if parsed >= 0 else default


def _load_session_model_profile() -> dict[str, Any]:
    session_id = re.sub(r"[^A-Za-z0-9_-]", "", request_session_id.get("local") or "local")[:80] or "local"
    state_path = os.path.join(get_output_dir(), "sessions", session_id, "pipeline_state.json")
    if not os.path.exists(state_path):
        return {}
    try:
        with open(state_path, "r", encoding="utf-8-sig") as file:
            state = json.load(file)
    except Exception:
        return {}
    profile = state.get("model_profile_snapshot") if isinstance(state, dict) else {}
    return profile if isinstance(profile, dict) else {}


def _get_embed_client() -> OpenAI:
    """Return cached OpenAI-compatible embedding client.

    Runtime embedding settings come from the model profile snapshot first,
    then config/settings.yaml; the frontend-saved config is the single source
    of truth.
    """
    config = load_config() or {}
    vdb_config = config.get("vectordb") or {}
    profile = _load_session_model_profile()
    api_key = profile.get("vectordb_api_key") or profile.get("api_key") or vdb_config.get("api_key") or ""
    base_url = profile.get("vectordb_base_url") or vdb_config.get("base_url") or COMFLY_BASE_URL
    timeout_seconds = _coerce_positive_float(
        profile.get("vectordb_timeout_seconds") or vdb_config.get("timeout_seconds"),
        120.0,
    )
    max_retries = _coerce_non_negative_int(vdb_config.get("max_retries"), 2)
    if not api_key:
        raise RuntimeError("vectordb.api_key 未配置，无法创建 Embedding 客户端。")
    cache_key = (api_key, base_url, timeout_seconds, max_retries)
    if cache_key not in _embed_clients:
        _embed_clients[cache_key] = OpenAI(
            api_key=api_key,
            base_url=base_url,
            timeout=timeout_seconds,
            max_retries=max_retries,
        )
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
        profile = _load_session_model_profile()
        model = profile.get("embedding_model") or config["vectordb"]["embedding_model"]
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
        return [item.strip() for item in re.split(r"[,，;；\n]+", value) if item.strip()]
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    return []


PROFILE_FIELDS = (
    "retrieval_key",
    "applies_when",
    "avoid_when",
    "signals",
    "scene_types",
    "events",
    "risks",
    "dialogue_types",
    "aspect_ratios",
    "tags",
    "served_agents",
    "visual_constraints",
    "reusable_pattern",
)

STANDARD_RULE_METADATA_FIELDS = (
    "owner_agent",
    "pipeline_stage",
    "applies_when",
    "avoid_when",
    "failure_mode",
    "output_contract",
    "example_good",
    "example_bad",
)


def _normalise_frontmatter_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        items: list[str] = []
        for item in value:
            items.extend(_normalise_frontmatter_list(item))
        return items
    if isinstance(value, dict):
        return [f"{key}:{val}" for key, val in value.items()]
    return [item.strip() for item in re.split(r"[,，\n]", str(value)) if item.strip()]


def _canonical_priority(value: Any) -> str:
    priority = str(value or "").strip()
    aliases = {
        "hard": "P0",
        "critical": "P0",
        "must": "P0",
        "high": "P1",
        "medium": "P3",
        "normal": "P3",
        "low": "P5",
    }
    return aliases.get(priority.lower(), priority)


def _profile_value_text(value: Any) -> str:
    return " ".join(_normalise_frontmatter_list(value))


def build_retrieval_profile_query(context_hint: str = "", retrieval_profile: dict[str, Any] | None = None) -> str:
    """Append structured task tags to the free-text retrieval hint."""
    if not retrieval_profile:
        return context_hint or ""

    parts = [context_hint or ""]
    for field in PROFILE_FIELDS:
        text = _profile_value_text(retrieval_profile.get(field))
        if text:
            parts.append(f"{field}: {text}")

    singular_aliases = {
        "scene_type": "scene_types",
        "event": "events",
        "risk": "risks",
        "dialogue_type": "dialogue_types",
        "aspect_ratio": "aspect_ratios",
    }
    for singular, plural in singular_aliases.items():
        text = _profile_value_text(retrieval_profile.get(singular))
        if text:
            parts.append(f"{plural}: {text}")

    return "\n".join(part for part in parts if part.strip())


def _metadata_signal_text(metadata: dict[str, Any]) -> str:
    fields = (
        "rule_id",
        "id",
        "title",
        "doc_type",
        "rule_type",
        "priority",
        "status",
        "owner_agent",
        "pipeline_stage",
        "applies_to",
        "applies_when",
        "avoid_when",
        "failure_mode",
        "output_contract",
        "retrieval_key",
        "signals",
        "scene_types",
        "events",
        "risks",
        "dialogue_types",
        "aspect_ratios",
        "aspect_ratio",
        "tags",
        "served_agents",
        "case_title",
        "visual_constraints",
        "reusable_pattern",
    )
    parts: list[str] = []
    for field in fields:
        value = metadata.get(field)
        if isinstance(value, (list, tuple, set)):
            parts.extend(str(item) for item in value)
        elif value:
            parts.append(str(value))
    parts.extend(_normalise_agent_scope(metadata.get("agent_scope")))
    return "\n".join(parts)


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
AGENT_RETRIEVAL_CONTRACTS_FILENAME = "agent_retrieval_contracts.yaml"
GLOBAL_RULE_PRIORITIES = {"P0", "P1"}
SOURCE_PREFERENCE_BM25_BOOST = 0.2
SOURCE_PREFERENCE_VECTOR_BOOST = 0.06
SOURCE_PREFERENCE_RRF_BOOST = 0.01
PROFILED_METADATA_BOOST = 0.35
PROFILED_AVOID_PENALTY = 0.7
_rule_registry_cache: dict | None = None
_retrieval_contracts_cache: dict | None = None
_source_runtime_retrieval_cache: dict[str, bool] = {}


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

def load_agent_retrieval_contracts() -> dict:
    """Load bootstrap retrieval contracts without adding them to RAG content."""
    global _retrieval_contracts_cache
    if _retrieval_contracts_cache is not None:
        return _retrieval_contracts_cache

    contracts_path = os.path.join(get_knowledge_dir(), AGENT_RETRIEVAL_CONTRACTS_FILENAME)
    if not os.path.exists(contracts_path):
        _retrieval_contracts_cache = {}
        return _retrieval_contracts_cache

    try:
        with open(contracts_path, "r", encoding="utf-8") as f:
            contracts = yaml.safe_load(f) or {}
    except (yaml.YAMLError, OSError) as exc:
        print(f"  [Registry] WARN: 检索契约加载失败 ({contracts_path}): {exc}")
        contracts = {}

    _retrieval_contracts_cache = contracts if isinstance(contracts, dict) else {}
    return _retrieval_contracts_cache


def _contract_field_values(section: dict[str, Any], field: str) -> list[str]:
    value = section.get(field)
    if isinstance(value, dict):
        values: list[str] = []
        for key in ("primary", "secondary", "prefer", "match", "boost"):
            values.extend(_normalise_frontmatter_list(value.get(key)))
        return values
    return _normalise_frontmatter_list(value)


def build_agent_bootstrap_retrieval_profile(agent_name: str) -> dict[str, Any]:
    contracts = load_agent_retrieval_contracts()
    agents = contracts.get("agents") if isinstance(contracts, dict) else {}
    agent_contract = agents.get(agent_name) if isinstance(agents, dict) else {}
    if not isinstance(agent_contract, dict):
        agent_contract = {}

    profile: dict[str, Any] = {}
    global_strategy = contracts.get("global_matching_strategy", {}) if isinstance(contracts, dict) else {}
    if isinstance(global_strategy, dict):
        exclude_status = _normalise_frontmatter_list(global_strategy.get("exclude_status"))
        if exclude_status:
            profile["exclude_status"] = exclude_status
        case_limits = global_strategy.get("case_card_limits")
        if isinstance(case_limits, dict):
            profile["case_card_limits"] = dict(case_limits)

    served_agents = _contract_field_values(agent_contract, "agent_scope")
    if served_agents:
        profile["served_agents"] = served_agents

    for field in ("scene_types", "events", "risks", "dialogue_types", "aspect_ratios", "signals"):
        values = _contract_field_values(agent_contract, field)
        if values:
            profile[field] = values

    tags: list[str] = []
    tags.extend(_contract_field_values(agent_contract, "rule_type"))
    priority_policy = agent_contract.get("priority_policy")
    if isinstance(priority_policy, dict):
        tags.extend(_normalise_frontmatter_list(priority_policy.get("prefer")))
    if tags:
        profile["tags"] = tags

    if profile:
        profile["retrieval_key"] = [agent_name, "agent_retrieval_contracts"]
    return profile


COMMON_KNOWLEDGE_FILES = [
    "00_知识库优先级与冲突裁决规则.md",
    # rule_registry.yaml 不再全量注入（29K chars / ~7400 tokens），
    # 改由 get_smart_knowledge() → query_rule_registry() 按需检索。
]

AGENT_WIKI_CONTEXT_MAP = {
    "director_showrunner": [
        "wiki/agents/director_showrunner.md",
        "wiki/playbooks/argument_scene.md",
        "wiki/playbooks/misunderstanding_reversal.md",
    ],
    "rhythm_rewrite_director": [
        "wiki/agents/rhythm_rewrite_director.md",
        "wiki/playbooks/argument_scene.md",
        "wiki/playbooks/misunderstanding_reversal.md",
    ],
    "scene_analyst": [
        "wiki/agents/scene_analyst.md",
        "wiki/contracts/continuity_contract.md",
        "wiki/failure_modes/scene_space_unclear.md",
    ],
    "story_planner": [
        "wiki/agents/story_planner.md",
        "wiki/contracts/story_to_shot_contract.md",
        "wiki/contracts/continuity_contract.md",
    ],
    "shot_director": [
        "wiki/agents/shot_director.md",
        "wiki/contracts/story_to_shot_contract.md",
        "wiki/contracts/shot_to_prompt_contract.md",
        "wiki/contracts/continuity_contract.md",
    ],
    "shot_director_layout": [
        "wiki/agents/shot_director_layout.md",
        "wiki/contracts/story_to_shot_contract.md",
        "wiki/failure_modes/scene_space_unclear.md",
    ],
    "shot_director_blocking": [
        "wiki/agents/shot_director_blocking.md",
        "wiki/contracts/shot_to_prompt_contract.md",
        "wiki/contracts/continuity_contract.md",
        "wiki/failure_modes/action_discontinuity.md",
    ],
    "shot_director_guard": [
        "wiki/agents/shot_director_guard.md",
        "wiki/contracts/continuity_contract.md",
        "wiki/failure_modes/action_discontinuity.md",
        "wiki/failure_modes/scene_space_unclear.md",
    ],
    "prompt_compiler": [
        "wiki/agents/prompt_compiler.md",
        "wiki/contracts/shot_to_prompt_contract.md",
        "wiki/contracts/prompt_to_quality_contract.md",
        "wiki/failure_modes/prompt_too_abstract.md",
    ],
    "quality_inspector": [
        "wiki/agents/quality_inspector.md",
        "wiki/contracts/prompt_to_quality_contract.md",
        "wiki/contracts/continuity_contract.md",
        "wiki/failure_modes/hard_fail_quality.md",
    ],
    "storyboard_designer": [
        "wiki/agents/storyboard_designer.md",
        "wiki/playbooks/nine_panel_storyboard.md",
        "wiki/failure_modes/storyboard_inconsistent.md",
        "wiki/contracts/continuity_contract.md",
    ],
}


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
        "rules/shot_director/SHOT-SIMPLE-SEEDANCE-CAMERA-001.md",
    ],
    "shot_director_layout": [
        "25_镜头摆位主分镜骨架规则.md",
        "02_焦段景深与景别画幅策略.md",
        "06_连续性与安全规则.md",
        "21_镜头调用规则与多机位模板.md",
        "22_多机位分镜与镜头多样性规则.md",
        "28_全场景分镜与转场案例库.md",
        "rules/shot_director/SHOT-SIMPLE-SEEDANCE-CAMERA-001.md",
    ],
    "shot_director_blocking": [
        "26_动作调度与受击覆盖规则.md",
        "04_对白与表演镜头规则.md",
        "06_连续性与安全规则.md",
        "14_动作描述精细化控制规则.md",
        "18_情绪锚点与逐段交互与仰拍限制补丁.md",
        "21_镜头调用规则与多机位模板.md",
        "28_全场景分镜与转场案例库.md",
        "rules/shot_director/SHOT-SIMPLE-SEEDANCE-CAMERA-001.md",
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
        "rules/prompt_compiler/PROMPT-TIME-INHERIT-UPSTREAM-001.md",
        "rules/prompt_compiler/PROMPT-SHOT-TRANSITION-VERB-001.md",
        "rules/prompt_compiler/PROMPT-NO-SAME-CAMERA-ABUSE-001.md",
        "rules/prompt_compiler/PROMPT-VISIBLE-BODY-LANGUAGE-001.md",
        "rules/prompt_compiler/PROMPT-SMALL-ACTION-STABILITY-001.md",
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
        "rules/prompt_compiler/PROMPT-TIME-INHERIT-UPSTREAM-001.md",
        "rules/prompt_compiler/PROMPT-SHOT-TRANSITION-VERB-001.md",
        "rules/prompt_compiler/PROMPT-NO-SAME-CAMERA-ABUSE-001.md",
        "rules/prompt_compiler/PROMPT-VISIBLE-BODY-LANGUAGE-001.md",
        "rules/prompt_compiler/PROMPT-SMALL-ACTION-STABILITY-001.md",
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
        "rules/shot_director/SHOT-SIMPLE-SEEDANCE-CAMERA-001.md",  # Seedance 稳定短句降级
    ],
    "shot_director_layout": [
        "25_镜头摆位主分镜骨架规则.md",   # 一号机位摆位导演的职责合同
        "04_对白与表演镜头规则.md",       # 对白覆盖与表演落点
        "02_焦段景深与景别画幅策略.md",   # 景别/焦段/画幅主规则
        "06_连续性与安全规则.md",          # 接缝与状态安全
        "21_镜头调用规则与多机位模板.md",  # 主镜头骨架模板
        "rules/shot_director/SHOT-SIMPLE-SEEDANCE-CAMERA-001.md",  # 单任务镜头基底
    ],
    "shot_director_blocking": [
        "26_动作调度与受击覆盖规则.md",   # 二号动作调度导演的职责合同
        "06_连续性与安全规则.md",          # 受击接续需要连续性保障
        "14_动作描述精细化控制规则.md",   # 动作描述精度
        "04_对白与表演镜头规则.md",       # 对白落点规则
        "rules/shot_director/SHOT-SIMPLE-SEEDANCE-CAMERA-001.md",  # 禁止复杂摆尾运镜
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
        "rules/prompt_compiler/PROMPT-TIME-INHERIT-UPSTREAM-001.md",  # 时间切片继承上游，不得重切
        "rules/prompt_compiler/PROMPT-SHOT-TRANSITION-VERB-001.md",  # 主体变化时准确选衔接词
        "rules/prompt_compiler/PROMPT-NO-SAME-CAMERA-ABUSE-001.md",  # 禁止滥用同一机位继续
        "rules/prompt_compiler/PROMPT-VISIBLE-BODY-LANGUAGE-001.md",  # 抽象情绪转身体语言
        "rules/prompt_compiler/PROMPT-SMALL-ACTION-STABILITY-001.md",  # 小动作优先与动作拆链
        "rules/shot_director/SHOT-SIMPLE-SEEDANCE-CAMERA-001.md",  # 复杂运镜降级
    ],
    "quality_inspector": [
        "17_结果质检与回溯修正规则.md",    # 质检核心文件
        "05_剧本拆分与15秒片段规划规则.md",  # 片段边界校验
        "06_连续性与安全规则.md",          # 连续性与禁忌校验
        "24_戏剧微粒识别与节奏触发规则.md",  # 戏剧微粒与 Hook 回查
        "rules/quality_inspector/QC-PACING-SAFETY-CHECKLIST-001.md",  # 节奏质检清单
        "rules/prompt_compiler/PROMPT-TIME-INHERIT-UPSTREAM-001.md",  # 校验时间继承
        "rules/prompt_compiler/PROMPT-SHOT-TRANSITION-VERB-001.md",  # 校验衔接词准确性
        "rules/prompt_compiler/PROMPT-NO-SAME-CAMERA-ABUSE-001.md",  # 校验同一机位滥用
        "rules/prompt_compiler/PROMPT-VISIBLE-BODY-LANGUAGE-001.md",  # 校验抽象情绪降级
        "rules/prompt_compiler/PROMPT-SMALL-ACTION-STABILITY-001.md",  # 校验动作拆链与单任务运镜
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


def _append_runtime_rule_card(
    files: list[str],
    relpath: str,
    filepath: str,
    include: Callable[[str], bool] | None = None,
) -> None:
    if relpath in files:
        return
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()
    except OSError:
        return
    if not _runtime_retrieval_enabled(content):
        return
    if include is not None and not include(content):
        return
    files.append(relpath)


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
                if not fname.endswith(".md"):
                    continue
                _append_runtime_rule_card(
                    files,
                    f"rules/{agent_name}/{fname}",
                    os.path.join(agent_rules_dir, fname),
                )
        # Also include shared rule cards from rules/shared/
        shared_rules_dir = os.path.join(knowledge_dir, "rules", "shared")
        if os.path.isdir(shared_rules_dir):
            for fname in sorted(os.listdir(shared_rules_dir)):
                if not fname.endswith(".md"):
                    continue
                _append_runtime_rule_card(
                    files,
                    f"rules/shared/{fname}",
                    os.path.join(shared_rules_dir, fname),
                )

        # Cross-folder critical injection by frontmatter agent_scope.
        # A rule card under rules/<owner>/ may declare agent_scope listing OTHER
        # agents (e.g. PROMPT-AXIS-LOCK lives in rules/prompt_compiler/ but
        # also scopes shot_director and quality_inspector). Without this pass
        # those rules only land in the owner's critical knowledge, leaving
        # other in-scope agents to rely on RAG retrieval, which is unreliable.
        def scoped_to_agent(content: str) -> bool:
            metadata = _frontmatter_metadata(content)
            if not metadata:
                return False
            scope = set(_normalise_agent_scope(metadata.get("agent_scope")))
            return agent_name in scope

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

                    _append_runtime_rule_card(
                        files,
                        relpath,
                        os.path.join(sub_dir, fname),
                        include=scoped_to_agent,
                    )
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
        served_agents = set(_normalise_agent_scope(metadata.get("served_agents")))
        if agent_name in scope or agent_name in served_agents or "shared" in scope or "shared" in served_agents:
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


def get_agent_wiki_files(agent_name: str) -> list[str]:
    files = list(AGENT_WIKI_CONTEXT_MAP.get(agent_name, []))
    default_handbook = f"wiki/agents/{agent_name}.md"
    if default_handbook not in files:
        files.insert(0, default_handbook)

    knowledge_dir = get_knowledge_dir()
    runtime_files: list[str] = []
    seen: set[str] = set()
    for relpath in files:
        if relpath in seen:
            continue
        seen.add(relpath)
        filepath = os.path.join(knowledge_dir, relpath)
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read()
        except OSError:
            continue
        if _runtime_retrieval_enabled(content):
            runtime_files.append(relpath)
    return runtime_files


def get_agent_wiki_context(agent_name: str) -> tuple[str, list[str]]:
    docs = load_knowledge_documents(agent_name, get_agent_wiki_files(agent_name))
    if not docs:
        return "", []
    parts = [f"--- {doc['filename']} (agent_wiki_context) ---\n{doc['content']}" for doc in docs]
    return "\n\n".join(parts), [doc["filename"] for doc in docs]


# ---------- 向量库（纯 Python 实现） ----------

# 向量库文件路径
def _vectordb_dir() -> str:
    config = load_config() or {}
    vdb_config = config.get("vectordb") or {}
    persist_dir = vdb_config.get("persist_directory") or "vectordb/chroma_data"
    if os.path.isabs(str(persist_dir)):
        return os.path.normpath(str(persist_dir))
    return os.path.normpath(os.path.join(get_cache_dir(), str(persist_dir)))


def _vectordb_path() -> str:
    return os.path.join(_vectordb_dir(), "vectordb.json")
    # 设置默认 persist_directory，防止配置缺失时 KeyError


# 全局缓存
def _legacy_vectordb_path(knowledge_dir: str | None = None) -> str:
    project_root = os.path.dirname(os.path.abspath(knowledge_dir or get_knowledge_dir()))
    return os.path.join(project_root, "vectordb", "chroma_data", "vectordb.json")


def _format_mtime(timestamp: float | None) -> str:
    if timestamp is None:
        return ""
    return datetime.fromtimestamp(timestamp).isoformat(timespec="seconds")


def _knowledge_file_summary(relpath: str, filepath: str) -> dict[str, Any]:
    summary: dict[str, Any] = {
        "title": os.path.splitext(os.path.basename(relpath))[0],
        "runtime_retrieval": True,
        "priority": "",
        "status": "",
        "doc_type": "",
        "rule_type": "",
        "agents": [],
        "read_error": "",
    }
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()
    except OSError as exc:
        summary["runtime_retrieval"] = None
        summary["read_error"] = str(exc)
        return summary

    metadata = _frontmatter_metadata(content)
    title = str(
        metadata.get("case_title")
        or metadata.get("title")
        or metadata.get("rule_id")
        or ""
    ).strip()
    if not title:
        for line in _strip_frontmatter(content).splitlines():
            stripped = line.strip()
            if stripped.startswith("#"):
                title = stripped.lstrip("#").strip()
                break
    if title:
        summary["title"] = title
    summary["runtime_retrieval"] = _runtime_retrieval_enabled(content)
    summary["priority"] = _canonical_priority(metadata.get("priority"))
    summary["status"] = str(metadata.get("status", "") or "")
    summary["doc_type"] = str(metadata.get("doc_type", "") or "")
    summary["rule_type"] = str(metadata.get("rule_type", "") or "")
    summary["agents"] = _normalise_agent_scope(metadata.get("agent_scope") or metadata.get("served_agents"))
    return summary


def _knowledge_source_state(knowledge_dir: str | None = None) -> dict:
    latest_mtime = None
    latest_file = ""
    file_count = 0
    files: list[dict[str, Any]] = []
    for relpath, filepath in _iter_knowledge_files(knowledge_dir):
        try:
            mtime = os.path.getmtime(filepath)
        except OSError:
            continue
        file_count += 1
        files.append({
            "path": relpath,
            "mtime": mtime,
            "mtime_iso": _format_mtime(mtime),
            **_knowledge_file_summary(relpath, filepath),
        })
        if latest_mtime is None or mtime > latest_mtime:
            latest_mtime = mtime
            latest_file = relpath
    files.sort(key=lambda item: item["mtime"], reverse=True)
    return {
        "file_count": file_count,
        "latest_mtime": latest_mtime,
        "latest_mtime_iso": _format_mtime(latest_mtime),
        "latest_file": latest_file,
        "files": files,
    }


def knowledge_index_status(knowledge_dir: str | None = None) -> dict:
    knowledge_root = os.path.abspath(knowledge_dir or get_knowledge_dir())
    db_path = os.path.abspath(_vectordb_path())
    source_state = _knowledge_source_state(knowledge_root)
    db_exists = os.path.exists(db_path)
    db_mtime = os.path.getmtime(db_path) if db_exists else None
    newer_files = [
        item for item in source_state["files"]
        if db_mtime is None or item["mtime"] > db_mtime
    ]
    legacy_path = os.path.abspath(_legacy_vectordb_path(knowledge_root))
    legacy_exists = os.path.exists(legacy_path) and os.path.normcase(legacy_path) != os.path.normcase(db_path)
    legacy_mtime = os.path.getmtime(legacy_path) if legacy_exists else None
    needs_rebuild = (not db_exists) or bool(newer_files)
    if not db_exists:
        status = "missing"
        message = "未找到运行时向量库，需要先构建。"
    elif newer_files:
        status = "stale"
        message = f"知识库有 {len(newer_files)} 个文件比运行时向量库新，需要重建。"
    else:
        status = "fresh"
        message = "知识库索引是最新的。"
    return {
        "status": status,
        "needs_rebuild": needs_rebuild,
        "message": message,
        "knowledge_dir": knowledge_root,
        "knowledge_file_count": source_state["file_count"],
        "knowledge_latest_file": source_state["latest_file"],
        "knowledge_latest_mtime": source_state["latest_mtime_iso"],
        "knowledge_files": source_state["files"],
        "vectordb_path": db_path,
        "vectordb_exists": db_exists,
        "vectordb_mtime": _format_mtime(db_mtime),
        "newer_file_count": len(newer_files),
        "newer_files": newer_files[:10],
        "legacy_vectordb": {
            "path": legacy_path,
            "exists": legacy_exists,
            "mtime": _format_mtime(legacy_mtime),
            "message": "根目录旧 vectordb 仍存在，仅作旧索引，不是当前运行路径。" if legacy_exists else "",
        },
    }


_vectordb_cache: dict | None = None


def _write_vectordb_json(db_path: str, data: dict) -> None:
    persist_dir = os.path.dirname(db_path)
    os.makedirs(persist_dir, exist_ok=True)
    temp_path = f"{db_path}.tmp.{os.getpid()}"
    try:
        with open(temp_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False)
            f.flush()
            os.fsync(f.fileno())
        if os.path.exists(db_path):
            os.chmod(db_path, stat.S_IREAD | stat.S_IWRITE)
        for attempt in range(4):
            try:
                os.replace(temp_path, db_path)
                break
            except PermissionError:
                if attempt == 3:
                    raise
                time.sleep(0.25 * (attempt + 1))
    except PermissionError as exc:
        raise PermissionError(
            f"无法写入向量库文件：{db_path}。请关闭正在占用该文件的程序，"
            f"确认目录可写后重试。原始错误：{exc}"
        ) from exc
    finally:
        if os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except OSError:
                pass


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
    embeddings = np.array(data["embeddings"], dtype=np.float32)
    data["embeddings"] = embeddings
    data["embedding_dim"] = embeddings.shape[1]
    # 记录构建时的 embedding 模型，便于维度漂移排查
    data["embedding_model"] = data.get("embedding_model", "")

    # 提前检查：embedding 模型/维度与当前配置是否一致
    try:
        cfg = load_config() or {}
        vdb_cfg = cfg.get("vectordb") or {}
        current_model = vdb_cfg.get("embedding_model", "")
        if current_model and data.get("embedding_model") and data["embedding_model"] != current_model:
            warnings.warn(
                f"[Vectordb] embedding_model 不匹配: 向量库由 '{data['embedding_model']}' 构建, "
                f"当前配置为 '{current_model}'。请执行 `python main.py build-db --rebuild` 重建向量库。",
                RuntimeWarning,
                stacklevel=2,
            )
        # 用一个小样本请求验证当前模型返回的维度是否与库存一致
        # 只在缓存首次加载时执行一次，避免每次查询都发请求
        if current_model:
            sample_emb = _embed_texts(["维度校验"], model=current_model, batch_size=1)
            actual_dim = len(sample_emb[0])
            if actual_dim != data["embedding_dim"]:
                warnings.warn(
                    f"[Vectordb] embedding_dim 不匹配: 向量库存储维度={data['embedding_dim']}, "
                    f"当前模型 '{current_model}' 返回维度={actual_dim}。"
                    f"请执行 `python main.py build-db --rebuild` 重建向量库。",
                    RuntimeWarning,
                    stacklevel=2,
                )
    except Exception:
        # 配置可能不完整或网络不通，不阻断加载
        pass

    _vectordb_cache = data
    return data


def build_vectordb(
    knowledge_dir: str = None,
    force_rebuild: bool = False,
    embedding_model_override: str | None = None,
):
    """
    构建向量知识库。
    每个知识文件的切片都会标注来源文件和所属 Agent，
    便于 RAG 检索时按 Agent 过滤。
    """
    global _vectordb_cache
    config = load_config()
    vdb_config = config["vectordb"]
    profile = _load_session_model_profile()
    embedding_model = embedding_model_override or profile.get("embedding_model") or vdb_config["embedding_model"]
    embedding_base_url = profile.get("vectordb_base_url") or vdb_config.get("base_url", "")

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
    print(f"  embedding:     {embedding_model} via {embedding_base_url}")

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

        agents = (
            _normalise_agent_scope(metadata.get("agent_scope"))
            or _normalise_agent_scope(metadata.get("served_agents"))
            or file_to_agents.get(filename, ["all"])
        )

        for i, chunk in enumerate(chunks):
            chunk_metadata = {
                "source_file": filename,
                "chunk_index": i,
                "title": chunk["title"],
                "agents": ",".join(agents),
                "agent_scope": ",".join(_normalise_agent_scope(metadata.get("agent_scope"))),
                "rule_id": str(metadata.get("rule_id", "")),
                "case_title": str(metadata.get("case_title", "")),
                "priority": _canonical_priority(metadata.get("priority")),
                "status": str(metadata.get("status", "")),
                "rule_type": str(metadata.get("rule_type", "")),
                "doc_type": str(metadata.get("doc_type", "")),
            }
            for field in PROFILE_FIELDS:
                chunk_metadata[field] = ", ".join(_normalise_frontmatter_list(metadata.get(field)))
            for field in STANDARD_RULE_METADATA_FIELDS:
                chunk_metadata[field] = ", ".join(_normalise_frontmatter_list(metadata.get(field)))
            all_documents.append(chunk["text"])
            all_metadatas.append(chunk_metadata)

        total_chunks += len(chunks)
        print(f"  [OK] {filename}: {len(chunks)} chunks -> Agent: {', '.join(agents)}")

    # 调用在线 API 获取所有片段的 Embedding
    print(f"\n[INFO] 正在获取 {len(all_documents)} 个片段的 Embedding...")
    all_embeddings = _embed_texts(all_documents, model=embedding_model)
    print(f"  [OK] Embedding 维度: {len(all_embeddings[0])}")

    # 持久化到 JSON 文件（含维度/模型元数据，便于后续一致性检查）
    source_state = _knowledge_source_state(knowledge_dir)
    db_data = {
        "documents": all_documents,
        "metadatas": all_metadatas,
        "embeddings": [list(e) for e in all_embeddings],
        "embedding_model": embedding_model,
        "embedding_dim": len(all_embeddings[0]),
        "built_at": datetime.now().isoformat(timespec="seconds"),
        "knowledge_dir": os.path.abspath(knowledge_dir),
        "knowledge_file_count": source_state["file_count"],
        "knowledge_latest_file": source_state["latest_file"],
        "knowledge_latest_mtime": source_state["latest_mtime_iso"],
    }
    _write_vectordb_json(db_path, db_data)

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

    # 维度一致性检查 —— 提前暴露 embedding 模型切换导致的维度漂移
    stored_dim = db.get("embedding_dim", db["embeddings"].shape[1])
    if query_emb.shape[0] != stored_dim:
        raise RuntimeError(
            f"Embedding 维度不匹配: 向量库存储维度={stored_dim}, "
            f"查询向量维度={query_emb.shape[0]}。"
            f"当前模型返回维度与向量库构建时使用的模型不一致。"
            f"请执行 python main.py build-db --rebuild 重建向量库。"
        )

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
            "metadata": dict(meta),
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


def _metadata_match_score(metadata: dict[str, Any], query_tokens: set[str], agent_name: str | None = None) -> float:
    if not metadata or not query_tokens:
        return 0.0

    score = 0.0
    scope = set(_normalise_agent_scope(metadata.get("agent_scope")))
    served_agents = set(_normalise_agent_scope(metadata.get("served_agents")))
    if agent_name and (agent_name in scope or agent_name in served_agents or "all" in scope or "all" in served_agents):
        score += 0.45

    priority_boosts = {"P0": 0.5, "P1": 0.4, "P2": 0.25, "P3": 0.15, "P4": 0.08, "P5": 0.04}
    score += priority_boosts.get(_canonical_priority(metadata.get("priority")), 0.0)

    searchable_tokens = set(_tokenize_chinese(_metadata_signal_text(metadata)))
    overlap = query_tokens & searchable_tokens
    if overlap:
        score += min(0.5, len(overlap) / max(len(query_tokens), 1))

    avoid_text = "\n".join(_normalise_frontmatter_list(metadata.get("avoid_when")))
    avoid_tokens = set(_tokenize_chinese(avoid_text))
    if avoid_tokens and query_tokens & avoid_tokens:
        score -= PROFILED_AVOID_PENALTY

    return score


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
    source_name = os.path.basename(str(source))
    if source_name in _source_runtime_retrieval_cache:
        return _source_runtime_retrieval_cache[source_name]

    source_path = os.path.join(get_knowledge_dir(), source_name)
    if not os.path.exists(source_path):
        _source_runtime_retrieval_cache[source_name] = False
        return False

    with open(source_path, "r", encoding="utf-8") as f:
        content = f.read()
    enabled = _runtime_retrieval_enabled(content)
    _source_runtime_retrieval_cache[source_name] = enabled
    return enabled


def preferred_sources_from_registry_results(registry_results: list[dict]) -> set[str]:
    sources: set[str] = set()
    for result in registry_results:
        for source in result.get("source_files", []) or []:
            if _source_runtime_retrieval_enabled(source):
                sources.add(os.path.basename(str(source)))
    return sources


def _rule_visible_to_agent(
    rule: dict,
    agent_name: str | None,
    agent_files: set[str] | None = None,
) -> bool:
    if not agent_name:
        return True

    owner_agent = str(rule.get("owner_agent", "")).strip()
    if owner_agent == agent_name:
        return True

    agent_scope = set(_normalise_agent_scope(rule.get("agent_scope")))
    return agent_name in agent_scope


def _score_registry_rule(
    rule: dict,
    query_tokens: set[str],
    agent_name: str | None,
    agent_files: set[str] | None = None,
) -> float:
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

    agent_scope = set(_normalise_agent_scope(rule.get("agent_scope")))
    if agent_name and rule.get("owner_agent") == agent_name:
        score += 0.75
    elif agent_name and agent_name in agent_scope:
        score += 0.55

    if agent_name:
        if agent_files is None:
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

    agent_files = set(get_agent_knowledge_files(agent_name)) if agent_name else set()
    scored_rules = []
    for rule in rules:
        if not isinstance(rule, dict):
            continue
        if not _rule_visible_to_agent(rule, agent_name, agent_files):
            continue

        score = _score_registry_rule(rule, query_tokens, agent_name, agent_files)
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
            "agent_scope": rule.get("agent_scope", []),
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
        metadata = _frontmatter_metadata(content)
        chunks = chunk_markdown(content, chunk_size=chunk_size, chunk_overlap=chunk_overlap)
        for chunk in chunks:
            all_chunks.append({
                "text": chunk["text"],
                "title": chunk.get("title", ""),
                "source": filename,
                "metadata": metadata,
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
    metadata_profile: bool = False,
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
    query_tokens_for_profile = set(_tokenize_chinese(query)) if metadata_profile else set()
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
        metadata_boost = (
            _metadata_match_score(chunk.get("metadata", {}), query_tokens_for_profile, agent_name)
            * PROFILED_METADATA_BOOST
            if metadata_profile
            else 0.0
        )
        pieces.append({
            "text": chunk["text"],
            "source": chunk["source"],
            "title": chunk["title"],
            "relevance": score + source_boost + metadata_boost,
            "base_relevance": score,
            "source_boost": source_boost,
            "metadata_boost": metadata_boost,
            "metadata": chunk.get("metadata", {}),
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
    metadata_profile: bool = False,
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
                metadata_profile=metadata_profile,
            )
        except Exception:
            pass

    # ---- 向量路 ----
    vector_results = []
    vector_error = None
    try:
        vector_results = query_knowledge(
            query,
            agent_name,
            n_results=vector_k,
            preferred_sources=preferred_source_names,
        )
    except Exception as exc:
        vector_error = exc
        # 不静默吞掉：明确记录 vector 路失败原因，同时保留 BM25 兜底通道
        warnings.warn(
            f"[query_knowledge_hybrid] Vector search failed: {exc}. "
            f"Falling back to BM25-only results for this query.",
            RuntimeWarning,
            stacklevel=2,
        )

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
            "metadata": meta.get("metadata", {}),
        })
    return results


def _profile_rerank_results(
    results: list[dict],
    query: str,
    agent_name: str,
    n_results: int,
) -> list[dict]:
    query_tokens = set(_tokenize_chinese(query))
    reranked: list[dict] = []
    for item in results:
        metadata = item.get("metadata", {}) if isinstance(item.get("metadata"), dict) else {}
        metadata_score = _metadata_match_score(metadata, query_tokens, agent_name)
        source = item.get("source", "")
        rule_card_bonus = 0.2 if "/rules/" in str(source).replace("\\", "/") or str(source).startswith("rules/") else 0.0
        profiled_score = float(item.get("relevance", 0.0)) + metadata_score + rule_card_bonus
        if metadata_score < -0.2:
            continue
        reranked.append({
            **item,
            "profiled_relevance": profiled_score,
            "metadata_score": metadata_score,
        })

    reranked.sort(key=lambda item: item.get("profiled_relevance", item.get("relevance", 0)), reverse=True)
    return reranked[:n_results]


def query_knowledge_profiled(
    query: str,
    agent_name: str,
    n_results: int = 8,
    bm25_k: int = 12,
    vector_k: int = 12,
    preferred_sources: list[str] | set[str] | tuple[str, ...] | None = None,
) -> list[dict]:
    """Task-profiled retrieval for Obsidian-style rule cards.

    This keeps the existing BM25/vector channels but reranks results with
    frontmatter fields such as agent_scope, priority, applies_when, signals,
    scene_types, risks and avoid_when.
    """
    candidates = query_knowledge_hybrid(
        query=query,
        agent_name=agent_name,
        n_results=max(n_results * 3, n_results),
        bm25_k=max(bm25_k, n_results * 2),
        vector_k=max(vector_k, n_results * 2),
        preferred_sources=preferred_sources,
        metadata_profile=True,
    )
    return _profile_rerank_results(candidates, query, agent_name, n_results)


def _profile_int(value: Any, default: int, minimum: int = 1) -> int:
    if value is None:
        return default
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return default
    return parsed if parsed >= minimum else default


def _merge_retrieval_profiles(base: dict[str, Any], override: dict[str, Any] | None) -> dict[str, Any]:
    merged = dict(base or {})
    for key, value in (override or {}).items():
        if key == "case_card_limits" and isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = {**merged[key], **value}
        elif key in PROFILE_FIELDS or key in {"exclude_status"}:
            items = _normalise_frontmatter_list(merged.get(key))
            items.extend(_normalise_frontmatter_list(value))
            merged[key] = list(dict.fromkeys(items))
        else:
            merged[key] = value
    return merged


def _bootstrap_policy_profile(profile: dict[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in (profile or {}).items()
        if key in {"exclude_status", "case_card_limits", "retrieval_key"}
    }


def _status_is_excluded(status: Any, excluded_statuses: Any) -> bool:
    status_value = str(status or "").strip().lower()
    if not status_value:
        return False
    excluded = {str(item).strip().lower() for item in _normalise_frontmatter_list(excluded_statuses)}
    if status_value in excluded:
        return True
    return status_value == "draft" and any(item.startswith("draft") for item in excluded)


def _filter_results_by_excluded_status(results: list[dict], excluded_statuses: Any) -> list[dict]:
    if not excluded_statuses:
        return results
    filtered = []
    for item in results:
        metadata = item.get("metadata", {}) if isinstance(item.get("metadata"), dict) else {}
        if _status_is_excluded(metadata.get("status"), excluded_statuses):
            continue
        filtered.append(item)
    return filtered


def _case_result_limit(final_top_k: int, profile_options: dict[str, Any]) -> int | None:
    limits = profile_options.get("case_card_limits")
    if not isinstance(limits, dict):
        return None
    share = limits.get("max_share_of_context")
    try:
        max_share = float(share)
    except (TypeError, ValueError):
        return None
    if max_share < 0:
        return None
    return max(0, int(final_top_k * max_share))


def _is_case_result(item: dict) -> bool:
    metadata = item.get("metadata", {}) if isinstance(item.get("metadata"), dict) else {}
    source = str(item.get("source", "")).replace("\\", "/")
    return metadata.get("doc_type") == "case_card" or source.startswith("cases/") or "/cases/" in source


def _limit_case_results(results: list[dict], max_cases: int | None) -> list[dict]:
    if max_cases is None:
        return results
    case_count = 0
    limited = []
    for item in results:
        if _is_case_result(item):
            if case_count >= max_cases:
                continue
            case_count += 1
        limited.append(item)
    return limited


def get_smart_knowledge(
    agent_name: str,
    context_hint: str = "",
    retrieval_profile: dict[str, Any] | None = None,
    retrieval_mode: str | None = None,
    allow_critical_fallback: bool = True,
) -> str:
    """
    智能知识获取主接口。
    根据 config 中 retrieval_mode 决定检索策略：
      - full:   全文注入（现有行为）
      - bm25:   BM25 关键词检索
      - hybrid: BM25 + 向量混合检索（推荐）
      - profiled: 先按任务信号/规则元数据路由，再混合检索

    旧模式下检索结果不足 min_chunks_fallback 个时，自动 fallback 到全文注入。
    profiled 模式不全文回退，只补 critical 规则以避免大知识库污染。
    """
    config = load_config()
    kb_config = config.get("knowledge", {})
    mode = retrieval_mode or kb_config.get("retrieval_mode", "full")
    bootstrap_profile = build_agent_bootstrap_retrieval_profile(agent_name)
    if mode == "profiled" and not retrieval_profile:
        profile_options = bootstrap_profile
    else:
        profile_options = _merge_retrieval_profiles(_bootstrap_policy_profile(bootstrap_profile), retrieval_profile)
    final_top_k = _profile_int(
        profile_options.get("final_top_k", profile_options.get("top_k")),
        kb_config.get("final_top_k", 8),
    )
    min_fallback = _profile_int(
        profile_options.get("min_chunks_fallback"),
        kb_config.get("min_chunks_fallback", 3),
        minimum=0,
    )
    registry_top_k = _profile_int(
        profile_options.get("registry_top_k"),
        kb_config.get("registry_top_k", 4),
        minimum=0,
    )
    max_chunks_per_source = _profile_int(profile_options.get("max_chunks_per_source"), 0, minimum=0)
    profiled_mode = mode == "profiled"
    query_hint = build_retrieval_profile_query(context_hint, profile_options)
    wiki_text, wiki_sources = get_agent_wiki_context(agent_name)

    # 全文模式直接返回
    if mode == "full" or (not query_hint.strip() and not profiled_mode):
        return get_full_knowledge_for_agent(agent_name), {
            "retrieval_mode": mode,
            "used_full_fallback": True,
            "used_wiki_context": bool(wiki_sources),
            "wiki_sources": wiki_sources,
            "matched_sources": get_agent_knowledge_files(agent_name),
            "critical_sources": get_agent_knowledge_files(agent_name, critical_only=True),
            "result_count": 0,
            "registry_result_count": 0,
            "registry_rule_ids": [],
            "registry_preferred_sources": [],
            "context_hint": context_hint,
            "retrieval_profile": profile_options,
        }

    if registry_top_k > 0:
        registry_text, registry_results = get_rule_registry_context(
            query=query_hint,
            agent_name=agent_name,
            n_results=registry_top_k,
        )
    else:
        registry_text, registry_results = "", []
    registry_rule_ids = [item.get("rule_id", "") for item in registry_results if item.get("rule_id")]
    registry_preferred_sources = sorted(preferred_sources_from_registry_results(registry_results))

    # 检索
    results = []
    try:
        if profiled_mode:
            bm25_k = _profile_int(profile_options.get("bm25_top_k"), kb_config.get("bm25_top_k", 12))
            vector_k = _profile_int(profile_options.get("vector_top_k"), kb_config.get("vector_top_k", 12))
            results = query_knowledge_profiled(
                query=query_hint,
                agent_name=agent_name,
                n_results=final_top_k,
                bm25_k=bm25_k,
                vector_k=vector_k,
                preferred_sources=registry_preferred_sources,
            )
        elif mode == "hybrid":
            bm25_k = _profile_int(profile_options.get("bm25_top_k"), kb_config.get("bm25_top_k", 10))
            vector_k = _profile_int(profile_options.get("vector_top_k"), kb_config.get("vector_top_k", 10))
            results = query_knowledge_hybrid(
                query=query_hint,
                agent_name=agent_name,
                n_results=final_top_k,
                bm25_k=bm25_k,
                vector_k=vector_k,
                preferred_sources=registry_preferred_sources,
            )
        elif mode == "bm25":
            results = query_knowledge_bm25(
                query=query_hint,
                agent_name=agent_name,
                n_results=final_top_k,
                preferred_sources=registry_preferred_sources,
            )
        else:
            full_text = get_full_knowledge_for_agent(agent_name)
            return full_text, {
                "retrieval_mode": mode,
                "used_full_fallback": True,
                "used_wiki_context": bool(wiki_sources),
                "wiki_sources": wiki_sources,
                "matched_sources": get_agent_knowledge_files(agent_name),
                "critical_sources": get_agent_knowledge_files(agent_name, critical_only=True),
                "result_count": 0,
                "registry_result_count": len(registry_results),
                "registry_rule_ids": registry_rule_ids,
                "registry_preferred_sources": registry_preferred_sources,
                "context_hint": context_hint,
                "query_hint": query_hint,
                "retrieval_profile": profile_options,
            }
    except Exception as e:
        fallback_kind = "critical_only" if profiled_mode and allow_critical_fallback else "empty"
        if not profiled_mode:
            fallback_kind = "full"
        print(f"[WARN] 知识检索失败 ({mode}): {e}，回退 {fallback_kind} 注入。")
        full_text = (
            get_full_knowledge_for_agent(agent_name, critical_only=profiled_mode)
            if (not profiled_mode or allow_critical_fallback)
            else ""
        )
        return full_text, {
            "retrieval_mode": mode,
            "used_full_fallback": not profiled_mode,
            "used_critical_fallback": bool(profiled_mode and allow_critical_fallback),
            "used_wiki_context": bool(wiki_sources),
            "wiki_sources": wiki_sources,
            "matched_sources": get_agent_knowledge_files(agent_name),
            "critical_sources": get_agent_knowledge_files(agent_name, critical_only=True),
            "result_count": 0,
            "registry_result_count": len(registry_results),
            "registry_rule_ids": registry_rule_ids,
            "registry_preferred_sources": registry_preferred_sources,
            "context_hint": context_hint,
            "query_hint": query_hint,
            "retrieval_profile": profile_options,
            "error": str(e),
        }

    raw_result_count = len(results)
    results = _filter_results_by_excluded_status(results, profile_options.get("exclude_status"))
    results = _limit_case_results(results, _case_result_limit(final_top_k, profile_options))
    if max_chunks_per_source > 0:
        source_counts: dict[str, int] = {}
        filtered_results = []
        for index, item in enumerate(results):
            source = item.get("source") or f"__unknown_{index}"
            count = source_counts.get(source, 0)
            if count >= max_chunks_per_source:
                continue
            source_counts[source] = count + 1
            filtered_results.append(item)
        results = filtered_results

    # 结果不足，fallback 全文
    if len(results) < min_fallback and not profiled_mode:
        print(f"[INFO] 检索结果仅 {len(results)} 条 < {min_fallback}，回退全文注入。")
        full_text = get_full_knowledge_for_agent(agent_name)
        return full_text, {
            "retrieval_mode": mode,
            "used_full_fallback": True,
            "used_wiki_context": bool(wiki_sources),
            "wiki_sources": wiki_sources,
            "matched_sources": sorted({item.get("source", "") for item in results if item.get("source")}),
            "critical_sources": get_agent_knowledge_files(agent_name, critical_only=True),
            "result_count": len(results),
            "raw_result_count": raw_result_count,
            "registry_result_count": len(registry_results),
            "registry_rule_ids": registry_rule_ids,
            "registry_preferred_sources": registry_preferred_sources,
            "context_hint": context_hint,
            "query_hint": query_hint,
            "retrieval_profile": profile_options,
        }

    # 拼接检索到的知识片段
    parts = []
    seen_sources = set()
    if wiki_text:
        parts.append(wiki_text)
        seen_sources.update(wiki_sources)
    if registry_text:
        parts.append(registry_text)
        seen_sources.add(RULE_REGISTRY_FILENAME)
    for item in results:
        source = item.get("source", "")
        if source and source not in seen_sources:
            parts.append(f"--- {source} (精选片段) ---")
            seen_sources.add(source)
        parts.append(item["text"])
    if profiled_mode and allow_critical_fallback and len(results) < min_fallback:
        critical_text = get_full_knowledge_for_agent(agent_name, critical_only=True)
        if critical_text:
            parts.append("--- critical_rules (profiled fallback) ---")
            parts.append(critical_text)
            seen_sources.update(get_agent_knowledge_files(agent_name, critical_only=True))
    return "\n\n".join(parts), {
        "retrieval_mode": mode,
        "used_full_fallback": False,
        "used_critical_fallback": bool(profiled_mode and allow_critical_fallback and len(results) < min_fallback),
        "used_wiki_context": bool(wiki_sources),
        "wiki_sources": wiki_sources,
        "matched_sources": sorted(seen_sources),
        "critical_sources": get_agent_knowledge_files(agent_name, critical_only=True),
        "result_count": len(results),
        "raw_result_count": raw_result_count,
        "registry_result_count": len(registry_results),
        "registry_rule_ids": registry_rule_ids,
        "registry_preferred_sources": registry_preferred_sources,
        "context_hint": context_hint,
        "query_hint": query_hint,
        "retrieval_profile": profile_options,
    }


if __name__ == "__main__":
    import sys
    force = "--rebuild" in sys.argv
    build_vectordb(force_rebuild=force)
