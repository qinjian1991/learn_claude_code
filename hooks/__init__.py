"""
Hook 包 — 导入即自动注册内置钩子。

使用:
    import hooks  # 自动注册内置钩子（日志等）

    from hooks import register_hook, trigger_hooks

    @register_hook("PreToolUse")
    def my_callback(**kw):
        ...
"""

import logging

from .hook import HOOKS, register_hook, trigger_hooks
from . import logging_hooks  # noqa: F811 — 副作用导入：@register_hook 装饰器在 import 时自动注册

__all__ = ["HOOKS", "register_hook", "trigger_hooks"]

logger = logging.getLogger("agent")
logger.info("Hooks initialized (built-in: logging)")
