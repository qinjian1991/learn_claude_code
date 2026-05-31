# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Environment

- Python 3.13 with a virtual environment at `.venv/`
- Run: `.venv/Scripts/python main.py [optional query]`

## Key dependencies

- **anthropic 0.105.2** — Anthropic/Claude API SDK
- **streamlit** — web app framework (for later UI)
- **pandas / numpy / pyarrow** — data processing

## Architecture

### File structure

```
main.py          — Agent loop 逻辑 + state 管理 + CLI 入口
app.py           — Streamlit Web UI
tools/           — 工具包（会频繁修改）
  __init__.py    — 注册表 + 导出 SCHEMAS 和 execute()
  powershell.py  — PowerShell 工具 (schema + executor)
```

### Agent Loop (`main.py`)

`agent_loop(state, verbose=True, stream=True)` 是核心：接受 state dict，读写 `state["messages"]`，返回 state。
默认流式输出；`stream=False` 切回非流式，`verbose=False` 静默（供 UI 调用）。

```
User msg → send to Claude → response
  ├── text only → done
  └── tool_use → tools.execute(name, args) → append tool_result → loop
```

调用方拥有 `state["messages"]` 的所有权 — 多轮对话时只需继续追加 user 消息再调用 `agent_loop()`。

### Streamlit UI (`app.py`)

`streamlit run app.py` 启动 Web 界面。通过 `st.session_state` 持久化 state，侧边栏可调整 model / max_tokens / system prompt。

### Tools package (`tools/`)

每个工具是一个独立模块，导出 `SCHEMA` (dict) 和 `execute(args) -> str`。

添加新工具只需两步：
1. 创建 `tools/xxx.py`，定义 `SCHEMA` 和 `execute(args)`
2. 在 `tools/__init__.py` 的 `_TOOL_MODULES` 中添加 `from . import xxx` 并注册

`__init__.py` 自动从各模块收集 SCHEMAS 和构建 name→execute 映射。

Current tools:
- `powershell` — 真实执行 PowerShell 命令 (subprocess, 30s timeout)

### `sys.stdout.reconfigure(encoding="utf-8")` 

Windows GBK 终端无法输出模型返回的 Unicode 内容，因此在入口处强制 UTF-8。
