"""
工具包 — 每个工具是一个独立模块。

添加新工具的步骤:
  1. 创建 tools/xxx.py
  2. 定义 SCHEMA (dict) 和 execute(args) -> str
  3. 在下面的 _TOOL_MODULES 中注册

导出:
  SCHEMAS  — 给 Anthropic API 的纯 schema 列表
  execute() — 根据工具名分发执行
"""

from . import powershell

# ── 注册表: 在此注册所有工具模块 ──────────────────────────
_TOOL_MODULES = [powershell]

# ── 构建导出 ────────────────────────────────────────────────

SCHEMAS = [m.SCHEMA for m in _TOOL_MODULES]

_EXECUTORS = {m.SCHEMA["name"]: m.execute for m in _TOOL_MODULES}


def execute(name: str, args: dict) -> str:
    """根据工具名分发到对应执行函数"""
    executor = _EXECUTORS.get(name)
    if not executor:
        return f"未知工具: {name}"
    return executor(args)
