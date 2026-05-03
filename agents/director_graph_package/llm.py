from __future__ import annotations

import json
import os
import re
import time as _time
from typing import Any

import httpx
import yaml

from ..request_context import request_session_id
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
    if layer.get("api_key"):
        settings["api_key"] = layer["api_key"]
    if layer.get("base_url"):
        settings["base_url"] = layer["base_url"]
    if layer.get("model"):
        settings["model"] = layer["model"]
    if layer.get("default_model"):
        settings["model"] = layer["default_model"]
    if "temperature" in layer:
        settings["temperature"] = layer["temperature"]


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
            if key == "temperature":
                continue
            base_payload[key] = value
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
                last_retryable = status_code >= 500
            except Exception as exc:
                last_exc = exc
                last_retryable = False

            if not last_retryable or attempt == max_retries:
                break

            wait_seconds = 2 ** attempt
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
