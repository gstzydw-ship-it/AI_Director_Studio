from __future__ import annotations

import asyncio
import os
import shutil
import time
from typing import Any, List, Optional

from .utils import get_base_dir, get_config_path, get_output_dir, load_yaml_config


ROOT_DIR = get_base_dir()
DISABLED_VALUES = {"", "0", "false", "no", "off", "disabled", "none", "null"}


def _load_config() -> dict[str, Any]:
    try:
        return load_yaml_config(get_config_path())
    except Exception:
        return {}


def _mcp_config() -> dict[str, Any]:
    config = _load_config().get("mcp", {})
    return config if isinstance(config, dict) else {}


def _as_bool(value: Any, default: bool = False) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    return str(value).strip().lower() not in DISABLED_VALUES


def _mcp_timeout_seconds() -> float:
    value = _mcp_config().get("timeout_seconds", 90)
    try:
        return max(10.0, float(value))
    except (TypeError, ValueError):
        return 90.0


def _fallback_enabled() -> bool:
    return _as_bool(_mcp_config().get("fallback_enabled"), default=True)


def _log_tool_details() -> bool:
    return _as_bool(_mcp_config().get("log_tool_details"), default=False)


def _agent_server_type(agent_name: str, requested_type: str) -> str | None:
    config = _mcp_config()
    if not _as_bool(config.get("enabled"), default=False):
        return None

    agents = config.get("agents", {})
    agent_setting: Any = requested_type
    if isinstance(agents, dict) and agent_name in agents:
        agent_setting = agents[agent_name]

    if isinstance(agent_setting, dict):
        if not _as_bool(agent_setting.get("enabled"), default=True):
            return None
        agent_setting = agent_setting.get("server_type", requested_type)

    server_type = str(agent_setting or "").strip().lower()
    if server_type in DISABLED_VALUES:
        return None
    return server_type or requested_type


def _resolve_npx_command() -> str | None:
    candidates = ["npx.cmd", "npx.exe", "npx"] if os.name == "nt" else ["npx"]
    for candidate in candidates:
        found = shutil.which(candidate)
        if found:
            return found
    return None


def _filesystem_roots() -> list[str]:
    configured = _mcp_config().get("filesystem_roots")
    if isinstance(configured, list):
        roots = [str(item) for item in configured if str(item).strip()]
    else:
        roots = [
            os.path.join(ROOT_DIR, "knowledge"),
            os.path.join(get_output_dir(), "sessions"),
        ]
    resolved: list[str] = []
    for root in roots:
        path = root if os.path.isabs(root) else os.path.join(ROOT_DIR, root)
        path = os.path.abspath(path)
        if os.path.exists(path):
            resolved.append(path)
    return resolved


def _server_args(server_type: str) -> tuple[str, list[str]]:
    npx_cmd = _resolve_npx_command()
    if not npx_cmd:
        raise RuntimeError("未找到 npx，无法启动 MCP stdio server。")

    if server_type == "sequential":
        return npx_cmd, ["-y", "@modelcontextprotocol/server-sequential-thinking"]
    if server_type == "memory":
        return npx_cmd, ["-y", "@modelcontextprotocol/server-memory"]
    if server_type == "filesystem":
        roots = _filesystem_roots()
        if not roots:
            raise RuntimeError("filesystem MCP 未配置可访问目录。")
        return npx_cmd, ["-y", "@modelcontextprotocol/server-filesystem", *roots]

    raise ValueError(f"不支持的 MCP 服务器类型: {server_type}")


def _message_text(message: Any) -> str:
    content = getattr(message, "content", message)
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for item in content:
            if isinstance(item, dict):
                parts.append(str(item.get("text") or item.get("content") or ""))
            else:
                parts.append(str(item))
        return "\n".join(part for part in parts if part).strip()
    return str(content or "")


