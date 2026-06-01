"""
内置日志钩子 — 为各个生命周期事件提供日志输出。

每个回调签名与 trigger_hooks 传递的 kwargs 匹配，
返回值均为 None（不拦截流程）。
"""

import logging
import json

from .hook import register_hook

logger = logging.getLogger("agent")


# ── 辅助函数 ──────────────────────────────────────────────

def _dump(obj) -> str:
    if obj is None:
        return "<None>"
    if hasattr(obj, "content"):
        return _dump_message(obj)
    if isinstance(obj, (dict, list)):
        return json.dumps(obj, ensure_ascii=False, indent=2, default=str)
    return str(obj)


def _dump_message(msg) -> str:
    blocks = []
    for block in msg.content:
        if block.type == "text":
            blocks.append(f"[text] {block.text}")
        elif block.type == "tool_use":
            blocks.append(
                f"[tool_use] {block.name}("
                f"{json.dumps(dict(block.input), ensure_ascii=False)})"
            )
    return "\n".join(blocks)


# ── 钩子回调 ──────────────────────────────────────────────

@register_hook("PreModelCall")
def on_model_start(state=None, system=None, model=None,
                   messages=None, **kw):
    msgs = []
    for m in (messages or []):
        role = m.get("role", "?")
        content = m.get("content", "")
        if isinstance(content, str):
            msgs.append(f"  [{role}] {content}")
        elif isinstance(content, list):
            for block in content:
                if isinstance(block, dict):
                    t = block.get("type", "?")
                    if t == "text":
                        msgs.append(f"  [{role} text] {block.get('text', '')}")
                    elif t == "tool_use":
                        msgs.append(
                            f"  [{role} tool_use] {block.get('name')}("
                            f"{json.dumps(block.get('input', {}), ensure_ascii=False)})"
                        )
                    elif t == "tool_result":
                        msgs.append(
                            f"  [{role} tool_result] "
                            f"{block.get('content', '')[:500]}"
                        )
                else:
                    msgs.append(f"  [{role} {block.type}] ...")

    logger.info(
        "▶ Model Call | model=%s | messages=%d\n"
        "  system: %s\n"
        "  messages:\n%s",
        model,
        len(messages or []),
        (system or "")[:500],
        "\n".join(msgs) if msgs else "  (empty)",
    )


@register_hook("PostModelCall")
def on_model_end(state=None, system=None, model=None,
                 messages=None, response=None, **kw):
    tool_uses = []
    for block in (response.content if response else []):
        if block.type == "tool_use":
            tool_uses.append(
                f"{block.name}("
                f"{json.dumps(dict(block.input), ensure_ascii=False)})"
            )

    usage = ""
    if response and response.usage:
        usage = (f"input={response.usage.input_tokens} "
                 f"output={response.usage.output_tokens}")

    logger.info(
        "◀ Model Response | stop_reason=%s | %s\n%s",
        response.stop_reason if response else "?",
        usage,
        _dump_message(response) if response else "",
    )


@register_hook("PreToolUse")
def on_tool_start(state=None, tool_name=None, tool_args=None, **kw):
    logger.info(
        "🔧 Tool Call | %s(%s)",
        tool_name,
        json.dumps(tool_args, ensure_ascii=False),
    )


@register_hook("PostToolUse")
def on_tool_end(state=None, tool_name=None, tool_args=None,
                result=None, **kw):
    logger.info(
        "🔧 Tool Result | %s → %s",
        tool_name,
        _dump(result)[:2000],
    )


@register_hook("Stop")
def on_stop(state=None, **kw):
    logger.info("■ Agent Stop | messages=%d",
                len(state.get("messages", [])) if state else 0)
