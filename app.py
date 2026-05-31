"""
Streamlit UI for the Agent Loop — 流式打字机效果

Run: .venv/Scripts/streamlit run app.py
"""

import streamlit as st
from main import make_state, agent_loop

st.set_page_config(page_title="Agent Demo", page_icon="🤖")

st.title("Agent Loop Demo")
st.caption("Streamlit UI + streaming typewriter effect")

# ── 初始化 session state ──────────────────────────────────
if "state" not in st.session_state:
    st.session_state.state = make_state()

state = st.session_state.state

# ── 侧边栏 ────────────────────────────────────────────────
with st.sidebar:
    st.subheader("Settings")
    state["model"] = st.selectbox(
        "Model",
        ["claude-sonnet-4-6", "claude-haiku-4-5", "claude-opus-4-8"],
        index=0,
    )
    state["max_tokens"] = st.slider("Max tokens", 256, 4096, 1024, 256)
    state["system"] = st.text_area("System prompt", state["system"], height=120)

    st.divider()
    if st.button("Reset conversation"):
        st.session_state.state = make_state()
        st.rerun()

    st.caption(f"Messages: {len(state['messages'])}")

# ── 渲染对话历史 ──────────────────────────────────────────
for msg in state["messages"]:
    if msg["role"] == "user":
        content = msg["content"]
        if isinstance(content, list):
            continue  # tool_result，跳过
        with st.chat_message("user"):
            st.write(content)

    elif msg["role"] == "assistant":
        text_parts = []
        tool_uses = []

        for block in msg["content"]:
            if block.type == "text":
                text_parts.append(block.text)
            elif block.type == "tool_use":
                tool_uses.append(block)

        with st.chat_message("assistant"):
            if text_parts:
                st.write("".join(text_parts))
            for tool in tool_uses:
                with st.expander(f"🔧 {tool.name}", expanded=False):
                    st.json({"name": tool.name, "input": dict(tool.input)})

# ── 输入框 ────────────────────────────────────────────────
if prompt := st.chat_input("Ask something..."):
    state["messages"].append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.write(prompt)

    # 收集流式文本块，运行 Agent
    chunks: list[str] = []
    agent_loop(state, verbose=False, on_text=chunks.append)

    # 打字机效果呈现文本
    with st.chat_message("assistant"):
        st.write_stream(chunks)

    st.rerun()