def _host_from_base_url(base_url: str) -> str:
    try:
        return base_url.split("//", 1)[1].split("/", 1)[0] if "//" in base_url else base_url
    except Exception:
        return base_url or ""


def _init_call_trace(
    agent_name: str,
    requested_server: str,
    resolved_server: str | None,
    temperature: float,
) -> dict[str, Any]:
    from agents.director_graph import _get_llm_settings

    _api_key, base_url, model, agent_temperature = _get_llm_settings(agent_name)
    resolved_temperature = agent_temperature if agent_temperature is not None else temperature
    return {
        "agent_name": agent_name,
        "requested_server_type": requested_server,
        "resolved_server_type": resolved_server,
        "model": model,
        "host": _host_from_base_url(base_url),
        "temperature": resolved_temperature,
        "mcp_timeout_seconds": _mcp_timeout_seconds(),
        "fallback_enabled": _fallback_enabled(),
    }


def _fallback_call_llm(
    system_prompt: str,
    user_prompt: str,
    images_base64: Optional[List[str]],
    agent_name: str,
    temperature: float,
    reason: str,
) -> str:
    if not _fallback_enabled():
        raise RuntimeError(reason)
    print(f"  [MCP] {agent_name}: {reason}；已降级为普通 LLM 调用。")
    from agents.director_graph import call_llm

    return call_llm(
        system_prompt,
        user_prompt,
        images_base64=images_base64,
        agent_name=agent_name,
        temperature=temperature,
    )


async def _invoke_mcp_agent_async(
    system_prompt: str,
    user_prompt: str,
    server_type: str,
    images_base64: Optional[List[str]],
    agent_name: str,
    temperature: float,
) -> str:
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client
    from langchain_mcp_adapters.tools import load_mcp_tools
    from langchain_openai import ChatOpenAI
    from langgraph.prebuilt import create_react_agent

    from agents.director_graph import _get_llm_settings

    api_key, base_url, model, agent_temperature = _get_llm_settings(agent_name)
    if not api_key or not base_url:
        raise ValueError("LLM API key/base_url 未配置，请先配置后端 settings。")
    if agent_temperature is not None:
        temperature = agent_temperature

    command, args = _server_args(server_type)
    print(f"  [MCP] {agent_name} -> {model} via {server_type}")

    llm = ChatOpenAI(
        model=model,
        api_key=api_key,
        base_url=base_url,
        temperature=temperature,
        timeout=_mcp_timeout_seconds(),
    )

    server_params = StdioServerParameters(command=command, args=args, env=os.environ.copy())
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            tools = await load_mcp_tools(session)
            agent = create_react_agent(
                llm,
                tools=tools,
                prompt=system_prompt,
                checkpointer=False,
            )

            if images_base64:
                content: list[dict[str, Any]] = [{"type": "text", "text": user_prompt}]
                for image in images_base64:
                    image_url = image if image.startswith("data:") else f"data:image/jpeg;base64,{image}"
                    content.append({"type": "image_url", "image_url": {"url": image_url}})
                messages = [{"role": "user", "content": content}]
            else:
                messages = [{"role": "user", "content": user_prompt}]

            response = await agent.ainvoke({"messages": messages})
            messages_out = response.get("messages", []) if isinstance(response, dict) else []
            tool_calls = 0
            tool_results = 0
            for msg in messages_out:
                tool_calls += len(getattr(msg, "tool_calls", None) or [])
                if getattr(msg, "type", "") == "tool":
                    tool_results += 1
            if _log_tool_details():
                print(f"  [MCP] {agent_name}: tools={len(tools)}, calls={tool_calls}, results={tool_results}")

            if not messages_out:
                return ""
            return _message_text(messages_out[-1]).strip()


