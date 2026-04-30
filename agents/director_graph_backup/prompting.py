from __future__ import annotations

from typing import Any

from ..knowledge_base import (
    get_agent_knowledge_files,
    get_full_knowledge_for_agent,
    get_smart_knowledge,
    load_knowledge_documents,
)
from .types import DirectorState


def _critical_knowledge_block(agent_name: str) -> str:
    critical_docs = load_knowledge_documents(agent_name, get_agent_knowledge_files(agent_name, critical_only=True))
    if not critical_docs:
        return ""
    return "\n\n".join(f"--- {doc['filename']} (关键规则) ---\n{doc['content']}" for doc in critical_docs)


def _knowledge_metadata(state: DirectorState) -> dict[str, Any]:
    return dict(state.get("knowledge_metadata") or {})


def _record_knowledge_metadata(
    state: DirectorState,
    agent_name: str,
    context_hint: str,
    retrieval_meta: dict[str, Any] | None,
) -> dict[str, Any]:
    metadata = _knowledge_metadata(state)
    metadata[agent_name] = {
        "context_hint": context_hint,
        "critical_sources": get_agent_knowledge_files(agent_name, critical_only=True),
        "all_sources": get_agent_knowledge_files(agent_name),
        **(retrieval_meta or {}),
    }
    return metadata


def build_system_prompt(role_description: str, agent_name: str, context_hint: str = "") -> tuple[str, dict[str, Any]]:
    critical_text = _critical_knowledge_block(agent_name)
    retrieval_meta: dict[str, Any] = {}
    try:
        kb_text, retrieval_meta = get_smart_knowledge(agent_name, context_hint)
    except Exception:
        kb_text = get_full_knowledge_for_agent(agent_name)
        retrieval_meta = {
            "retrieval_mode": "fallback",
            "used_full_fallback": True,
            "matched_sources": get_agent_knowledge_files(agent_name),
            "critical_sources": get_agent_knowledge_files(agent_name, critical_only=True),
            "result_count": 0,
            "context_hint": context_hint,
        }

    knowledge_sections = []
    if critical_text:
        knowledge_sections.append("===== 以下是必须优先执行的关键规则 =====\n" + critical_text)
    if kb_text:
        knowledge_sections.append("===== 以下是补充知识库规则 =====\n" + kb_text)

    system_prompt = (
        f"{role_description}\n\n"
        + "\n\n".join(knowledge_sections)
        + "\n===== 规则结束 =====\n"
        + "请严格遵守上述规则，并直接输出结果，不要包含寒暄或无关内容。"
    )
    return system_prompt, retrieval_meta
