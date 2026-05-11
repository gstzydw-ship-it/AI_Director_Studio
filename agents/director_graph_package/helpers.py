"""Shared helpers and compatibility wrappers for director graph package code."""
from __future__ import annotations

import json
import os
import re
import time
from typing import Any

import httpx
import yaml

from .types import (
    AGENT_CONFIG_PARENTS,
    CONFIG_FILE,
    DEFAULT_LLM_MODEL,
    LLMSettings,
    STORY_PLANNER_MAX_SCHEMA_ATTEMPTS,
)
from ..knowledge_base import (
    get_agent_knowledge_files,
    get_full_knowledge_for_agent,
    get_smart_knowledge,
    load_knowledge_documents,
)
from ..utils import COMFLY_BASE_URL, load_yaml_config


_BODY_MECHANICS_ACTION_RE = re.compile(
    r"进入|走进|冲入|冲向|穿过|越过|进电梯|进门|出门|碰撞|撞上|扶住|松开|擦身而过|过阈值|转身|离开|"
    r"拿起|放下|递给|交给|推开|拉开|关上|打开|下车|上车|起身|坐下|后退|让出|站到|移动|行走|奔跑"
)


def load_config() -> dict[str, Any]:
    try:
        return load_yaml_config(CONFIG_FILE)
    except yaml.YAMLError as exc:
        print(f"  [Config] WARN: YAML parse failed ({CONFIG_FILE}): {exc}")
        return {}
    except OSError as exc:
        print(f"  [Config] WARN: unable to read config ({CONFIG_FILE}): {exc}")
        return {}
