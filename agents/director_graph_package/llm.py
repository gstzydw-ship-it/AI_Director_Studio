from __future__ import annotations

import json
import ast
import os
import re
import time as _time
from typing import Any

import httpx
import yaml

from ..request_context import emit_runtime_event, request_session_id
from ..utils import COMFLY_BASE_URL, load_yaml_config
from .types import AGENT_CONFIG_PARENTS, CONFIG_FILE, DEFAULT_LLM_MODEL, LLMSettings, OUTPUT_DIR, SESSION_ID_RE


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
    if isinstance(model, dict):
        return _normalise_model_name(model.get("model") or model.get("id"))
    value = str(model or "").strip()
    for _ in range(3):
        if not (value.startswith("{") and "model" in value):
            break
        try:
            parsed = ast.literal_eval(value)
        except (SyntaxError, ValueError):
            break
        if not isinstance(parsed, dict) or "model" not in parsed:
            break
        next_value = str(parsed.get("model") or "").strip()
        if not next_value or next_value == value:
            break
        value = next_value
    if value.startswith("openai/"):
        value = value.replace("openai/", "", 1)
    return value


def _is_masked_api_key(value: Any) -> bool:
    return bool(re.fullmatch(r"\*{3,}", str(value or "").strip()))


def _clean_api_key(value: Any) -> str:
    api_key = str(value or "").strip()
    return "" if _is_masked_api_key(api_key) else api_key


def _optional_float(value: Any) -> float | None:
    try:
        return float(value) if value is not None else None
    except (TypeError, ValueError):
        return None


def _agent_config_layers(full_config: dict[str, Any], agent_name: str) -> list[tuple[str, dict[str, Any]]]:
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


def _normalise_session_id(session_id: str | None) -> str:
    safe = SESSION_ID_RE.sub("", (session_id or "local").strip())[:80]
    return safe or "local"


def _load_session_model_profile() -> dict[str, Any]:
    session_id = _normalise_session_id(request_session_id.get("local"))
    state_path = os.path.join(OUTPUT_DIR, "sessions", session_id, "pipeline_state.json")
    if not os.path.exists(state_path):
        return {}
    try:
        with open(state_path, "r", encoding="utf-8-sig") as file:
            state = json.load(file)
    except Exception:
        return {}
    profile = state.get("model_profile_snapshot") if isinstance(state, dict) else {}
    return profile if isinstance(profile, dict) else {}


def _profile_global_layer(profile: dict[str, Any]) -> dict[str, Any]:
    if not profile:
        return {}
    layer = {
        "api_key": profile.get("api_key"),
        "base_url": profile.get("base_url"),
        "model": profile.get("model") or profile.get("default_model"),
        "temperature": profile.get("temperature"),
        "fallback_models": profile.get("fallback_models"),
        "max_tokens": profile.get("max_tokens"),
        "max_retries": profile.get("max_retries"),
        "timeout_seconds": profile.get("timeout_seconds"),
        "connect_timeout_seconds": profile.get("connect_timeout_seconds"),
        "read_timeout_seconds": profile.get("read_timeout_seconds"),
        "write_timeout_seconds": profile.get("write_timeout_seconds"),
        "fallback_routes": profile.get("fallback_routes"),
        "extra_params": profile.get("extra_params"),
    }
    return {key: value for key, value in layer.items() if value not in (None, "", [])}


def _profile_agent_layers(profile: dict[str, Any], agent_name: str) -> list[tuple[str, dict[str, Any]]]:
    if not profile or not agent_name:
        return []
    agent_models = _as_mapping(profile.get("agent_models")) or _as_mapping(profile.get("agents"))
    layers: list[tuple[str, dict[str, Any]]] = []

    def coerce_layer(value: Any) -> dict[str, Any]:
        if isinstance(value, str):
            return {"model": value}
        if isinstance(value, dict):
            result = dict(value)
            if result.get("default_model") and not result.get("model"):
                result["model"] = result["default_model"]
            return result
        return {}

    parent_name = AGENT_CONFIG_PARENTS.get(agent_name)
    if parent_name:
        parent_layer = coerce_layer(agent_models.get(parent_name))
        if parent_layer:
            layers.append((parent_name, parent_layer))
    agent_layer = coerce_layer(agent_models.get(agent_name))
    if agent_layer:
        layers.append((agent_name, agent_layer))
    return layers


