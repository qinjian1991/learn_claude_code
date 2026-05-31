"""
最小 Agent Loop — 学习 AI Agent 的第一步

核心流程:
  用户输入 → 发送给 Claude → 收到响应
    ├── 纯文本 → 输出给用户，结束
    └── 工具调用 → 执行工具 → 把结果发给 Claude → 循环

State 模式: agent_loop 接受 state dict，在其中读写 messages，
从而与调用方解耦 —— 调用方拥有对话历史的所有权。

工具定义在 tools.py 中，main.py 只负责 Agent 循环逻辑。
"""

import json
import sys

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from anthropic import Anthropic

import tools  # 工具模块：提供 SCHEMAS 和 execute()

# ── 全局配置 ────────────────────────────────────────────────
client = Anthropic()
DEFAULT_MODEL = "claude-sonnet-4-6"
DEFAULT_SYSTEM = "你是一个有用的助手。当需要实时数据或计算时，使用工具。"


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
def agent_loop(state: dict, verbose: bool = True, *, on_text=None) -> dict:
    """
    以 state 为上下文的 Agent 循环（始终流式）。

    state.messages 由调用方构建和拥有；返回更新后的 state。

    on_text(str) — 可选回调，每收到一个文本块就调用（供 Streamlit 打
    字机效果等场景使用）。verbose=False + on_text 配合使用。

    返回更新后的 state。verbose=False 时静默（供 UI 使用）。
    """
    messages = state["messages"]

    while True:
        # ── 流式调用 ──────────────────────────────────────
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
                elif verbose:
                    print(text, end="", flush=True)

            if verbose:
                print()

            final_message = stream_response.get_final_message()

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
            return state

        # ── 执行工具 ───────────────────────────────────────
        tool_results = []
        for tool in tool_uses:
            tool_args = dict(tool.input)
            if verbose:
                print(f"[Tool] {tool.name}({json.dumps(tool_args, ensure_ascii=False)})")
            result = tools.execute(tool.name, tool_args)
            if verbose:
                print(f"[Result] {result}\n")

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


# ── 入口 ────────────────────────────────────────────────────
if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        user_msg = " ".join(sys.argv[1:])
        state = make_state(messages=[{"role": "user", "content": user_msg}])
        print(f"\n{'='*50}")
        print(f"[User] {user_msg}")
        print("=" * 50)
        agent_loop(state)
        print("-" * 50)
    else:
        print("\n=== Minimal Agent Loop Demo ===")
        print("Type a message, or 'quit' to exit\n")
        state = make_state()

        while True:
            try:
                user_input = input("> ").strip()
                if user_input.lower() in ("quit", "exit", "q"):
                    print("Bye!")
                    break
                if not user_input:
                    continue

                state["messages"].append({"role": "user", "content": user_input})
                print(f"\n{'='*50}")
                print(f"[User] {user_input}")
                print("=" * 50)

                agent_loop(state)

                print("-" * 50)
                print(f"[messages: {len(state['messages'])}]")
            except KeyboardInterrupt:
                print("\nBye!")
                break