def _as_mapping(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _normalise_base_url(base_url: Any) -> str:
    value = str(base_url or "").strip()
    if value and not value.startswith(("http://", "https://")):
        value = f"https://{value}"
    return value.rstrip("/")


def _normalise_model_name(model: Any) -> str:
    value = str(model or "").strip()
    if value.startswith("openai/"):
        value = value.replace("openai/", "", 1)
    return value


def _optional_float(value: Any) -> float | None:
    try:
        return float(value) if value is not None else None
    except (TypeError, ValueError):
        return None


def _agent_config_layers(full_config: dict[str, Any], agent_name: str) -> list[tuple[str, dict[str, Any]]]:
    """Return inherited config layers in increasing priority order."""
    if not agent_name:
        return []

    agent_models = _as_mapping(full_config.get("agent_models"))
    layers: list[tuple[str, dict[str, Any]]] = []

    parent_name = AGENT_CONFIG_PARENTS.get(agent_name)
    parent_cfg = _as_mapping(agent_models.get(parent_name)) if parent_name else {}
    if parent_name and parent_cfg:
        layers.append((parent_name, parent_cfg))

    agent_cfg = _as_mapping(agent_models.get(agent_name))
    if agent_cfg:
        layers.append((agent_name, agent_cfg))

    return layers


def _apply_llm_config_layer(settings: dict[str, Any], layer: dict[str, Any]) -> None:
    if layer.get("api_key"):
        settings["api_key"] = layer["api_key"]
    if layer.get("base_url"):
        settings["base_url"] = layer["base_url"]
    if layer.get("model"):
        settings["model"] = layer["model"]
    if "temperature" in layer:
        settings["temperature"] = layer["temperature"]


def resolve_llm_settings(agent_name: str = "", full_config: dict[str, Any] | None = None) -> LLMSettings:
    """Resolve LLM settings into a validation-friendly object.

    优先级（从低到高）：
        1. 代码默认值（COMFLY_BASE_URL / DEFAULT_LLM_MODEL）
        2. llm.* 全局配置
        3. 环境变量 DIRECTOR_LLM_API_KEY / DIRECTOR_LLM_MODEL
        4. parent agent 配置（如 shot_director_layout 继承 shot_director）
        5. agent_models.<agent_name>.* 当前 agent 覆盖
    """
    config = load_config() if full_config is None else full_config
    llm_config = _as_mapping(config.get("llm"))
    raw_settings: dict[str, Any] = {
        "api_key": llm_config.get("api_key", "") or "",
        "base_url": llm_config.get("base_url") or COMFLY_BASE_URL,
        "model": llm_config.get("model") or DEFAULT_LLM_MODEL,
        "temperature": llm_config.get("temperature"),
    }

    env_api_key = os.getenv("DIRECTOR_LLM_API_KEY")
    env_model = os.getenv("DIRECTOR_LLM_MODEL")
    if env_api_key:
        raw_settings["api_key"] = env_api_key
    if env_model:
        raw_settings["model"] = env_model

    layers = _agent_config_layers(config, agent_name)
    for _layer_name, layer in layers:
        _apply_llm_config_layer(raw_settings, layer)

    return LLMSettings(
        agent_name=agent_name,
        api_key=str(raw_settings.get("api_key") or "").strip(),
        base_url=_normalise_base_url(raw_settings.get("base_url")),
        model=_normalise_model_name(raw_settings.get("model")),
        temperature=_optional_float(raw_settings.get("temperature")),
        config_path=CONFIG_FILE,
        parent_agent=AGENT_CONFIG_PARENTS.get(agent_name) if layers else None,
    )


def _get_llm_settings(agent_name: str = "") -> tuple[str, str, str, float | None]:
    """Backward-compatible tuple API for older call sites."""
    return resolve_llm_settings(agent_name).as_tuple()


def _get_llm_extra_params(agent_name: str = "") -> dict[str, Any]:
    """解析 llm.extra_params 与 agent_models.<name>.extra_params 的合并结果。

    这个字段用于透传 Claude thinking / GPT-5 reasoning_effort / response_format
    等 provider-specific 参数给 Comfly（或任何 OpenAI 兼容网关）。
    """
    full_config = load_config()
    merged: dict[str, Any] = {}

    global_extra = _as_mapping(full_config.get("llm")).get("extra_params")
    if isinstance(global_extra, dict):
        merged.update(global_extra)

    for _layer_name, layer in _agent_config_layers(full_config, agent_name):
        agent_extra = layer.get("extra_params")
        if isinstance(agent_extra, dict):
            merged.update(agent_extra)

    return merged


def _coerce_float(value: Any, default: float, minimum: float | None = None) -> float:
    try:
        resolved = float(value)
    except (TypeError, ValueError):
        resolved = default
    if minimum is not None:
        resolved = max(minimum, resolved)
    return resolved


def _coerce_int(value: Any, default: int, minimum: int | None = None) -> int:
    try:
        resolved = int(value)
    except (TypeError, ValueError):
        resolved = default
    if minimum is not None:
        resolved = max(minimum, resolved)
    return resolved


def _get_llm_runtime_option(agent_name: str, key: str, default: Any) -> Any:
    full_config = load_config()
    value = _as_mapping(full_config.get("llm")).get(key, default)
    for _layer_name, layer in _agent_config_layers(full_config, agent_name):
        if key in layer:
            value = layer[key]
    return value


def _normalise_model_list(value: Any) -> list[str]:
    if isinstance(value, str):
        candidates = re.split(r"[,\n]+", value)
    elif isinstance(value, (list, tuple)):
        candidates = value
    else:
        candidates = []

    models: list[str] = []
    for candidate in candidates:
        model = _normalise_model_name(candidate)
        if model and model not in models:
            models.append(model)
    return models


def _get_llm_fallback_models(agent_name: str = "") -> list[str]:
    full_config = load_config()
    value = _as_mapping(full_config.get("llm")).get("fallback_models", [])
    for _layer_name, layer in _agent_config_layers(full_config, agent_name):
        if "fallback_models" in layer:
            value = layer["fallback_models"]
    return _normalise_model_list(value)


def _raise_llm_failure(
    last_exc: Exception | None,
    *,
    agent_name: str,
    model: str,
    max_retries: int,
    images_base64: list[str] | None,
    attempted_models: list[str],
) -> None:
    attempted_note = f"；尝试模型: {', '.join(attempted_models)}" if attempted_models else ""
    if isinstance(last_exc, httpx.RemoteProtocolError):
        cause_hint = (
            "常见原因是参考图过大、上游代理超时或模型网关临时中断，请压缩参考图后重试。"
            if images_base64
            else "常见原因是上游模型网关临时断流或代理超时；本次请求未发送参考图。"
        )
        raise RuntimeError(
            f"LLM 服务在返回前断开连接（agent={agent_name or '?'}, model={model}，已重试 {max_retries} 次{attempted_note}）。"
            f"{cause_hint}"
        ) from last_exc
    if isinstance(last_exc, httpx.ConnectError):
        raise RuntimeError(
            f"LLM 网络连接失败（已重试 {max_retries} 次{attempted_note}）。"
            "已默认绕开环境代理；如果仍失败，通常是上游网关 TLS 抖动或本机网络中断，请稍后重试。"
        ) from last_exc
    if isinstance(last_exc, httpx.TimeoutException):
        raise RuntimeError(
            f"LLM 服务响应超时（已重试 {max_retries} 次{attempted_note}）。请减少参考图数量或稍后重试。"
        ) from last_exc
    if isinstance(last_exc, httpx.HTTPStatusError):
        if last_exc.response is not None:
            try:
                detail = (last_exc.response.text or "")[:800]
            except Exception:
                detail = ""
            status_code = last_exc.response.status_code
        else:
            detail = ""
            status_code = "unknown"
        raise RuntimeError(
            f"LLM 接口返回 HTTP {status_code}（agent={agent_name or '?'}, model={model}，已重试 {max_retries} 次{attempted_note}）: {detail}"
        ) from last_exc
    raise RuntimeError(f"LLM 调用失败（已重试 {max_retries} 次{attempted_note}）: {last_exc}") from last_exc


def _default_llm_timeout_seconds(model: str, extra_params: dict[str, Any]) -> float:
    model_name = (model or "").lower()
    thinking = extra_params.get("thinking")
    if isinstance(thinking, dict) and thinking.get("type") == "enabled":
        return 240.0
    if "thinking" in model_name:
        return 240.0
    if "opus" in model_name:
        return 180.0
    return 120.0


def _extract_message_text(message: dict[str, Any]) -> str:
    """把 OpenAI 风格 message.content 解析成纯文本。

    兼容三种返回形态：
      1. 字符串（标准 OpenAI / 大多数 Comfly 路由）
      2. Anthropic 风格的 block 数组 [{type: thinking/text, ...}]
      3. 兼容 reasoning_content / output_text 的降级字段
    """
    content = message.get("content")
    if content is None:
        for alt_key in ("reasoning_content", "output_text", "text"):
            alt = message.get(alt_key)
            if isinstance(alt, str) and alt:
                return alt
        return ""

    if isinstance(content, str):
        return content

    if isinstance(content, list):
        texts: list[str] = []
        for block in content:
            if not isinstance(block, dict):
                texts.append(str(block))
                continue
            btype = block.get("type")
            if btype in {"thinking", "reasoning"}:
                # thinking 块不参与最终输出，仅保留方便 debug
                continue
            if btype in {"text", "output_text"}:
                texts.append(str(block.get("text") or block.get("content") or ""))
            elif btype == "json":
                texts.append(json.dumps(block.get("json") or {}, ensure_ascii=False))
            else:
                fallback = block.get("text") or block.get("content")
                if fallback:
                    texts.append(str(fallback))
        return "\n".join(t for t in texts if t).strip()

    return str(content)


def call_llm(
    system_prompt: str,
    user_prompt: str,
    images_base64: list[str] | None = None,
    temperature: float = 0.4,
    agent_name: str = "",
    max_retries: int | None = None,
    bypass_proxy: bool = True,
) -> str:
    import time as _time

    settings = resolve_llm_settings(agent_name)
    settings.require_valid()
    api_key, base_url, model, agent_temperature = settings.as_tuple()
    if agent_temperature is not None:
        temperature = agent_temperature

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    messages: list[dict[str, Any]] = [{"role": "system", "content": system_prompt}]

    if images_base64:
        content: list[dict[str, Any]] = [{"type": "text", "text": user_prompt}]
        for image in images_base64:
            image_url = image if image.startswith("data:") else f"data:image/jpeg;base64,{image}"
            content.append(
                {
                    "type": "image_url",
                    "image_url": {"url": image_url},
                }
            )
        messages.append({"role": "user", "content": content})
    else:
        messages.append({"role": "user", "content": user_prompt})

    base_payload: dict[str, Any] = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
    }

    max_tokens = _coerce_int(_get_llm_runtime_option(agent_name, "max_tokens", 0), 0)
    if max_tokens > 0:
        base_payload["max_tokens"] = max_tokens

    # 透传 agent/全局 extra_params（thinking / reasoning_effort / response_format 等）
    extra_params = _get_llm_extra_params(agent_name)
    if extra_params:
        for key, value in extra_params.items():
            # temperature 已由 agent_temperature 覆盖，避免 extra_params 再次冲突
            if key == "temperature":
                continue
            base_payload[key] = value
        # Claude thinking 模式强制要求 temperature=1.0
        if isinstance(extra_params.get("thinking"), dict) and extra_params["thinking"].get("type") == "enabled":
            base_payload["temperature"] = 1.0
            budget = extra_params["thinking"].get("budget_tokens", 0)
            if isinstance(budget, (int, float)) and budget > 0:
                needed = int(budget) + 8192
                if max_tokens <= 0 or max_tokens < needed:
                    base_payload["max_tokens"] = needed

    if max_retries is None:
        max_retries = _coerce_int(_get_llm_runtime_option(agent_name, "max_retries", 2), 2, minimum=1)
    else:
        max_retries = max(1, int(max_retries))

    # 默认直连 Comfly，避免 UI/测试进程遗留的代理环境变量把 TLS 握手导向本机代理。
    trust_env = not bypass_proxy
    last_exc: Exception | None = None
    last_retryable = False
    models_to_try = _normalise_model_list([model, *_get_llm_fallback_models(agent_name)])
    attempted_models: list[str] = []

    for model_index, active_model in enumerate(models_to_try):
        attempted_models.append(active_model)
        payload = dict(base_payload)
        payload["model"] = active_model

        if agent_name:
            fallback_note = " fallback" if model_index else ""
            print(f"  [LLM] {agent_name} -> {active_model} @ {settings.host}{fallback_note}")

        default_timeout = _default_llm_timeout_seconds(active_model, extra_params)
        request_timeout = _coerce_float(
            _get_llm_runtime_option(agent_name, "timeout_seconds", default_timeout),
            default_timeout,
            minimum=30.0,
        )
        connect_timeout = _coerce_float(
            _get_llm_runtime_option(agent_name, "connect_timeout_seconds", min(30.0, request_timeout)),
            min(30.0, request_timeout),
            minimum=5.0,
        )
        read_timeout = _coerce_float(
            _get_llm_runtime_option(agent_name, "read_timeout_seconds", request_timeout),
            request_timeout,
            minimum=30.0,
        )
        write_timeout = _coerce_float(
            _get_llm_runtime_option(agent_name, "write_timeout_seconds", min(60.0, request_timeout)),
            min(60.0, request_timeout),
            minimum=10.0,
        )
        timeout = httpx.Timeout(request_timeout, connect=connect_timeout, read=read_timeout, write=write_timeout)

        for attempt in range(1, max_retries + 1):
            try:
                with httpx.Client(timeout=timeout, trust_env=trust_env) as client:
                    response = client.post(f"{base_url}/chat/completions", headers=headers, json=payload)
                    response.raise_for_status()
                    result = response.json()
                # 防御式解析：上游可能返回非标格式（choices 缺失、消息无 content 等）
                if not isinstance(result, dict):
                    raise RuntimeError(f"LLM 响应格式异常，期待 dict，得到 {type(result).__name__}：{str(result)[:400]}")
                choices = result.get("choices")
                if not choices or not isinstance(choices, list):
                    raise RuntimeError(f"LLM 响应缺少 choices 字段：{json.dumps(result, ensure_ascii=False)[:500]}")
                message = (choices[0] or {}).get("message") or {}
                text = _extract_message_text(message)
                return text.strip()
            except (httpx.RemoteProtocolError, httpx.ConnectError, httpx.NetworkError) as exc:
                last_exc = exc
                last_retryable = True
            except httpx.TimeoutException as exc:
                last_exc = exc
                last_retryable = True
            except httpx.HTTPStatusError as exc:
                last_exc = exc
                status_code = exc.response.status_code if exc.response is not None else 0
                # 仅对 5xx 服务端错误重试，4xx 客户端错误直接失败
                last_retryable = (status_code >= 500)
            except Exception as exc:
                last_exc = exc
                last_retryable = False

            if not last_retryable or attempt == max_retries:
                break

            wait_seconds = 2 ** attempt  # 2s, 4s, 8s, 16s 指数退避
            print(f"  [LLM] WARN: attempt {attempt} failed on {active_model} ({type(last_exc).__name__}); retrying in {wait_seconds}s...")
            _time.sleep(wait_seconds)

        if last_retryable and model_index < len(models_to_try) - 1:
            next_model = models_to_try[model_index + 1]
            print(f"  [LLM] WARN: {active_model} failed after {max_retries} attempts; trying fallback model {next_model}...")
            continue
        break

    _raise_llm_failure(
        last_exc,
        agent_name=agent_name,
        model=attempted_models[-1] if attempted_models else model,
        max_retries=max_retries,
        images_base64=images_base64,
        attempted_models=attempted_models,
    )


def _critical_knowledge_block(agent_name: str) -> str:
    critical_docs = load_knowledge_documents(agent_name, get_agent_knowledge_files(agent_name, critical_only=True))
    if not critical_docs:
        return ""
    return "\n\n".join(f"--- {doc['filename']} (关键规则) ---\n{doc['content']}" for doc in critical_docs)