def _apply_llm_config_layer(settings: dict[str, Any], layer: dict[str, Any]) -> None:
    if _clean_api_key(layer.get("api_key")):
        settings["api_key"] = _clean_api_key(layer.get("api_key"))
    if layer.get("base_url"):
        settings["base_url"] = layer["base_url"]
    if layer.get("model"):
        settings["model"] = layer["model"]
    if layer.get("default_model"):
        settings["model"] = layer["default_model"]
    if "temperature" in layer:
        settings["temperature"] = layer["temperature"]

    route_preset = str(layer.get("route_preset") or "").strip()
    route: dict[str, Any] = {}
    if route_preset == "custom":
        route = _as_mapping(layer.get("custom_route"))
        if not route and (layer.get("custom_base_url") or layer.get("custom_api_key")):
            route = {
                "base_url": layer.get("custom_base_url"),
                "api_key": layer.get("custom_api_key"),
            }
    elif route_preset == "fallback":
        fallback_routes = layer.get("fallback_routes")
        if isinstance(fallback_routes, list) and fallback_routes:
            route = _as_mapping(fallback_routes[0])
    if route:
        if route.get("base_url"):
            settings["base_url"] = route["base_url"]
        route_api_key = _clean_api_key(route.get("api_key"))
        if route_api_key:
            settings["api_key"] = route_api_key
        if route.get("model") or route.get("default_model"):
            settings["model"] = route.get("model") or route.get("default_model")


def resolve_llm_settings(agent_name: str = "", full_config: dict[str, Any] | None = None) -> LLMSettings:
    config = load_config() if full_config is None else full_config
    llm_config = _as_mapping(config.get("llm"))
    raw_settings: dict[str, Any] = {
        "api_key": os.getenv("DIRECTOR_LLM_API_KEY") or "",
        "base_url": os.getenv("DIRECTOR_LLM_BASE_URL") or COMFLY_BASE_URL,
        "model": os.getenv("DIRECTOR_LLM_MODEL") or DEFAULT_LLM_MODEL,
        "temperature": None,
    }

    _apply_llm_config_layer(raw_settings, llm_config)

    layers = _agent_config_layers(config, agent_name)
    for _layer_name, layer in layers:
        _apply_llm_config_layer(raw_settings, layer)

    profile = _load_session_model_profile()
    _apply_llm_config_layer(raw_settings, _profile_global_layer(profile))
    for _layer_name, layer in _profile_agent_layers(profile, agent_name):
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
    return resolve_llm_settings(agent_name).as_tuple()


def _get_llm_extra_params(agent_name: str = "") -> dict[str, Any]:
    full_config = load_config()
    merged: dict[str, Any] = {}

    global_extra = _as_mapping(full_config.get("llm")).get("extra_params")
    if isinstance(global_extra, dict):
        merged.update(global_extra)

    for _layer_name, layer in _agent_config_layers(full_config, agent_name):
        agent_extra = layer.get("extra_params")
        if isinstance(agent_extra, dict):
            merged.update(agent_extra)

    profile = _load_session_model_profile()
    profile_extra = _profile_global_layer(profile).get("extra_params")
    if isinstance(profile_extra, dict):
        merged.update(profile_extra)
    for _layer_name, layer in _profile_agent_layers(profile, agent_name):
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