async def call_llm_with_mcp_async_detailed(
    system_prompt: str,
    user_prompt: str,
    server_type: str,
    images_base64: Optional[List[str]] = None,
    agent_name: str = "mcp_agent",
    temperature: float = 0.4,
) -> tuple[str, dict[str, Any]]:
    resolved_server = _agent_server_type(agent_name, server_type)
    trace = _init_call_trace(agent_name, server_type, resolved_server, temperature)
    started = time.perf_counter()

    if not resolved_server:
        fallback_started = time.perf_counter()
        text = _fallback_call_llm(
            system_prompt,
            user_prompt,
            images_base64,
            agent_name,
            temperature,
            "MCP 鏈惎鐢ㄦ垨璇?Agent 宸茬鐢?MCP",
        )
        fallback_elapsed = round(time.perf_counter() - fallback_started, 3)
        total_elapsed = round(time.perf_counter() - started, 3)
        trace.update(
            {
                "status": "mcp_disabled",
                "path": "direct",
                "mcp_elapsed_seconds": 0.0,
                "fallback_elapsed_seconds": fallback_elapsed,
                "elapsed_seconds": total_elapsed,
            }
        )
        print(
            f"  [MCP] {agent_name}: direct-only completed in {fallback_elapsed:.1f}s "
            f"(total {total_elapsed:.1f}s)"
        )
        return text, trace

    try:
        text = await asyncio.wait_for(
            _invoke_mcp_agent_async(
                system_prompt,
                user_prompt,
                resolved_server,
                images_base64,
                agent_name,
                temperature,
            ),
            timeout=_mcp_timeout_seconds(),
        )
        total_elapsed = round(time.perf_counter() - started, 3)
        trace.update(
            {
                "status": "mcp_success",
                "path": "mcp",
                "mcp_elapsed_seconds": total_elapsed,
                "elapsed_seconds": total_elapsed,
            }
        )
        print(f"  [MCP] {agent_name}: completed in {total_elapsed:.1f}s")
        return text, trace
    except Exception as exc:
        mcp_elapsed = round(time.perf_counter() - started, 3)
        fallback_started = time.perf_counter()
        text = _fallback_call_llm(
            system_prompt,
            user_prompt,
            images_base64,
            agent_name,
            temperature,
            f"MCP {resolved_server} 璋冪敤澶辫触鎴栬秴鏃?({type(exc).__name__}, {mcp_elapsed:.1f}s): {exc}",
        )
        fallback_elapsed = round(time.perf_counter() - fallback_started, 3)
        total_elapsed = round(time.perf_counter() - started, 3)
        trace.update(
            {
                "status": "mcp_fallback",
                "path": "mcp_then_direct",
                "mcp_error_type": type(exc).__name__,
                "mcp_error": str(exc)[:500],
                "mcp_elapsed_seconds": mcp_elapsed,
                "fallback_elapsed_seconds": fallback_elapsed,
                "elapsed_seconds": total_elapsed,
            }
        )
        print(
            f"  [MCP] {agent_name}: fallback direct completed in {fallback_elapsed:.1f}s "
            f"(total {total_elapsed:.1f}s)"
        )
        return text, trace


async def call_llm_with_mcp_async(
    system_prompt: str,
    user_prompt: str,
    server_type: str,
    images_base64: Optional[List[str]] = None,
    agent_name: str = "mcp_agent",
    temperature: float = 0.4,
) -> str:
    resolved_server = _agent_server_type(agent_name, server_type)
    if not resolved_server:
        return _fallback_call_llm(
            system_prompt,
            user_prompt,
            images_base64,
            agent_name,
            temperature,
            "MCP 未启用或该 Agent 已禁用 MCP",
        )

    started = time.time()
    try:
        return await asyncio.wait_for(
            _invoke_mcp_agent_async(
                system_prompt,
                user_prompt,
                resolved_server,
                images_base64,
                agent_name,
                temperature,
            ),
            timeout=_mcp_timeout_seconds(),
        )
    except Exception as exc:
        elapsed = time.time() - started
        return _fallback_call_llm(
            system_prompt,
            user_prompt,
            images_base64,
            agent_name,
            temperature,
            f"MCP {resolved_server} 调用失败或超时 ({type(exc).__name__}, {elapsed:.1f}s): {exc}",
        )


