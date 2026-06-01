# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Environment

- Python 3.13 with a virtual environment at `.venv/`
- Run: `.venv/Scripts/streamlit run app.py`

## Key dependencies

- **anthropic 0.105.2** — Anthropic/Claude API SDK
- **streamlit** — web app framework (for later UI)
- **pandas / numpy / pyarrow** — data processing

## Architecture

### File structure

```
agent_loop.py   — Agent loop 逻辑 + state 管理（核心）
app.py          — Streamlit Web UI（入口）
log_config.py   — 日志配置（dictConfig，只做日志）
hooks/          — 生命周期钩子
  __init__.py   — 导入即自动注册内置钩子，re-export 核心 API
  hook.py       — HOOKS 注册表 + register_hook/trigger_hooks
  logging_hooks.py — 内置日志钩子
tools/          — 工具包
  __init__.py   — 注册表 + 导出 SCHEMAS 和 execute()
  powershell.py — PowerShell 工具 (schema + executor)
```

### 启动顺序 (`app.py`)

```python
import log_config   # 1. 配置日志基础设施
import hooks        # 2. 钩子系统（导入时自动注册内置钩子）
```

### Logging (`log_config.py`)

纯 dictConfig，不管 hook。项目只用一个 `"agent"` logger：
- 控制台输出（DEBUG 级别）
- `agent.log` 文件（DEBUG 级别）

各模块通过 `logging.getLogger("agent")` 获取。

### Hooks (`hooks/`)

六个生命周期事件 + 内置日志回调。`import hooks` 时自动注册内置钩子。
要新增内置钩子（如 metrics），在 `logging_hooks.py` 中添加 `@register_hook` 装饰器即可。

```python
from hooks import register_hook

@register_hook("PreToolUse")
def my_callback(**kw):
    ...
```

### Agent Loop (`agent_loop.py`)

`agent_loop(state, on_text=None)` 是核心：接受 state dict，读写 `state["messages"]`，返回 state。
始终流式输出；配合 `on_text` 回调实现打字机效果，不传 `on_text` 则静默运行。

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