def _coerce_bool(value: Any, default: bool = False) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return default
    if isinstance(value, (int, float)):
        return bool(value)
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"1", "true", "yes", "y", "on"}:
            return True
        if normalized in {"0", "false", "no", "n", "off"}:
            return False
    return default


def _is_shot_director_agent(agent_name: str) -> bool:
    return agent_name in {
        "shot_director",
        "shot_director_layout",
        "shot_director_blocking",
        "shot_director_guard",
    }


def _get_llm_runtime_option(agent_name: str, key: str, default: Any) -> Any:
    full_config = load_config()
    value = _as_mapping(full_config.get("llm")).get(key, default)
    for _layer_name, layer in _agent_config_layers(full_config, agent_name):
        if key in layer:
            value = layer[key]
    profile = _load_session_model_profile()
    profile_global = _profile_global_layer(profile)
    if key in profile_global:
        value = profile_global[key]
    for _layer_name, layer in _profile_agent_layers(profile, agent_name):
        if key in layer:
            value = layer[key]

    # Shot director prompts are usually the longest and the upstream gateway often
    # drops long-running responses before completion.  UI model profiles commonly
    # store a global max_retries=1/2, which used to silently override the safer
    # config/settings.yaml value and caused "已重试 1 次" failures.  Keep a
    # conservative floor for this agent unless the caller explicitly passes a
    # max_retries argument to call_llm().
    if _is_shot_director_agent(agent_name) and key == "max_retries":
        value = max(_coerce_int(value, 3, minimum=1), 3)
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
    profile = _load_session_model_profile()
    profile_global = _profile_global_layer(profile)
    if "fallback_models" in profile_global:
        value = profile_global["fallback_models"]
    for _layer_name, layer in _profile_agent_layers(profile, agent_name):
        if "fallback_models" in layer:
            value = layer["fallback_models"]
    return _normalise_model_list(value)


def _normalise_fallback_routes(value: Any) -> list[dict[str, Any]]:
    if isinstance(value, dict):
        candidates = [value]
    elif isinstance(value, (list, tuple)):
        candidates = list(value)
    else:
        candidates = []

    routes: list[dict[str, Any]] = []
    for candidate in candidates:
        route = _as_mapping(candidate)
        base_url = _normalise_base_url(route.get("base_url"))
        model = _normalise_model_name(route.get("model") or route.get("default_model"))
        if not base_url and not model:
            continue
        routes.append(
            {
                "api_key": _clean_api_key(route.get("api_key")),
                "base_url": base_url,
                "model": model,
                "fallback_models": _normalise_model_list(route.get("fallback_models", [])),
            }
        )
    return routes


def _get_llm_fallback_routes(agent_name: str = "") -> list[dict[str, Any]]:
    full_config = load_config()
    routes: list[dict[str, Any]] = []

    global_routes = _normalise_fallback_routes(_as_mapping(full_config.get("llm")).get("fallback_routes"))
    routes.extend(global_routes)

    for _layer_name, layer in _agent_config_layers(full_config, agent_name):
        if "fallback_routes" in layer:
            routes.extend(_normalise_fallback_routes(layer.get("fallback_routes")))

    profile = _load_session_model_profile()
    profile_global = _profile_global_layer(profile)
    if "fallback_routes" in profile_global:
        routes.extend(_normalise_fallback_routes(profile_global.get("fallback_routes")))
    for _layer_name, layer in _profile_agent_layers(profile, agent_name):
        if "fallback_routes" in layer:
            routes.extend(_normalise_fallback_routes(layer.get("fallback_routes")))

    deduped: list[dict[str, Any]] = []
    seen: set[tuple[str, str, tuple[str, ...]]] = set()
    for route in routes:
        key = (route.get("base_url", ""), route.get("model", ""), tuple(route.get("fallback_models") or []))
        if key in seen:
            continue
        seen.add(key)
        deduped.append(route)
    return deduped