def call_llm_with_mcp(
    system_prompt: str,
    user_prompt: str,
    server_type: str,
    images_base64: Optional[List[str]] = None,
    agent_name: str = "mcp_agent",
    temperature: float = 0.4,
) -> str:
    """Synchronous wrapper used by the existing LangGraph nodes.

    支持三种调用上下文：
    1. 纯同步线程（最常见，LangGraph 节点在 ThreadPool 中跑）— 直接 asyncio.run()
    2. 已有正在运行的 event loop（如某些异步宿主环境）— 用 nest_asyncio 嵌套
    3. 该线程曾经设置过空闲 loop — 复用或新建
    """

    def _make_coro():
        # 每次调用都要新建 coroutine，以防第一次 run 失败后 coroutine 被消耗
        return call_llm_with_mcp_async(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            server_type=server_type,
            images_base64=images_base64,
            agent_name=agent_name,
            temperature=temperature,
        )

    # 优先路径：当前线程没有运行中的 event loop，asyncio.run() 最安全
    try:
        running_loop = asyncio.get_running_loop()
    except RuntimeError:
        running_loop = None

    if running_loop is None:
        try:
            return asyncio.run(_make_coro())
        except RuntimeError as exc:
            # 某些线程可能持有 close 过的 loop，降级走 new_event_loop 路径
            if "already running" not in str(exc).lower():
                loop = asyncio.new_event_loop()
                try:
                    asyncio.set_event_loop(loop)
                    return loop.run_until_complete(_make_coro())
                finally:
                    try:
                        loop.close()
                    except Exception:
                        pass
                    asyncio.set_event_loop(None)
            raise

    # 回退路径：当前线程已有运行中的 loop（例如 FastAPI 的主协程）
    try:
        import nest_asyncio

        nest_asyncio.apply(running_loop)
    except ImportError:
        raise RuntimeError(
            "当前线程已有运行中的 event loop，无法同步调用 MCP。请安装 nest_asyncio 或改为在独立线程中调用。"
        )
    except Exception as exc:
        print(f"  [MCP] WARN: nest_asyncio.apply 失败: {exc}")
    return running_loop.run_until_complete(_make_coro())


def call_llm_with_mcp_detailed(
    system_prompt: str,
    user_prompt: str,
    server_type: str,
    images_base64: Optional[List[str]] = None,
    agent_name: str = "mcp_agent",
    temperature: float = 0.4,
) -> tuple[str, dict[str, Any]]:
    """Sync wrapper that also returns transport/runtime metadata."""

    def _make_coro():
        return call_llm_with_mcp_async_detailed(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            server_type=server_type,
            images_base64=images_base64,
            agent_name=agent_name,
            temperature=temperature,
        )

    try:
        running_loop = asyncio.get_running_loop()
    except RuntimeError:
        running_loop = None

    if running_loop is None:
        try:
            return asyncio.run(_make_coro())
        except RuntimeError as exc:
            if "already running" not in str(exc).lower():
                loop = asyncio.new_event_loop()
                try:
                    asyncio.set_event_loop(loop)
                    return loop.run_until_complete(_make_coro())
                finally:
                    try:
                        loop.close()
                    except Exception:
                        pass
                    asyncio.set_event_loop(None)
            raise

    try:
        import nest_asyncio

        nest_asyncio.apply(running_loop)
    except ImportError:
        raise RuntimeError(
            "A running event loop already exists in this thread, so MCP cannot be called synchronously. Install nest_asyncio or call this helper from a separate thread."
        )
    except Exception as exc:
        print(f"  [MCP] WARN: nest_asyncio.apply 澶辫触: {exc}")
    return running_loop.run_until_complete(_make_coro())
