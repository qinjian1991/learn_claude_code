"""
Agent Loop — 核心循环逻辑

流程:
  用户输入 → 发送给 Claude → 收到响应
    ├── 纯文本 → 输出给用户，结束
    └── 工具调用 → 执行工具 → 把结果发给 Claude → 循环

State 模式: agent_loop 接受 state dict，在其中读写 messages，
从而与调用方解耦 —— 调用方拥有对话历史的所有权。
"""

import sys
import time

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from anthropic import (
    Anthropic,
    APIError,
    APIConnectionError,
    APITimeoutError,
    AuthenticationError,
    BadRequestError,
    InternalServerError,
    RateLimitError,
)
from anthropic._exceptions import OverloadedError, ServiceUnavailableError

from hooks import trigger_hooks
import tools  # 工具模块：提供 SCHEMAS 和 execute()
from context_compact import context_compact, reactive_compact

# ── 全局配置 ────────────────────────────────────────────────
client = Anthropic()
DEFAULT_MODEL = "claude-sonnet-4-6"
DEFAULT_SYSTEM = "你是一个有用的助手。当需要实时数据或计算时，使用工具。"

# ── 重试配置 ────────────────────────────────────────────────
MAX_RETRIES = 3
RETRY_BASE_DELAY = 2.0  # 秒，指数退避: 2, 4, 8

# 可重试的异常类型
RETRYABLE_ERRORS = (
    APIConnectionError,   # 网络问题
    APITimeoutError,      # 超时
    RateLimitError,       # 速率限制
    OverloadedError,      # 服务器过载 (529)
    InternalServerError,  # 服务端 500
    ServiceUnavailableError,  # 服务不可用 (503)
)

# ── 默认 state 工厂 ────────────────────────────────────────
def make_state(**overrides) -> dict:
    """创建一个新的 state，调用方可以覆盖任意字段"""
    state = {
        "messages": [],
        "system": DEFAULT_SYSTEM,
        "tools": tools.SCHEMAS,
        "model": DEFAULT_MODEL,
        "max_tokens": 1024,
    }
    state.update(overrides)
    return state


# ── Agent Loop ──────────────────────────────────────────────
def agent_loop(state: dict, *, on_text=None) -> dict:
    """
    以 state 为上下文的 Agent 循环（始终流式）。

    state.messages 由调用方构建和拥有；返回更新后的 state。

    on_text(str) — 可选回调，每收到一个文本块就调用（供调用方实现打
    字机效果等场景使用）。不传则静默运行。
    """
    if trigger_hooks("UserPromptSubmit", state=state) is not None:
        return state

    messages = state["messages"]

    context_compact(state)

    while True:
        # ── 调用大模型前 hook ────────────────────────────
        trigger_hooks("PreModelCall", state=state,
                      system=state["system"], model=state["model"],
                      messages=messages)

        # ── 流式调用（带重试）───────────────────────────
        final_message = None
        for attempt in range(MAX_RETRIES + 1):
            try:
                with client.messages.stream(
                    model=state["model"],
                    max_tokens=state["max_tokens"],
                    system=state["system"],
                    tools=state["tools"],
                    messages=messages,
                ) as stream_response:
                    for text in stream_response.text_stream:
                        if on_text:
                            on_text(text)
                    final_message = stream_response.get_final_message()
                break  # 成功，跳出重试循环

            except RETRYABLE_ERRORS as e:
                if attempt < MAX_RETRIES:
                    delay = RETRY_BASE_DELAY * (2 ** attempt)
                    notice = (
                        f"\n[Retry {attempt + 1}/{MAX_RETRIES}] "
                        f"{type(e).__name__}: {e}. "
                        f"Retrying in {delay:.0f}s...\n"
                    )
                    if on_text:
                        on_text(notice)
                    time.sleep(delay)
                else:
                    error_msg = (
                        f"[Error] API call failed after "
                        f"{MAX_RETRIES} retries: {type(e).__name__}: {e}"
                    )
                    if on_text:
                        on_text(f"\n{error_msg}\n")
                    trigger_hooks("Stop", state=state)
                    messages.append({
                        "role": "user",
                        "content": error_msg,
                    })
                    return state

            except BadRequestError as e:
                # 检测 context-length 错误 → reactive_compact 后重试
                error_str = str(e).lower()
                ctx_keywords = (
                    "prompt is too long", "context_length_exceeded",
                    "too many tokens", "maximum context",
                    "tokens exceeds", "token limit",
                )
                if any(kw in error_str for kw in ctx_keywords):
                    if not state.get("_reactive_compacted"):
                        state["_reactive_compacted"] = True
                        messages[:] = reactive_compact(messages)
                        if on_text:
                            on_text(
                                "\n[Context limit exceeded — "
                                "reactively compacting history...]\n"
                            )
                        continue  # 压缩后重试（消耗一次 attempt）
                # 非 context-length 或已压缩过 → 致命
                error_msg = f"[Error] {type(e).__name__}: {e}"
                if on_text:
                    on_text(f"\n{error_msg}\n")
                trigger_hooks("Stop", state=state)
                messages.append({"role": "user", "content": error_msg})
                return state

            except AuthenticationError as e:
                # 不可重试：认证失败
                error_msg = f"[Error] {type(e).__name__}: {e}"
                if on_text:
                    on_text(f"\n{error_msg}\n")
                trigger_hooks("Stop", state=state)
                messages.append({"role": "user", "content": error_msg})
                return state

            except APIError as e:
                # 未预期的 API 错误 —— 保守处理，不重试
                error_msg = f"[Error] Unexpected API error: {type(e).__name__}: {e}"
                if on_text:
                    on_text(f"\n{error_msg}\n")
                trigger_hooks("Stop", state=state)
                messages.append({
                    "role": "user",
                    "content": error_msg,
                })
                return state

        # ── 调用大模型后 hook ────────────────────────────
        trigger_hooks("PostModelCall", state=state,
                      system=state["system"], model=state["model"],
                      messages=messages, response=final_message)

        # ── 记录 assistant 响应 ───────────────────────────
        messages.append({
            "role": "assistant",
            "content": final_message.content,
        })

        # ── 解析 tool_use ─────────────────────────────────
        tool_uses = []
        for block in final_message.content:
            if block.type == "tool_use":
                tool_uses.append(block)

        if not tool_uses:
            trigger_hooks("Stop", state=state)
            return state

        # ── 执行工具 ───────────────────────────────────────
        tool_results = []
        for tool in tool_uses:
            tool_name = tool.name
            tool_args = dict(tool.input)

            result = trigger_hooks("PreToolUse", state=state,
                                  tool_name=tool_name, tool_args=tool_args)

            if result is None:  # 没有 hook 拦截，正常执行
                result = tools.execute(tool_name, tool_args)

            trigger_hooks("PostToolUse", state=state,
                          tool_name=tool_name, tool_args=tool_args, result=result)

            tool_results.append({
                "type": "tool_result",
                "tool_use_id": tool.id,
                "content": result,
            })

        messages.append({
            "role": "user",
            "content": tool_results,
        })
        # 循环继续