def _host_matches_base_url(left: Any, right: Any) -> bool:
    left_host = _runtime_event_base_url_host(_normalise_base_url(left))
    right_host = _runtime_event_base_url_host(_normalise_base_url(right))
    return bool(left_host and right_host and left_host == right_host)


def _configured_api_key_for_base_url(base_url: str, agent_name: str = "") -> str:
    """Find a configured key for a fallback route host without cross-host reuse."""
    if not base_url:
        return ""

    full_config = load_config()
    candidates: list[dict[str, Any]] = []
    for section_name in ("llm", "image_generation", "vectordb"):
        candidates.append(_as_mapping(full_config.get(section_name)))

    agent_models = _as_mapping(full_config.get("agent_models"))
    parent_name = AGENT_CONFIG_PARENTS.get(agent_name)
    if parent_name:
        candidates.append(_as_mapping(agent_models.get(parent_name)))
    if agent_name:
        candidates.append(_as_mapping(agent_models.get(agent_name)))
    candidates.extend(_as_mapping(value) for value in agent_models.values())

    profile = _load_session_model_profile()
    candidates.append(_profile_global_layer(profile))
    for _layer_name, layer in _profile_agent_layers(profile, agent_name):
        candidates.append(layer)
    profile_agent_models = _as_mapping(profile.get("agent_models")) or _as_mapping(profile.get("agents"))
    candidates.extend(_as_mapping(value) for value in profile_agent_models.values())

    for candidate in candidates:
        api_key = _clean_api_key(candidate.get("api_key"))
        candidate_base_url = candidate.get("base_url")
        if api_key and candidate_base_url and _host_matches_base_url(candidate_base_url, base_url):
            return api_key
    return ""


def _effective_retry_budget(agent_name: str, max_retries: int, *, has_fallback_routes: bool = False) -> int:
    if has_fallback_routes:
        return max_retries
    if agent_name in {"story_planner", "director_showrunner"}:
        return max(max_retries, 3)
    if agent_name == "director_showrunner_logic_reviewer":
        return max(max_retries, 2)
    return max_retries


def _effective_timeout_settings(
    agent_name: str,
    request_timeout: float,
    connect_timeout: float,
    read_timeout: float,
    write_timeout: float,
) -> tuple[float, float, float, float]:
    if agent_name == "story_planner":
        request_timeout = min(max(request_timeout, 180.0), 240.0)
        connect_timeout = min(connect_timeout, 20.0)
        read_timeout = min(max(read_timeout, 180.0), 240.0)
        write_timeout = min(max(write_timeout, 60.0), 90.0)
    elif agent_name in {"director_showrunner", "director_showrunner_logic_reviewer"}:
        request_timeout = min(max(request_timeout, 300.0), 360.0)
        connect_timeout = min(connect_timeout, 20.0)
        read_timeout = min(max(read_timeout, 300.0), 360.0)
        write_timeout = min(max(write_timeout, 60.0), 90.0)
    elif _is_shot_director_agent(agent_name):
        request_timeout = min(max(request_timeout, 600.0), 900.0)
        connect_timeout = min(connect_timeout, 20.0)
        read_timeout = min(max(read_timeout, 600.0), 900.0)
        write_timeout = min(max(write_timeout, 90.0), 120.0)
    return request_timeout, connect_timeout, read_timeout, write_timeout