def build_system_prompt(
    role_description: str,
    agent_name: str,
    context_hint: str = "",
    retrieval_profile: dict[str, Any] | None = None,
    include_critical_knowledge: bool = True,
    fallback_to_full_knowledge: bool = True,
    retrieval_mode: str | None = None,
) -> tuple[str, dict[str, Any]]:
    critical_text = _critical_knowledge_block(agent_name) if include_critical_knowledge else ""
    retrieval_meta: dict[str, Any] = {}
    try:
        kb_text, retrieval_meta = get_smart_knowledge(
            agent_name,
            context_hint,
            retrieval_profile=retrieval_profile,
            retrieval_mode=retrieval_mode,
            allow_critical_fallback=include_critical_knowledge,
        )
    except Exception:
        kb_text = get_full_knowledge_for_agent(agent_name) if fallback_to_full_knowledge else ""
        retrieval_meta = {
            "retrieval_mode": "fallback",
            "used_full_fallback": fallback_to_full_knowledge,
            "matched_sources": get_agent_knowledge_files(agent_name),
            "critical_sources": get_agent_knowledge_files(agent_name, critical_only=True),
            "result_count": 0,
            "context_hint": context_hint,
            "retrieval_profile": retrieval_profile or {},
            "include_critical_knowledge": include_critical_knowledge,
            "fallback_to_full_knowledge": fallback_to_full_knowledge,
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


def _primary_script_character_names(script: str) -> list[str]:
    for line in (script or "").splitlines():
        stripped = line.strip()
        if not stripped.startswith("人物"):
            continue
        _, _, names_text = stripped.partition("：")
        names = [name.strip() for name in re.split(r"[、,，/和\s]+", names_text) if name.strip()]
        return names
    return []


def _director_brief_prompt_block(director_brief: str) -> str:
    director_brief = (director_brief or "").strip()
    if not director_brief:
        return ""
    return (
        "[Director Showrunner Brief]\n"
        "This brief is the top-level creative contract. Preserve script facts, "
        "but use it to choose emphasis, shot priority, rhythm, and acceptable tradeoffs.\n"
        f"{director_brief}\n"
    )


def _script_fidelity_rules() -> str:
    return (
        "【剧本忠实度硬规则】\n"
        "1. 只能使用原剧本已经出现的人物、场景、动作、台词和信息点，禁止补写剧本外新事件。\n"
        "2. 禁止新增剧本中没有的台词、旁白、员工低语、心理活动或解释性信息；凡带引号的台词必须能在原剧本中找到。\n"
        "3. 若原剧本没有写员工说话，就不能写员工低声确认、新CEO到了、议论等补戏。\n"
        "4. 片段不足15秒时允许短于15秒，禁止为了凑时长添加新情节。\n"
    )


def _rhythm_insert_continuity_rules() -> str:
    return (
        "【节奏插入连续性规则】\n"
        "1. 画面逻辑优先于情绪细节：任何新增辅助行都必须先保证人物位置、道具归属和下一拍连续性成立。\n"
        "2. 新增辅助行不得制造道具归属或位置跳变；同一件道具不能在相邻动作中同时被两个人持有、背着、收起或取用。\n"
        "3. 如果原文刚写某人拿起、捡起、塞回、攥住、交给某道具，新增行必须顺着这个状态承接，不能暗示道具已经离开该人。\n"
        "4. 低歧义画面优先：优先写\"放到桌上、站到门口、停住动作、看向某处\"等稳定可见动作，避免\"攥进掌心、指尖摩挲、掌心收紧\"等模型容易误画的细微手部状态。\n"
        "5. 插入儿童或人群小动作时，优先写身体姿态、站位、视线或停顿；只有原文明确道具已在该人物身上时，才写道具状态。\n"
    )


def _subject_framing_rules() -> str:
    return (
        "【主体+景别硬规则】\n"
        "1. 景别只能修饰人物、明确人物组合、可见身体局部或关键道具，不能修饰场景名。\n"
        "2. 禁止写\"大堂半身中景\"\"电梯厅近景\"\"空间中景\"\"通道特写\"等场景+景别组合。\n"
        "3. 正确写法示例：商北琛半身中景、乔熙胸部以上中近景、两人双人中景、腕表局部特写。\n"
        "4. 空间只能写作环境关系，例如\"大堂纵深关系清楚\"，不能写成\"大堂中景\"。\n"
    )


def _spatial_geometry_contract_rules() -> str:
    return (
        "【空间几何合同硬规则】\n"
        "1. 每个 main_shot 必须输出空间几何字段：camera_basis、camera_scene_position、camera_looks_toward、subject_position、subject_facing、visible_landmarks。\n"
        "2. camera_basis 只能写 subject_relative 或 scene_fixed。人物静止说话可用 subject_relative；人物转身、穿过门框、进入电梯/车门/房门时必须改用 scene_fixed。\n"
        "3. camera_scene_position 写摄影机在场景里的物理位置，例如 lobby_axis_outside_elevator、elevator_interior_facing_lobby、left_employee_line、corridor_right_side，不要只写\"正前方\"。\n"
        "4. camera_looks_toward 写镜头朝向的场景方向，例如 toward_elevator_interior、toward_lobby_axis、toward_corridor_left。\n"
        "5. subject_position 写人物相对空间锚点的位置，例如 lobby_axis_before_elevator、inside_elevator_near_back、at_door_threshold、left_side_of_table。\n"
        "6. subject_facing 写人物身体朝向，例如 toward_elevator、toward_lobby、toward_other_character、back_to_lobby、left_profile_to_camera。\n"
        "7. visible_landmarks 必须写清每个锚点在画面中的前景/中景/后景/左侧/右侧/画外关系，例如 elevator_door_frame=foreground_edges、employee_lines=background_left_right_blur。\n"
        "8. 几何闭环优先于好听文案：如果 subject_facing=toward_elevator 且拍人物正面，摄影机就在电梯方向，elevator_door_frame 只能是 foreground_edges/side_edges，不能是 background。\n"
        "9. 如果 visible_landmarks 要写 elevator_door_frame=background，人物必须 facing_toward_lobby 或镜头必须拍人物背面/侧背；否则前后景矛盾。\n"


        "10. compiler 翻译时间轴时必须服从这些字段，不得为了\"保留空间锚点\"临时把不可见锚点塞进后景。\n"
        "11. 摄影机后退路径物理可行性：如果 subject_facing=toward_elevator 且 angle=正前方0度，摄影机在电梯方向；"
        "此时若运镜=同速后退，摄影机会退进电梯。必须改用 scene_fixed 侧面或背后机位，或改用 angle=左前方45度/右前方45度 让后退路径沿大堂侧面。\n"
        "12. 相邻 main_shot 视角翻转限制：同一 fragment 内相邻两个 main_shot 不得从正面(0度)直接跳到背后(180度)或反之，"
        "除非 state_delta 明确包含转身动作。如需从正面切到背面，必须插入侧面过渡机位(90度)或在 state_delta 写明人物转身。\n"
        "13. visible_landmarks 精简：每个 main_shot 的 visible_landmarks 最多列3个锚点；优先列出当前镜头任务必须看见的锚点，"
        "不要为了完整性把所有空间节点都塞进去。\n"
    )


def _camera_execution_rules() -> str:
    return (
        "【机位与运镜可执行硬规则】\n"
        "1. 内部镜头设计必须保留完整镜头语法：主体+主体景别、焦段、景深、机位高度、拍摄角度、唯一运镜、动作/表演、光源；不得因为最终要给 Seedance 就提前丢掉焦段/景深/高度/角度判断。\n"
        "2. 每个 shot 只能有一个主体焦点、一个景别基底、一个主导运镜；景别可以在子分镜内递进，但不能写成\"纵深中全景到半身中景\"这种单字段混合景别。\n"
        "3. 机位高度从仰拍、平视、俯拍、顶拍、虫眼中选择；普通关系/对白可用平视，权力压制可用仰拍，弱势/群体散开可用俯拍。最终 prompt 可把\"平视\"译成自然短句，避免机械写\"眼平高度\"。\n"
        "4. 拍摄角度从正面、左前方、右前方、左侧、右侧、背后、过肩、荷兰角、POV 中选择；POV 必须先有建立镜头说明谁在看，禁止直接跳 POV。不要每段都写数字角度。\n"
        "5. 运镜从推镜、拉镜、横移、横摇、垂直摇、升降、变焦、稳定器跟拍、手持、固定机位中选唯一主导运镜；禁止在一个 shot 内同时推近、横移、摇摄、再回主位。\n"
        "6. 运镜必须服务镜头目的：推近/切近/转特写只能服务信息逼近、情绪暴露、压迫上升、受击反应变重要、道具或局部动作成为焦点；禁止把慢推近当通用情绪模板。\n"
        "7. 反应落点优先按层级处理：主分镜负责主体关系和空间重心，子分镜负责受击、表情重音、局部动作；不要把\"同一运动里带到反应再回主位\"写成一个复杂主镜头。\n"
        "8. 禁止复合景别/复合机位：不要写\"纵深中全景到半身中景\"\"中景转电梯口关系景\"\"右后方中景转固定机位\"\"同轴线偏右侧\"\"前后景关系\"。改成结构化字段：shot_size=MS/MCU，angle=正面/斜侧面/背面，movement=固定/跟拍。\n"
        "9. 禁止使用模糊机位词：三分之四角度、斜侧、斜前方、轻微前推、轻微前推跟随、缓慢靠近、背影轻压。\n"
        "10. 禁止抽象判断句。不要写\"沉默就是回应\"\"权力关系锁住\"\"空气收紧\"\"命令落地即见效\"\"形成清晰钩子\"。必须改写成可见动作：停顿几秒、谁看向谁、谁后退半步、谁让出通道、电梯门停在什么开合状态。\n"
        "11. 内部可以技术化，最终编译必须感知化：85mm浅景深可译为\"背景虚化、主体突出\"，深景深可译为\"前后景都清楚\"，不得把\"电影感/高级感\"写成空壳标签。\n"
    )


def _camera_task_selection_rules() -> str:
    return (
        "【镜头任务到机位选择硬规则】\n"
        "1. 先判断当前 main_shot 的 coverage_role 与 shot_intent，再决定 shot_size、camera_height、angle、movement、lens、depth；不要先挑一个好看的机位再硬套剧情。\n"
        "2. 主分镜只在主体关系变化、场面权力关系变化、叙事重心变化、空间观察点变化、当前主镜头无法承载下一动作单元时新开；不要用主分镜机械对应每句台词。\n"
        "3. 完整发言单元优先保持在同一主分镜内；长挑衅/揭晓/质问台词超过2秒时，用子分镜/L-cut 切受击者，让后半句以画外音落在反应上。\n"
        "4. 听者受击、视线撞上、回神、表情冻结：优先挂到现有主镜头或新增 sub_shot；受击者机位必须落在同侧轴线内，并写 companion_visibility，不要靠横移摆尾带到反应。\n"
        "5. 动作路径、身体位移、擦身而过、碰撞、扶住、松手：优先左侧、右侧、左后方、右后方或 scene_fixed；目标是看清起点、路径、接触点和终点。同段切换只能发生在选定一侧内部，避免单一主机位持续承担整段。\n"
        "6. 目标方向、走向门口、冲向门缝、进入电梯、穿过门框、离开画面：优先背后、左后方、右后方或 scene_fixed；目标是看清人物前方目标与阈值关系。\n"
        "7. 9:16 主力景别为半身景/中景/MS，MCU 只用于压迫段或信息逼近中间层，CU 只用于信息炸点/受击反应/情绪顶点；禁止长期只在 MCU 与 CU 之间摆动。\n"
        "8. 群体调度必须保留空间容量：群体四散、主管退让、员工让路不能用面部特写承接，优先中景关系、半身关系或 scene_fixed。\n"
        "9. 每个 main_shot 必须有 cut_reason，回答为什么从上一主镜头切到这里；有效理由包括台词落点后切听者反应、动作中间态切接续、需要回关系景确认距离/门状态、tailframe_reset。\n"
        "10. sub_shot 必须有 parent_shot_id、trigger、shot_size、cut_point、companion_visibility、state_delta、beat_purpose、emotion_anchor、duration_hint、action_phase；每个片段最多2个子分镜。\n"
        "11. 如果一个 fragment 里有多个 main_shots，禁止所有 shot 都重复同一套 shot_size + angle + movement；但变化必须有叙事动机，禁止假丰富感。"
    )


def _space_rules_contract_rules() -> str:
    return (
        "[Scene Map Contract]\n"
        "1. Every fragment must include space_rules before shots. This is the floor-plan contract for layout, blocking, guard, and compiler.\n"
        "2. space_rules.space_anchors must name the stable set pieces / thresholds / landmarks and their relative directions, such as door=north, table=center, window=east.\n"
        "3. space_rules.character_positions must describe each active character's start position, end position when known, and body facing relative to the anchors.\n"
        "4. space_rules.action_axis must define the main eyeline/action axis and which side is the safe camera side.\n"
        "5. space_rules.safe_camera_zones must list physically valid camera zones that preserve the axis and keep required bodies/landmarks visible.\n"
        "6. space_rules.blocked_camera_zones must list forbidden or risky zones, such as axis-crossing seats, occluded corners, impossible doorway positions, or positions that hide the body path.\n"
        "7. main_shot.camera_scene_position and visible_landmarks must be compatible with space_rules. If a shot uses scene_fixed, it must come from a safe_camera_zones entry or explain the exception in selection_reason.\n"
    )


def _best_shot_selection_rules() -> str:
    return (
        "[Best Shot Selection Contract]\n"
        "1. Do not choose a shot only because it matches a rule category. First decide the viewer's attention job.\n"
        "2. Every main_shot must include attention_target: who or what the viewer must watch at this exact moment.\n"
        "3. Every main_shot must include information_strategy: what the shot reveals, delays, hides, or lets the viewer miss.\n"
        "4. Every main_shot must include selection_reason: why this specific shot size / angle / camera seat is the strongest choice now.\n"
        "5. Every main_shot must include rejected_alternatives: at least one tempting but weaker option and why it was rejected.\n"
        "6. selection_reason cannot be generic words such as cinematic, looks good, follows rules, or more emotional. Tie it to attention, information, space, body action, or cut continuity.\n"
        "7. If the shot is a reaction, explain why the viewer needs the receiver now instead of the speaker; if it is an action path, explain why the body path must stay readable; if it is a relation reset, explain what spatial confusion it repairs.\n"
    )


def _has_body_mechanics_action(block: str) -> bool:
    """Return True if the shot block describes a body-contact or movement-path action."""
    return bool(_BODY_MECHANICS_ACTION_RE.search(block or ""))


def _shot_composition_task_selection_rules() -> str:
    return (
        "【镜头任务到景别/镜头类型选择硬规则】\n"
        "1. 先判断 shot 的叙事任务，再决定 shot_size 与 main_shot/sub_shot 归属；不要先随手选 CU/MCU/MS，再把任务硬塞进去。\n"
        "2. 建立空间、人物关系、尾帧交接：优先 全景/中景/半身中景/双人关系景；这些必须是 main_shot，不能用脸部特写或手部局部承担。\n"
        "3. 发言承载、正面施压、冷处理对峙：鼓励使用极端景别！情绪爆发、挑衅、冷笑或压抑点，大胆使用特写（CU）或极特写（ECU）；展现权势碾压或孤独感时，大胆使用大远景（Wide Shot）。拒绝平庸的电视感中景。\n"
        "4. 听者受击、回神、视线撞上、表情冻结：优先 中近景或胸部以上近景；只允许在真正情绪极点使用一次特写，且必须保留前景肩线、门框、桌边或人物边缘作为空间锚点。\n"
        "5. 身体位移、擦身而过、碰撞、扶住、松手、转身、穿门、进电梯/车门/房门：优先 中景、半身关系景、双人中景或全身关系景；禁止用 CU/ECU/手部局部主镜头承担动作路径。\n"
        "6. 手部、道具、门缝、照片、手机、衣角等细节只能作为短 sub_shot 或 action_insert_slot；必须挂 parent_shot_id，不能升级成 main_shot，除非该物件本身就是当前剧本事件的唯一主体。\n"
        "7. sub_shot 只负责重音，不负责重新建场；duration_hint 要短，action_phase 必须说明 pre_action、mid_action、impact、reaction 或 reset。\n"
        "8. 一个 fragment 的有效镜头应有景别层次：关系景/中景负责空间和动作，中近景负责对白和反应，特写只负责一次重点；禁止连续用特写推进整段。\n"
        "9. 最后一个 main_shot 若承担 tailframe_reset，必须回到可继承的关系景、中景或明确空间状态；不能停在脸部特写、眼神、手部或道具局部。\n"
        "10. 9:16 竖屏审美纪律：减少废话一样的多人宽幅全景（竖屏塞不下），多使用切边构图、前景遮挡构图和极特写来构建电影级的视觉压迫感。\n"
    )


def _dialogue_coverage_contract_rules() -> str:
    return (
        "【对白覆盖与反应切镜硬规则】\n"
        "1. 完整发言单元必须保持语义连续，但不能理解为单镜头吃完整段台词；画面可以且应该在同一发言单元内部切到对手反应、过肩、反打或不同景别。\n"
        "2. 任何长台词、命令、质问、揭晓、挑衅或高压对白，至少需要\"说话者起句 -> 对手/听者反应或反打 -> 必要时切回说话者/关系景\"的覆盖方案。\n"
        "3. 高级剪辑思维（告别乒乓球剪辑）：高冲击台词必须强制使用画外音（OS / J-cut / L-cut）。例如 A 放狠话时，镜头不要拍 A，而是直接切给 B 微妙颤抖的下颌线或紧握的拳头，A 的声音作为画外音处理。\n"
        "4. 视线引导（Eyeline Match）：layout 和 blocking 阶段在切镜前，必须写清上一个镜头角色的视线看向哪里，下一个镜头的机位必须从该视线方向自然承接，严禁无视线的盲切。\n"
        "5. compiler 只忠实翻译上游 dialogue_coverage、reaction_coverage、sub_shots 和 cut_point，不得把它们压扁成一个固定机位里的人物连续说完。\n"
        "6. 对白切镜服务信息增量，不是机械按秒切；如果台词短且没有受击/信息落点，可以同一机位继续，但长句和高压句必须有视觉变化。\n"
        "7. 人物说长压迫对白时，严禁一个镜头、一个景别、一个机位说完整句或完整问答；必须在对白内部写出明确切镜点，例如\"他说出前半句 -> 镜头切至同侧听者中近景/过肩 -> 后半句以画外音/L-cut 落在听者反应上 -> 必要时切回说话者\"。\n"
        "8. 如果一个时间段包含两句以上往返对白，不能写成同一双人中景连续说完；必须拆出说话者起句、同侧听者反应、关系景复位，至少一次改变主体、景别或机位。\n"
    )


def _shot_director_source_event_rules() -> str:
    return (
        "【shot_director 剧本继承硬规则】\n"
        "1. shot_director 只能把 story_planner 的 source_script_events 翻译成镜头、景别和受击落点；不得重新解释剧本、不得新增睡醒、床边、伴侣、保镖、记者、闪光灯、鞠躬等剧本外前提。\n"
        "2. 场次标题、人物行、source_script_events 的可见事实优先级高于英文台词里的词义联想；例如 OS 里出现 \"wake up\" 只表示乔熙自我提醒，不能改拍成乔熙睡觉、睁眼或被伴侣叫醒。\n"
        "3. 场景空间必须继承场次标题和 source_script_events；公寓不能改成车内，门口不能改成大堂，集团门口不能改成办公室。\n"
        "4. subject 只能来自当前片段的人物行、source_script_events 中的可见人物/群体/道具/车辆；不能把 OS 里的昵称或英文名当成画面主体替换角色名。\n"
        "5. 必须继承上游的道具状态和空间状态：照片在桌上就保持在桌上，书包在小豆丁身上就保持在小豆丁身上，不得为了情绪镜头改写为攥在手里或塞回书包。\n"
        "6. 低歧义画面优先：优先使用站位、视线、停顿、桌面、门口、车辆到达、下车等稳定可见动作；避免把简单动作改成掌心、指尖、指节、发丝等微观细节。\n"
        "7. 先判断当前片段的节奏任务，再匹配镜头语言；必须先回答这是权力反转、冲突升级、悬念揭示、误解错位、情绪极点还是钩子结尾，再决定要不要切镜、切几镜，不能先拿模板再套剧情。\n"
        "8. 9:16 竖屏默认以半身、中景、双人关系景别承担叙事；特写只给炸点、受击、情绪峰值或关键信息插入。一个片段的面部特写最多一次，不得把特写当默认景别。\n"
        "9. 没必要每个细节动作都给镜头：如果主镜头已经能看清动作和关系，就不要再为手指、掌心、鞋尖、袖口、嘴唇、眼角等微细节单独开镜头；只有线索揭示、动作前摇或受击落点无法看清时才允许插入。\n"
        "10. 悬念揭示优先采用\"停顿/发现前逼近 -> 关键物或文字 -> 人物反应\"；冲突升级优先采用\"施压 -> 受击 -> 短暂停顿\"；误解错位优先提升听者反应镜头，而不是让说话者一直占满画面。\n"
        "11. shot_director 不得重新判断整体节奏，必须服从 atmosphere_strategy / rhythm supervisor 给出的快慢、停顿、卡断、反应归属、尾帧承接。\n"
        "12. 若节奏建议与剧本事实、台词原文、动作道具连续性、人物位置、空间轴线安全冲突，后者优先。\n"
    )


def _shot_director_rhythm_match_rules() -> str:
    return (
        "【节奏与镜头匹配规则（参考《AI 导演系统工程文档规范》）】\n"
        "0. shot_director 只执行 story_planner 与 rhythm supervisor 给出的片段节奏指令，不得重新判断整体节奏；必须服从 atmosphere_strategy 的快慢、停顿、卡断、反应归属、尾帧承接。\n"
        "1. 先识别戏剧微粒，再决定镜头：权力反转看压制与失势，冲突升级看施压与受击，悬念揭示看发现与停顿，误解错位看听者反应，情绪极点看停住后的内压，钩子结尾看最后的悬住点。\n"
        "2. 镜头数量由节奏任务决定，不由镜头库模板决定；能用 1 个主镜头讲清的动作，不要硬拆成 3 个细碎镜头。\n"
        "3. 需要切镜时，只切信息增量最大的节点：动作前摇、揭示落点、受击反应、关系变化、关键道具或文字出现。走近、弯腰、拿起、站定等中间过渡默认省略。\n"
        "4. 权力反转优先用站位高低、画面占比、稳定推进和反应落点表达，不靠堆叠特写表达压迫。\n"
        "5. 冲突升级优先 2-3 秒短镜，保留施压、受击和停顿，切掉无信息量动作过程。\n"
        "6. 悬念揭示里的关键物、文件、屏幕、照片要稳拍可读；不要为了好看加花哨运动，文字类信息优先静态或极轻微推进。\n"
        "7. 情绪极点允许更稳、更长一点，但仍应以简单背景、少动作、少机位运动为前提；9:16 下优先稳住半身或中景，再考虑是否真的需要更近景别。\n"
        "8. 9:16 竖屏下，半身/中景/双人关系镜头是主力，特写是强调而不是默认。若一个片段出现多次面部特写，必须有明确的炸点、受击或揭示理由，否则视为过度设计。\n"
        "9. 微细节镜头只用于关键信息，不用于堆砌存在感。手、嘴唇、眼角、袖口、鞋尖、发丝等局部如果不承载线索、动作前摇或受击结果，就不要单独给镜头。\n"
    )


def _clean_shot_director_output(text: str) -> str:
    """Strip thinking/prose wrappers and keep the YAML payload."""
    if not text:
        return ""
    cleaned = re.sub(r"(?is)<thinking>.*?</thinking>", "", text).strip()
    fence_match = re.search(r"(?is)```(?:yaml|yml)?\s*(.*?)```", cleaned)
    if fence_match:
        cleaned = fence_match.group(1).strip()
    lines = cleaned.splitlines()
    while lines and not re.match(_fragment_line_pattern(), lines[0].strip(), re.IGNORECASE):
        lines.pop(0)
    return "\n".join(lines).strip()


def _is_closeup_shot_size(value: str) -> bool:
    normalized = (value or "").strip().lower()
    if not normalized:
        return False

    # Do not classify medium-close vocabulary as close-up just because it
    # contains the substring "cu" (for example, "MCU").
    medium_close_tokens = [
        "mcu",
        "medium close",
        "medium-close",
        "medium_close",
        "medium close-up",
        "medium-close-up",
        "medium_close_up",
        "中近景",
        "胸部以上",
    ]
    if any(token in normalized for token in medium_close_tokens):
        return False

    if re.search(r"\b(?:ecu|cu)\b", normalized):
        return True
    if re.search(r"\b(?:extreme[-_ ]?)?close[-_ ]?up\b", normalized):
        return True
    return bool(re.search(r"极特写|大特写|脸部特写|手部特写|眼部特写|特写镜头|^特写$", normalized))


def _fragment_line_pattern() -> str:
    return r"^-?\s*(?:fragment_id|片段编号)\s*:\s*[\"']?F[\w-]+[\"']?"


_YAML_FIELD_ALIASES: dict[str, tuple[str, ...]] = {
    "fragment_id": ("fragment_id", "片段编号"),
    "fragment_task": ("fragment_task", "片段任务"),
    "rhythm": ("rhythm", "节奏"),
    "shots": ("shots", "镜头列表"),
    "shot_id": ("shot_id", "镜头编号"),
    "duration": ("duration", "时长"),
    "task": ("task", "镜头任务"),
    "subject": ("subject", "拍摄主体"),
    "shot": ("shot", "镜头"),
    "camera": ("camera", "机位"),
    "size": ("size", "景别"),
    "action": ("action", "画面动作"),
    "dialogue": ("dialogue", "台词"),
    "must_carry": ("must_carry", "必须承载"),
    "cut_point": ("cut_point", "切镜点"),
    "continuity": ("continuity", "连续性"),
    "type": ("type", "类型"),
    "audio": ("audio", "声音"),
}


def _yaml_field_names(field: str) -> tuple[str, ...]:
    return _YAML_FIELD_ALIASES.get(field, (field,))


def _yaml_field_pattern(field: str) -> str:
    return "|".join(re.escape(name) for name in _yaml_field_names(field))


def _has_yaml_field(block: str, field: str) -> bool:
    return bool(re.search(rf"(?m)^\s*-?\s*(?:{_yaml_field_pattern(field)})\s*:", block or ""))


def _extract_yaml_sections(yaml_text: str) -> list[str]:
    sections: list[str] = []
    current: list[str] = []
    for line in yaml_text.splitlines():
        stripped = line.strip()
        if stripped.startswith("```"):
            continue
        if re.match(_fragment_line_pattern(), stripped, re.IGNORECASE):
            if current:
                sections.append("\n".join(current))
            current = [line]
            continue
        if current:
            current.append(line)
    if current:
        sections.append("\n".join(current))
    return sections


def _extract_fragment_id(section: str) -> str:
    match = re.search(r"(?m)^\s*-?\s*(?:fragment_id|片段编号)\s*:\s*[\"']?([^\"'\s#]+)[\"']?", section)
    return match.group(1).strip() if match else ""


def _field_value(section: str, field: str) -> str:
    match = re.search(rf"(?m)^\s*-?\s*{re.escape(field)}\s*:\s*[\"']?(.+?)[\"']?\s*$", section)
    return match.group(1).strip() if match else ""


def _source_script_events(section: str) -> list[str]:
    block_match = re.search(
        r"(?m)^\s*source_script_events\s*:\s*([\s\S]*?)(?=\n\s*[a-z_]+\s*:|\n\s*-?\s*fragment_id\s*:|\Z)",
        section,
    )
    block = block_match.group(1) if block_match else ""
    return [
        item.strip().strip("\"'")
        for item in re.findall(r"(?m)^\s*-\s*[\"']?(.+?)[\"']?\s*$", block)
        if item.strip()
    ]


def _truncate_for_prompt(text: str, limit: int = 12000) -> str:
    text = text or ""
    if len(text) <= limit:
        return text
    return text[:limit] + "\n\n...[已截断，仅保留前文供修复参考]..."


def _runtime_context_contract_card() -> str:
    return (
        "[Runtime Context Contract]\n"
        "- story_planner 保留原始剧本作为逐字引用来源；其他阶段不要重新理解全剧本。\n"
        "- layout 只负责 shots 机位骨架，不承担剧本理解、情绪设计、动作调度或身份锁定。\n"
        "- blocking/guard/prompt_compiler 只使用当前片段资产和当前镜头资产，避免被其他片段带偏。\n"
        "- 参考图只负责身份/空间锚定；人物形象细节不需要在最终 prompt 中重复展开。\n"
        "- 如果人物面朝电梯且镜头写正面，电梯门框只能是前景边缘/左右侧边缘，不能写成后景。"
    )


def _validate_shot_director_output(director_output: str, expected_segments: list[str]) -> list[str]:
    """Simplified validation for lean shot director schema.

    Required fields per fragment: shots
    Required fields per shot: shot_id, subject, camera, size, action, intent
    Optional fields per shot: dialogue, type
    """
    issues: list[str] = []
    for segment_name in expected_segments:
        segment_num = re.sub(r"\D", "", segment_name)
        fragment_id = f"F{int(segment_num):02d}" if segment_num else segment_name
        block_match = re.search(
            rf"(?m)(^\s*-?\s*(?:fragment_id|片段编号)\s*:\s*[\"']?{re.escape(fragment_id)}[\"']?[\s\S]*?)"
            rf"(?=\n\s*-?\s*(?:fragment_id|片段编号)\s*:\s*[\"']?F\d+|\Z)",
            director_output,
        )
        if not block_match:
            issues.append(f"shot_director 缺少 {fragment_id} 的镜头设计。")
            continue
        block = block_match.group(1)

        # Check for required top-level field: shots
        if not _has_yaml_field(block, "shots"):
            issues.append(f"{fragment_id} 缺少 shots 字段。")
            continue

        # Check each shot for required fields
        for field in ["shot_id", "subject", "camera", "size", "action", "intent"]:
            if not _has_yaml_field(block, field):
                issues.append(f"{fragment_id} 的 shots 缺少字段 {field}。")

    return issues


_MAIN_SHOT_BLOCK_RE = re.compile(
    r"(?ms)^\s*-\s*(?:shot_id|镜头编号)\s*:\s*[\"']?([^\"'\n#]+?)[\"']?\s*$"
    r"([\s\S]*?)(?=^\s*-\s*(?:shot_id|镜头编号)\s*:|^\s*(?:sub_shots|子镜头|子镜头列表)\s*:|^\s*-\s*(?:fragment_id|片段编号)\s*:|\Z)"
)


def _fragment_id_for_segment_index(segment_names: Any, segment_index: int) -> str:
    try:
        index = int(segment_index)
    except Exception:
        index = 1
    if index < 1:
        index = 1
    if isinstance(segment_names, (list, tuple)) and 0 <= index - 1 < len(segment_names):
        fragment_id = str(segment_names[index - 1] or "").strip().strip("\"'")
        if fragment_id and re.match(r"^F[\w-]+$", fragment_id):
            return fragment_id
    return f"F{index:02d}"


def _segment_block_by_fragment_id(text: str, fragment_id: str) -> str:
    fragment_id = (fragment_id or "").strip().strip("\"'")
    if not fragment_id:
        return ""
    match = re.search(
        rf"(?m)(^\s*-?\s*(?:fragment_id|片段编号)\s*:\s*[\"']?{re.escape(fragment_id)}[\"']?[\s\S]*?)"
        rf"(?=\n\s*-?\s*(?:fragment_id|片段编号)\s*:\s*[\"']?F[\w-]+[\"']?|\Z)",
        text or "",
    )
    return match.group(1).strip() if match else ""


def _yaml_scalar_field(block: str, field: str) -> str:
    match = re.search(rf"(?m)^\s*-?\s*(?:{_yaml_field_pattern(field)})\s*:\s*[\"']?([^\"'\n#]+)", block or "")
    return match.group(1).strip() if match else ""


def _yaml_line_field(block: str, field: str) -> str:
    match = re.search(rf"(?m)^\s*-?\s*(?:{_yaml_field_pattern(field)})\s*:\s*(.+?)\s*$", block or "")
    if not match:
        return ""
    return match.group(1).strip().strip("\"'")


def _dialogue_listener_for_subject(subject: str, script: str) -> str:
    names = _primary_script_character_names(script)
    if len(names) < 2:
        return "听者"
    subject_text = subject or ""
    if names[0] in subject_text:
        return names[1]
    if names[1] in subject_text:
        return names[0]
    if re.search(r"商北琛|Nash|Mr\.?\s*Pierce", subject_text, re.IGNORECASE):
        return names[0]
    if re.search(r"乔熙|Sunny", subject_text, re.IGNORECASE):
        return names[1]
    return names[0]


def _repair_shot_director_main_shot_contract_block(block: str, script: str) -> str:
    names = _primary_script_character_names(script)
    if len(names) >= 2:
        subject = _yaml_line_field(block, "subject")
        if re.search(r"\bSunny\b", subject) and names[0] != "Sunny":
            block = _replace_yaml_scalar_field(block, "subject", re.sub(r"\bSunny\b", names[0], subject))
        subject = _yaml_line_field(block, "subject")
        if re.search(r"\b(?:Nash|Mr\.?\s*Pierce)\b", subject) and names[1] not in {"Nash", "Mr. Pierce"}:
            block = _replace_yaml_scalar_field(
                block,
                "subject",
                re.sub(r"\b(?:Nash|Mr\.?\s*Pierce)\b", names[1], subject),
            )

    coverage = _yaml_line_field(block, "dialogue_coverage")
    if _dialogue_coverage_needs_visual_break(coverage) and not _has_dialogue_coverage_visual_break(coverage):
        listener = _dialogue_listener_for_subject(_yaml_line_field(block, "subject"), script)
        repaired = (
            f"{coverage}；切{listener}中近景听者反应/反打，保留对手肩线或桌边作为空间锚点；"
            f"后半句以画外音/OS/L-cut落在{listener}反应上，必要时切回说话者。"
        )
        block = _replace_yaml_scalar_field(block, "dialogue_coverage", repaired)
    return block


def _repair_shot_director_contract_output(output: str, script: str) -> str:
    if not output:
        return output

    def repl(match: re.Match[str]) -> str:
        return _repair_shot_director_main_shot_contract_block(match.group(0), script)

    return _MAIN_SHOT_BLOCK_RE.sub(repl, output)


def _repair_body_mechanics_contract_output(output: str) -> str:
    if not output:
        return output

    def repl(match: re.Match[str]) -> str:
        block = match.group(0)
        if not _has_body_mechanics_action(block):
            return block

        indent_match = re.search(
            r"(?m)^(\s*)(?:state_delta|tailframe_role|shot_intent|dialogue_coverage|selection_reason)\s*:",
            block,
        )
        indent = indent_match.group(1) if indent_match else "      "
        child_indent = indent + "  "
        defaults = {
            "接触点位": "除非原剧本动作明确写出接触，否则不新增身体接触",
            "重心变化": "保持轻微变化；人物延续当前站位",
            "移动路径": "从起始位置出发，经过可见动作路径，停在已建立的位置",
            "身体朝向": "延续已建立的视线方向和空间轴线",
            "可拍性": "可拍；所选镜头能看清动作路径",
            "机位要求": "保持中景或中近景足够宽，能读清身体动作路径",
            "连续性风险": "保留尾帧人物位置和相邻人物关系，供下一镜继承",
        }
        if not re.search(r"(?m)^\s*(?:身体动作检查|body_mechanics_check)\s*:", block):
            body_lines = ["身体动作检查:"] + [
                f"{field}: {value}" for field, value in defaults.items()
            ]
            return block.rstrip() + "\n" + "\n".join(
                (indent if index == 0 else child_indent) + line
                for index, line in enumerate(body_lines)
            ) + "\n"

        additions = [
            f"{child_indent}{field}: {value}"
            for field, value in defaults.items()
            if not re.search(rf"(?m)^\s*{re.escape(field)}\s*:", block)
        ]
        if additions:
            block = block.rstrip() + "\n" + "\n".join(additions) + "\n"
        return block

    return _MAIN_SHOT_BLOCK_RE.sub(repl, output)


def _repair_shot_director_output_contracts(output: str, script: str) -> str:
    """Apply narrow deterministic repairs before asking another LLM to rewrite."""
    repaired = _repair_shot_layout_output(output)
    repaired = _repair_shot_director_contract_output(repaired, script)
    repaired = _repair_body_mechanics_contract_output(repaired)
    return repaired


def _has_elevator_facing(value: str) -> bool:
    return bool(re.search(r"电梯|elevator", value or "", re.IGNORECASE))


def _has_front_angle(value: str) -> bool:
    return bool(re.search(r"正面|正前方|front|frontal|0度", value or "", re.IGNORECASE))


def _has_background_elevator_anchor(value: str) -> bool:
    return bool(
        re.search(r"(?:后景|背景|background)[^,\n;；。]{0,30}(?:电梯|elevator)", value or "", re.IGNORECASE)
        or re.search(r"(?:电梯|elevator)[^,\n;；。]{0,40}(?:后景|背景|background)", value or "", re.IGNORECASE)
    )


_ACTION_PATH_TASK_RE = re.compile(
    r"进入|走进|冲入|冲向|穿过|越过|进电梯|进门|出门|碰撞|撞上|扶住|松开|擦身而过|过阈值|转身|离开|"
    r"enter(?:ing)?|cross(?:ing)?|rush(?:ing)?|collision|grab|release|threshold|turn(?:ing)?|exit(?:ing)?",
    re.IGNORECASE,
)


def _repair_background_elevator_anchor_text(text: str) -> str:
    parts = re.split(r"([,;；，])", text)
    repaired: list[str] = []
    for part in parts:
        if re.search(r"电梯|elevator", part, re.IGNORECASE) and re.search(
            r"后景|背景|background", part, re.IGNORECASE
        ):
            part = re.sub(r"background(?:_[A-Za-z0-9_-]+)?", "foreground_edges_or_side_edges", part, flags=re.IGNORECASE)
            part = re.sub(r"后景|背景", "前景边缘或侧边缘", part)
        repaired.append(part)
    return "".join(repaired)


def _repair_background_elevator_landmarks(block: str) -> str:
    lines = block.splitlines(keepends=True)
    in_landmarks = False
    landmark_indent = 0
    repaired_lines: list[str] = []
    for line in lines:
        stripped = line.lstrip()
        indent = len(line) - len(stripped)
        if re.match(r"visible_landmarks\s*:", stripped):
            in_landmarks = True
            landmark_indent = indent
            repaired_lines.append(_repair_background_elevator_anchor_text(line))
            continue
        if in_landmarks and stripped and indent <= landmark_indent and re.match(r"[A-Za-z_][\w-]*\s*:", stripped):
            in_landmarks = False
        if in_landmarks:
            repaired_lines.append(_repair_background_elevator_anchor_text(line))
        else:
            repaired_lines.append(line)
    return "".join(repaired_lines)


def _replace_yaml_scalar_field(block: str, field: str, value: str) -> str:
    pattern = re.compile(rf"(?m)^(\s*{re.escape(field)}\s*:\s*)([^\n#]*)(.*)$")

    def repl(match: re.Match[str]) -> str:
        return f"{match.group(1)}{value}{match.group(3)}"

    return pattern.sub(repl, block, count=1)


_SELECTION_REASON_ANCHOR_RE = re.compile(
    r"viewer|audience|attention|information|reveal|delay|hide|miss|space|body|action|path|cut|continuity|"
    r"观众|注意力|信息|揭示|延迟|隐藏|错过|空间|身体|动作|路径|切镜|连续|视线|关系|轴线|受击|反应",
    re.IGNORECASE,
)


_GENERIC_SELECTION_REASON_RE = re.compile(
    r"cinematic|looks good|more emotional|follow(?:s|ing)? rules|rule match|好看|高级|有电影感|符合规则|更有情绪",
    re.IGNORECASE,
)


def _layout_selection_reason_needs_repair(reason: str) -> bool:
    reason = (reason or "").strip()
    if len(reason) < 12:
        return True
    if _GENERIC_SELECTION_REASON_RE.search(reason):
        return True
    return not _SELECTION_REASON_ANCHOR_RE.search(reason)


def _layout_selection_reason_from_fields(block: str) -> str:
    def clean(value: str, fallback: str) -> str:
        text = re.sub(r"\s+", " ", (value or "").strip())
        text = text.replace(":", " -").strip(" -")
        return text or fallback

    attention = clean(_yaml_scalar_field(block, "attention_target"), clean(_yaml_scalar_field(block, "subject"), "current subject"))
    information = clean(
        _yaml_scalar_field(block, "information_strategy"),
        clean(_yaml_scalar_field(block, "shot_intent"), "current story information"),
    )
    coverage = clean(_yaml_scalar_field(block, "coverage_role"), "coverage beat")
    cut_reason = clean(_yaml_scalar_field(block, "cut_reason"), "this cut point")
    camera_seat = clean(
        _yaml_scalar_field(block, "camera_scene_position"),
        clean(_yaml_scalar_field(block, "angle"), "this camera seat"),
    )
    return (
        f"viewer attention stays on {attention}; information strategy is {information}; "
        f"the {camera_seat} choice supports {coverage} at {cut_reason} while preserving space/action/cut continuity"
    )


def _insert_yaml_scalar_after(block: str, after_fields: tuple[str, ...], field: str, value: str) -> str:
    if re.search(rf"(?m)^\s*{re.escape(field)}\s*:", block):
        return _replace_yaml_scalar_field(block, field, value)
    for after_field in after_fields:
        match = re.search(rf"(?m)^(\s*){re.escape(after_field)}\s*:.*$", block)
        if match:
            indent = match.group(1)
            return block[: match.end()] + f"\n{indent}{field}: {value}" + block[match.end():]
    indent_match = re.search(r"(?m)^(\s*)(?:shot_intent|tailframe_role|companion_visibility|coverage_role|depth|lens)\s*:", block)
    indent = indent_match.group(1) if indent_match else "      "
    return block.rstrip() + f"\n{indent}{field}: {value}\n"


def _repair_action_path_closeup_shot_size(block: str) -> str:
    shot_size = _yaml_scalar_field(block, "shot_size")
    if not _is_closeup_shot_size(shot_size):
        return block

    joined = " ".join(
        [
            _yaml_scalar_field(block, "subject"),
            _yaml_scalar_field(block, "coverage_role"),
            _yaml_scalar_field(block, "cut_reason"),
            _yaml_scalar_field(block, "shot_intent"),
            block,
        ]
    )
    if not _ACTION_PATH_TASK_RE.search(joined):
        return block

    relation_hint = " ".join(
        [
            _yaml_scalar_field(block, "coverage_role"),
            _yaml_scalar_field(block, "shot_intent"),
            _yaml_scalar_field(block, "companion_visibility"),
            _yaml_scalar_field(block, "visible_landmarks"),
        ]
    )
    repaired_size = "半身关系景" if re.search(r"双人|关系|肩线|two[_ -]?shot|shoulder", relation_hint, re.IGNORECASE) else "中景"
    return _replace_yaml_scalar_field(block, "shot_size", repaired_size)


def _repair_layout_main_shot_block(match: re.Match[str]) -> str:
    block = match.group(0)
    angle = _yaml_scalar_field(block, "angle")
    subject_facing = _yaml_scalar_field(block, "subject_facing")
    visible_landmarks = _yaml_scalar_field(block, "visible_landmarks")
    block = _repair_action_path_closeup_shot_size(block)
    if (
        _has_elevator_facing(subject_facing)
        and _has_front_angle(angle)
        and _has_background_elevator_anchor(visible_landmarks)
    ):
        block = _repair_background_elevator_landmarks(block)

    if not re.search(r"(?m)^\s*dialogue_coverage\s*:", block):
        indent_match = re.search(r"(?m)^(\s*)(?:shot_intent|tailframe_role|companion_visibility|coverage_role|depth|lens)\s*:", block)
        indent = indent_match.group(1) if indent_match else "      "
        block = block.rstrip() + f"\n{indent}dialogue_coverage: none\n"
    selection_reason = _yaml_scalar_field(block, "selection_reason")
    if _layout_selection_reason_needs_repair(selection_reason):
        block = _insert_yaml_scalar_after(
            block,
            ("information_strategy", "attention_target", "shot_intent"),
            "selection_reason",
            _layout_selection_reason_from_fields(block),
        )
    return block


def _repair_shot_layout_output(layout_output: str) -> str:
    """Apply deterministic minimal repairs before failing a layout contract."""
    if not layout_output:
        return layout_output
    return _MAIN_SHOT_BLOCK_RE.sub(_repair_layout_main_shot_block, layout_output)


_DIALOGUE_COVERAGE_TERMS_RE = re.compile(
    r"("
    r"\u5bf9\u767d|\u53f0\u8bcd|\u8bdd\u97f3|\u8bed\u6c14|\u58f0\u7ebf|\u8bf4\u8bdd\u8005|\u53d1\u8bdd\u8005|\u542c\u8005|\u5bf9\u624b|\u5bf9\u65b9|"
    r"\u56de\u5e94|\u56de\u8bdd|\u63a5\u8bdd|\u63d2\u8bdd|\u6253\u65ad|\u505c\u987f|\u6c89\u9ed8|\u8fdf\u7591|\u54bd\u4f4f|\u54fd\u4f4f|\u6123\u4f4f|\u50f5\u4f4f|"
    r"\u53cd\u5e94|\u53d7\u51fb|\u89c6\u7ebf|\u773c\u795e|\u770b\u7740|\u770b\u5411|\u907f\u5f00|\u5bf9\u89c6|\u773c\u7736|\u6469\u6332|"
    r"\u8fc7\u80a9|\u80a9\u7ebf|\u53cd\u6253|\u5207\u56de|\u5207\u81f3|\u5207\u51fa|\u5207\u5165|\u63a5\u5207|\u538b\u5230|\u5e26\u5230|"
    r"\u53f0\u8bcd\u65ad\u70b9|\u53e5\u5c3e|\u53e5\u4e2d|\u8bdd\u5934|\u753b\u5916\u97f3|\u65c1\u767d|\u97f3\u6548|"
    r"\bOS\b|O\.S\.|\bVO\b|V\.O\.|L-cut|J-cut|"
    r"\bdialogue\b|\bline\b|\blines\b|\bspeaker\b|\blistener\b|\breply\b|\brespond\b|\breaction\b|"
    r"\bpause\b|\bbeat\b|\binterrupt\b|\boverlap\b|\boffscreen\b|\boff-screen\b|\bvoiceover\b|\bvoice-over\b"
    r")",
    re.IGNORECASE,
)


def _quoted_dialogues(text: str) -> list[str]:
    return [item.strip() for item in re.findall(r"[\"\"]([^\"\"]+)[\"\"]", text or "") if item.strip()]


def _dialogue_payload_is_long(dialogues: list[str]) -> bool:
    if not dialogues:
        return False
    total = sum(len(item) for item in dialogues)
    return total >= 42 or any(len(item) >= 32 for item in dialogues) or len(dialogues) >= 2


def _dialogue_coverage_needs_visual_break(coverage: str) -> bool:
    text = (coverage or "").strip()
    if not text or text.lower() == "none":
        return False
    quoted = _quoted_dialogues(text)
    if _dialogue_payload_is_long(quoted):
        return True
    ascii_words = re.findall(r"[A-Za-z][A-Za-z']+", text)
    has_long_english = sum(len(word) for word in ascii_words) >= 42 or len(ascii_words) >= 8
    has_multi_line_or_exchange = len(re.findall(r"[/?？]|；|;|：|:", text)) >= 2
    has_pressure_marker = bool(
        re.search(
            r"命令|质问|高压|羞辱|压迫|反问|不准|返工|mistake|expect|important|leaving|afford|secretary|what do I need",
            text,
            re.IGNORECASE,
        )
    )
    return has_long_english or has_multi_line_or_exchange or (len(text) >= 42 and has_pressure_marker)


def _has_dialogue_coverage_visual_break(coverage: str) -> bool:
    return bool(_DIALOGUE_COVERAGE_TERMS_RE.search(coverage or ""))


def _agent_runtime_trace(
    agent_name: str,
    mode: str,
    started_at: float,
    status: str,
    output: str = "",
    error: Exception | None = None,
    **extra: Any,
) -> dict[str, Any]:
    _api_key, base_url, model, temperature = _get_llm_settings(agent_name)
    try:
        host = base_url.split("//", 1)[1].split("/", 1)[0] if "//" in base_url else base_url
    except Exception:
        host = base_url

    trace: dict[str, Any] = {
        "agent_name": agent_name,
        "mode": mode,
        "model": model,
        "host": host,
        "temperature": temperature,
        "status": status,
        "elapsed_seconds": round(time.perf_counter() - started_at, 3),
        "output_chars": len(output or ""),
    }
    if error is not None:
        trace["error_type"] = type(error).__name__
        trace["error"] = str(error)[:500]
    for key, value in extra.items():
        if value is not None:
            trace[key] = value
    return trace


def _shot_director_rule_block(aspect_ratio: str) -> str:
    return (
        f"{_script_fidelity_rules()}\n"
        f"{_subject_framing_rules()}\n"
        f"{_shot_composition_task_selection_rules()}\n"
        f"{_dialogue_coverage_contract_rules()}\n"
        f"{_space_rules_contract_rules()}\n"
        f"{_best_shot_selection_rules()}\n"
        # 空间几何合同：blocking/guard 也必须看到这些规则来验证和维护空间一致性
        f"{_spatial_geometry_contract_rules()}\n"
        f"{_camera_execution_rules()}\n"
        f"{_camera_task_selection_rules()}\n"
        f"{_shot_director_source_event_rules()}\n"
        f"{_shot_director_rhythm_match_rules()}\n"
        f"{_rhythm_insert_continuity_rules()}\n"
        f"【画幅】{aspect_ratio}\n\"        \"【防幻觉规则】\n"
        "1. 不新增剧情。\n"
        "2. 不新增人物。\n"
        "3. 不新增台词。\n"
        "4. 不新增动作。\n"
        "5. 不改变 id 和 fragment_id。\n"
        "6. 不改变人物出入场关系。\n"
        "7. 不保留 rejected_alternatives 的具体错误画面描述。\n"
        "8. 所有 must_not_show 必须简短，不要展开描述。\n"
        "9. action 只写可见动作，不写心理解释。\n"
        "10. 如果字段冲突，优先保留 continuity、space_rules、shots.action。\n"

    )


def _indent_level(line: str) -> int:
    return len(line) - len(line.lstrip(" "))


def _extract_parent_block_lines(section: str, field: str) -> list[str]:
    lines = section.splitlines()
    for idx, line in enumerate(lines):
        if not re.match(rf"^\s*{re.escape(field)}\s*:\s*$", line):
            continue
        parent_indent = _indent_level(line)
        block: list[str] = []
        for next_line in lines[idx + 1 :]:
            if not next_line.strip():
                continue
            if _indent_level(next_line) <= parent_indent:
                break
            block.append(next_line)
        return block
    return []


def _extract_nested_mapping_value(section: str, parent: str, child: str) -> str:
    for line in _extract_parent_block_lines(section, parent):
        match = re.match(rf'^\s*{re.escape(child)}\s*:\s*["\']?(.+?)["\']?\s*$', line)
        if match:
            return match.group(1).strip()
    return ""


def _extract_nested_list_items(section: str, parent: str, child: str) -> list[str]:
    block_lines = _extract_parent_block_lines(section, parent)
    items: list[str] = []
    for idx, line in enumerate(block_lines):
        match = re.match(rf"^(\s*){re.escape(child)}\s*:\s*$", line)
        if not match:
            continue
        child_indent = len(match.group(1))
        for next_line in block_lines[idx + 1 :]:
            if not next_line.strip():
                continue
            if _indent_level(next_line) <= child_indent:
                break
            item_match = re.match(r'^\s*-\s*["\']?(.+?)["\']?\s*$', next_line)
            if item_match:
                items.append(item_match.group(1).strip())
        break
    return items


def _trim_layout_text(value: str, limit: int = 120) -> str:
    cleaned = (value or "").strip().strip("'")
    if len(cleaned) <= limit:
        return cleaned
    return cleaned[: max(limit - 3, 1)].rstrip() + "..."


def _shot_director_layout_context(planner_output: str, aspect_ratio: str) -> str:
    sections = _extract_yaml_sections(planner_output or "")
    if not sections:
        return f"[Aspect Ratio]\n{aspect_ratio}\n\n[Planner Excerpt]\n{(planner_output or '').strip()[:2000]}"

    lines = [
        "[Layout Input Contract]",
        "Design only the camera skeleton for each fragment.",
        "Use the planner summary below. Do not re-interpret the whole script.",
        _runtime_context_contract_card(),
        "",
        "[Aspect Ratio]",
        aspect_ratio,
        "",
        "[Fragments]",
    ]
    for section in sections:
        fragment_id = _extract_fragment_id(section) or "unknown"
        dramatic_unit = _field_value(section, "dramatic_unit")
        active_cast = _extract_nested_list_items(section, "cast", "active")
        must_not_show = _extract_nested_list_items(section, "cast", "must_not_show")
        continuity_entry = _extract_nested_mapping_value(section, "continuity", "entry")
        continuity_exit = _extract_nested_mapping_value(section, "continuity", "exit")
        source_events = _source_script_events(section)
        key_events = [_trim_layout_text(event, 90) for event in source_events[:4]]
        dialogue_lines = [
            _trim_layout_text(event, 120)
            for event in source_events
            if ("\\uff1a" in event or ":" in event)
        ][:3]

        lines.extend(
            [
                f"- fragment_id: {fragment_id}",
                f"  dramatic_unit: {_trim_layout_text(dramatic_unit, 120) or 'n/a'}",
                f"  active_cast: {', '.join(active_cast) if active_cast else 'n/a'}",
                f"  must_not_show: {', '.join(must_not_show) if must_not_show else 'n/a'}",
                f"  continuity_entry: {_trim_layout_text(continuity_entry, 140) or 'n/a'}",
                f"  continuity_exit: {_trim_layout_text(continuity_exit, 140) or 'n/a'}",
                "  key_events:",
            ]
        )
        if key_events:
            lines.extend(f"    - {event}" for event in key_events)
        else:
            lines.append("    - n/a")
        lines.append("  dialogue_lines:")
        if dialogue_lines:
            lines.extend(f"    - {line}" for line in dialogue_lines)
        else:
            lines.append("    - none")
    return "\n".join(lines)


def _run_shot_director_single_pass(*args: Any, **kwargs: Any) -> tuple[str, dict[str, Any], dict[str, dict[str, Any]], dict[str, str]]:
    """Compatibility wrapper for the migrated shot_director implementation."""
    from . import shot_director_impl

    return shot_director_impl._run_shot_director_single_pass(*args, **kwargs)


def _run_shot_director_review_board(*args: Any, **kwargs: Any) -> tuple[str, dict[str, Any], dict[str, dict[str, Any]], dict[str, str]]:
    """Compatibility wrapper for the migrated shot_director review board."""
    from . import shot_director_impl

    return shot_director_impl._run_shot_director_review_board(*args, **kwargs)


def _run_story_planner_with_schema_repair(*args: Any, **kwargs: Any) -> Any:
    """Package-local compatibility entry for the migrated planner repair flow."""
    from .story_planner_impl import _run_story_planner_with_schema_repair as _impl

    return _impl(*args, **kwargs)