def _llm_failure_context(
    *,
    agent_name: str,
    model: str,
    max_retries: int,
    images_base64: list[str] | None,
    attempted_models: list[str],
    timeout_seconds: float | None = None,
    connect_timeout_seconds: float | None = None,
    read_timeout_seconds: float | None = None,
    write_timeout_seconds: float | None = None,
    bypass_proxy: bool = True,
) -> str:
    image_count = len(images_base64 or [])
    attempted_note = f"；尝试模型: {', '.join(attempted_models)}" if attempted_models else ""
    timeout_parts: list[str] = []
    if timeout_seconds is not None:
        timeout_parts.append(f"total={timeout_seconds:g}s")
    if connect_timeout_seconds is not None:
        timeout_parts.append(f"connect={connect_timeout_seconds:g}s")
    if read_timeout_seconds is not None:
        timeout_parts.append(f"read={read_timeout_seconds:g}s")
    if write_timeout_seconds is not None:
        timeout_parts.append(f"write={write_timeout_seconds:g}s")
    timeout_note = f"；timeout: {', '.join(timeout_parts)}" if timeout_parts else ""
    proxy_note = "；环境代理: 已绕开" if bypass_proxy else "；环境代理: 使用系统环境"
    image_note = f"；参考图: {image_count} 张" if image_count else "；参考图: 未发送"
    return f"agent={agent_name or '?'}, model={model}，已重试 {max_retries} 次{attempted_note}{image_note}{timeout_note}{proxy_note}"


def _raise_llm_failure(
    last_exc: Exception | None,
    *,
    agent_name: str,
    model: str,
    max_retries: int,
    images_base64: list[str] | None,
    attempted_models: list[str],
    timeout_seconds: float | None = None,
    connect_timeout_seconds: float | None = None,
    read_timeout_seconds: float | None = None,
    write_timeout_seconds: float | None = None,
    bypass_proxy: bool = True,
) -> None:
    context = _llm_failure_context(
        agent_name=agent_name,
        model=model,
        max_retries=max_retries,
        images_base64=images_base64,
        attempted_models=attempted_models,
        timeout_seconds=timeout_seconds,
        connect_timeout_seconds=connect_timeout_seconds,
        read_timeout_seconds=read_timeout_seconds,
        write_timeout_seconds=write_timeout_seconds,
        bypass_proxy=bypass_proxy,
    )
    image_count = len(images_base64 or [])
    image_hint = (
        f"本次请求发送了 {image_count} 张参考图；如果它们很大，可能导致上传/读取超时，可先压缩或减少参考图。"
        if image_count
        else "本次请求未发送参考图；不要按“参考图过大”排查，优先检查上游模型网关、模型排队、提示词过长或网络读超时。"
    )
    if isinstance(last_exc, httpx.RemoteProtocolError):
        raise RuntimeError(
            f"LLM 服务在返回前断开连接（{context}）。{image_hint} 原始错误: {last_exc}"
        ) from last_exc
    if isinstance(last_exc, httpx.ConnectError):
        raise RuntimeError(
            f"LLM 网络连接失败（{context}）。通常是上游网关不可达、TLS 抖动、本机网络中断或代理配置问题。原始错误: {last_exc}"
        ) from last_exc
    if isinstance(last_exc, httpx.TimeoutException):
        raise RuntimeError(
            f"LLM 服务响应超时（{context}）。{image_hint} 原始错误: {last_exc}"
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
            f"LLM 接口返回 HTTP {status_code}（{context}）: {detail}"
        ) from last_exc
    raise RuntimeError(f"LLM 调用失败（{context}）: {last_exc}") from last_exc


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


def _extract_stream_delta_text(chunk: dict[str, Any]) -> str:
    choices = chunk.get("choices")
    if not isinstance(choices, list) or not choices:
        return ""
    first_choice = choices[0] or {}
    if not isinstance(first_choice, dict):
        return ""
    delta = first_choice.get("delta")
    if isinstance(delta, dict):
        content = delta.get("content")
        if isinstance(content, str) and content:
            return content
        if isinstance(content, list):
            return _extract_message_text({"content": content})
        for key in ("output_text", "text"):
            text = delta.get(key)
            if isinstance(text, str) and text:
                return text
    message = first_choice.get("message")
    if isinstance(message, dict):
        text = _extract_message_text(message)
        if text:
            return text
    text = first_choice.get("text")
    return text if isinstance(text, str) else ""


def _read_chat_completion_stream(response: httpx.Response) -> str:
    parts: list[str] = []
    for raw_line in response.iter_lines():
        if not raw_line:
            continue
        line = raw_line.decode("utf-8", errors="ignore") if isinstance(raw_line, bytes) else str(raw_line)
        line = line.strip()
        if not line or line.startswith(":") or not line.startswith("data:"):
            continue
        data = line[5:].strip()
        if not data:
            continue
        if data == "[DONE]":
            break
        try:
            chunk = json.loads(data)
        except json.JSONDecodeError:
            continue
        if isinstance(chunk, dict):
            text = _extract_stream_delta_text(chunk)
            if text:
                parts.append(text)
    return "".join(parts)


def _llm_streaming_enabled(agent_name: str, extra_params: dict[str, Any], images_base64: list[str] | None) -> bool:
    if images_base64:
        return False
    if "stream" in extra_params:
        return _coerce_bool(extra_params.get("stream"), False)
    if "streaming" in extra_params:
        return _coerce_bool(extra_params.get("streaming"), False)
    return _coerce_bool(_get_llm_runtime_option(agent_name, "stream", False), False) or _coerce_bool(
        _get_llm_runtime_option(agent_name, "streaming", False),
        False,
    )


def _runtime_event_base_url_host(base_url: str) -> str:
    try:
        return base_url.split("//", 1)[1].split("/", 1)[0] if "//" in base_url else base_url
    except Exception:
        return str(base_url or "")


def call_llm(
    system_prompt: str,
    user_prompt: str,
    images_base64: list[str] | None = None,
    temperature: float = 0.4,
    agent_name: str = "",
    max_retries: int | None = None,
    bypass_proxy: bool = True,
) -> str:
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
            content.append({"type": "image_url", "image_url": {"url": image_url}})
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

    extra_params = _get_llm_extra_params(agent_name)
    if extra_params:
        for key, value in extra_params.items():
            if key in {"temperature", "stream", "streaming"}:
                continue
            base_payload[key] = value
        if isinstance(extra_params.get("thinking"), dict) and extra_params["thinking"].get("type") == "enabled":
            base_payload["temperature"] = 1.0
            budget = extra_params["thinking"].get("budget_tokens", 0)
            if isinstance(budget, (int, float)) and budget > 0:
                needed = int(budget) + 8192
                if max_tokens <= 0 or max_tokens < needed:
                    base_payload["max_tokens"] = needed

    stream_enabled = _llm_streaming_enabled(agent_name, extra_params, images_base64)
    if stream_enabled:
        base_payload["stream"] = True

    fallback_route_configs = _get_llm_fallback_routes(agent_name)
    if max_retries is None:
        max_retries = _coerce_int(_get_llm_runtime_option(agent_name, "max_retries", 2), 2, minimum=1)
    else:
        max_retries = max(1, int(max_retries))

    last_exc: Exception | None = None
    last_retryable = False
    primary_models = _normalise_model_list([model, *_get_llm_fallback_models(agent_name)])
    routes_to_try: list[dict[str, Any]] = [
        {
            "api_key": api_key,
            "base_url": base_url,
            "models": primary_models,
            "label": "primary",
        }
    ]
    for route in fallback_route_configs:
        route_base_url = _normalise_base_url(route.get("base_url") or base_url)
        route_api_key = str(route.get("api_key") or "").strip()
        if not route_api_key:
            route_api_key = _configured_api_key_for_base_url(route_base_url, agent_name)
        if not route_api_key:
            primary_host = _runtime_event_base_url_host(base_url)
            route_host = _runtime_event_base_url_host(route_base_url)
            if route_host and primary_host and route_host != primary_host:
                if agent_name:
                    print(
                        f"  [LLM] WARN: skipping fallback route @{route_host} for {agent_name}; "
                        "it has no api_key and cannot inherit credentials from a different host."
                    )
                    emit_runtime_event(
                        "llm_route_fallback_skipped",
                        agent_name=agent_name,
                        route_host=route_host,
                        reason="missing_api_key_for_different_host",
                    )
                continue
            route_api_key = api_key
        route_model = _normalise_model_name(route.get("model") or model)
        route_models = _normalise_model_list([route_model, *(route.get("fallback_models") or [])])
        if not route_api_key or not route_base_url or not route_models:
            continue
        routes_to_try.append(
            {
                "api_key": route_api_key,
                "base_url": route_base_url,
                "models": route_models,
                "label": "fallback route",
            }
        )

    max_retries = _effective_retry_budget(agent_name, max_retries, has_fallback_routes=len(routes_to_try) > 1)

    attempted_models: list[str] = []
    proxy_modes: list[tuple[bool, bool, str]] = [(not bypass_proxy, bypass_proxy, "")]
    if bypass_proxy:
        proxy_modes.append((True, False, " system-proxy fallback"))

    for route_index, route in enumerate(routes_to_try):
        active_base_url = str(route["base_url"]).rstrip("/")
        route_headers = dict(headers)
        route_headers["Authorization"] = f"Bearer {route['api_key']}"
        route_host = _runtime_event_base_url_host(active_base_url)
        models_to_try = route["models"]

        if route_index and agent_name:
            print(f"  [LLM] WARN: switching {agent_name} to fallback route @{route_host} after retryable failure.")
            emit_runtime_event(
                "llm_route_fallback",
                agent_name=agent_name,
                route_host=route_host,
                route_label=route.get("label", "fallback route"),
            )

        for model_index, active_model in enumerate(models_to_try):
            attempted_models.append(active_model)
            payload = dict(base_payload)
            payload["model"] = active_model

            if agent_name:
                fallback_note = " fallback" if model_index or route_index else ""
                print(f"  [LLM] {agent_name} -> {active_model} @ {route_host}{fallback_note}")
                emit_runtime_event(
                    "llm_model_selected",
                    agent_name=agent_name,
                    model=active_model,
                    route_host=route_host,
                    route_label=route.get("label", "primary"),
                    fallback=bool(model_index or route_index),
                    image_count=len(images_base64 or []),
                )

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
            request_timeout, connect_timeout, read_timeout, write_timeout = _effective_timeout_settings(
                agent_name,
                request_timeout,
                connect_timeout,
                read_timeout,
                write_timeout,
            )
            timeout = httpx.Timeout(request_timeout, connect=connect_timeout, read=read_timeout, write=write_timeout)

            for proxy_index, (trust_env, active_bypass_proxy, proxy_label) in enumerate(proxy_modes):
                for attempt in range(1, max_retries + 1):
                    attempt_started = _time.perf_counter()
                    emit_runtime_event(
                        "llm_attempt_started",
                        agent_name=agent_name,
                        model=active_model,
                        route_host=route_host,
                        attempt=attempt,
                        max_retries=max_retries,
                        proxy_mode="system" if trust_env else "direct",
                        timeout_seconds=request_timeout,
                        stream=stream_enabled,
                    )
                    try:
                        with httpx.Client(timeout=timeout, trust_env=trust_env) as client:
                            if stream_enabled:
                                with client.stream("POST", f"{active_base_url}/chat/completions", headers=route_headers, json=payload) as response:
                                    response.raise_for_status()
                                    text = _read_chat_completion_stream(response)
                                if not text:
                                    raise RuntimeError("LLM stream response did not include content")
                                emit_runtime_event(
                                    "llm_attempt_succeeded",
                                    agent_name=agent_name,
                                    model=active_model,
                                    route_host=route_host,
                                    attempt=attempt,
                                    elapsed_seconds=round(_time.perf_counter() - attempt_started, 3),
                                    output_chars=len(text or ""),
                                    stream=True,
                                )
                                return text.strip()
                            response = client.post(f"{active_base_url}/chat/completions", headers=route_headers, json=payload)
                            response.raise_for_status()
                            result = response.json()
                        if not isinstance(result, dict):
                            raise RuntimeError(f"LLM 响应格式异常，期待 dict，得到 {type(result).__name__}：{str(result)[:400]}")
                        choices = result.get("choices")
                        if not choices or not isinstance(choices, list):
                            raise RuntimeError(f"LLM 响应缺少 choices 字段：{json.dumps(result, ensure_ascii=False)[:500]}")
                        message = (choices[0] or {}).get("message") or {}
                        text = _extract_message_text(message)
                        emit_runtime_event(
                            "llm_attempt_succeeded",
                            agent_name=agent_name,
                            model=active_model,
                            route_host=route_host,
                            attempt=attempt,
                            elapsed_seconds=round(_time.perf_counter() - attempt_started, 3),
                            output_chars=len(text or ""),
                            stream=False,
                        )
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
                        last_retryable = status_code >= 500
                    except Exception as exc:
                        last_exc = exc
                        last_retryable = False

                    emit_runtime_event(
                        "llm_attempt_failed",
                        agent_name=agent_name,
                        model=active_model,
                        route_host=route_host,
                        attempt=attempt,
                        elapsed_seconds=round(_time.perf_counter() - attempt_started, 3),
                        error_type=type(last_exc).__name__ if last_exc else "UnknownError",
                        retryable=last_retryable,
                        proxy_mode="system" if trust_env else "direct",
                    )

                    if not last_retryable or attempt == max_retries:
                        break

                    wait_seconds = 2 ** attempt
                    print(f"  [LLM] WARN: attempt {attempt} failed on {active_model}{proxy_label} ({type(last_exc).__name__}); retrying in {wait_seconds}s...")
                    emit_runtime_event(
                        "llm_retry_wait",
                        agent_name=agent_name,
                        model=active_model,
                        wait_seconds=wait_seconds,
                        next_attempt=attempt + 1,
                    )
                    _time.sleep(wait_seconds)

                if (
                    proxy_index == 0
                    and bypass_proxy
                    and model_index == len(models_to_try) - 1
                    and isinstance(last_exc, (httpx.RemoteProtocolError, httpx.ConnectError, httpx.NetworkError))
                ):
                    print(f"  [LLM] WARN: direct connection failed on {active_model}; retrying with system proxy environment...")
                    emit_runtime_event(
                        "llm_proxy_fallback",
                        agent_name=agent_name,
                        model=active_model,
                        route_host=route_host,
                    )
                    continue
                break

            if last_retryable and model_index < len(models_to_try) - 1:
                next_model = models_to_try[model_index + 1]
                print(f"  [LLM] WARN: {active_model} failed after {max_retries} attempts; trying fallback model {next_model}...")
                emit_runtime_event(
                    "llm_model_fallback",
                    agent_name=agent_name,
                    failed_model=active_model,
                    next_model=next_model,
                    max_retries=max_retries,
                )
                continue
            break

        if last_retryable and route_index < len(routes_to_try) - 1:
            continue
        break

    emit_runtime_event(
        "llm_failed",
        agent_name=agent_name,
        attempted_models=attempted_models,
        error_type=type(last_exc).__name__ if last_exc else "UnknownError",
    )
    _raise_llm_failure(
        last_exc,
        agent_name=agent_name,
        model=attempted_models[-1] if attempted_models else model,
        max_retries=max_retries,
        images_base64=images_base64,
        attempted_models=attempted_models,
        timeout_seconds=request_timeout if "request_timeout" in locals() else None,
        connect_timeout_seconds=connect_timeout if "connect_timeout" in locals() else None,
        read_timeout_seconds=read_timeout if "read_timeout" in locals() else None,
        write_timeout_seconds=write_timeout if "write_timeout" in locals() else None,
        bypass_proxy=active_bypass_proxy if "active_bypass_proxy" in locals() else bypass_proxy,
    )
