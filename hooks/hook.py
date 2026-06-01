"""
Hook 核心定义 — 独立于 state 的生命周期钩子系统。

事件:
  UserPromptSubmit, PreModelCall, PostModelCall,
  PreToolUse, PostToolUse, Stop

使用:
    from hooks.hook import register_hook, trigger_hooks

    # 直接注册
    register_hook("PreToolUse", my_callback)

    # 装饰器注册
    @register_hook("PreToolUse")
    def my_callback(**kw):
        ...
"""

import logging

logger = logging.getLogger("agent")

# ── 事件注册表 ──────────────────────────────────────────────

HOOKS = {
    "UserPromptSubmit": [],
    "PreModelCall": [],
    "PostModelCall": [],
    "PreToolUse": [],
    "PostToolUse": [],
    "Stop": [],
}


def register_hook(event: str, callback=None):
    """
    注册一个钩子回调。两种用法::

        register_hook("PreToolUse", my_func)   # 直接注册
        @register_hook("PreToolUse")           # 装饰器注册
        def my_func(**kw): ...
    """
    if callback is not None:
        HOOKS[event].append(callback)
        return callback

    def decorator(cb):
        HOOKS[event].append(cb)
        return cb
    return decorator


def trigger_hooks(event: str, *args, **kwargs):
    """
    触发指定事件的所有回调。任一回调返回非 None 时立即返回该值（短路）。
    全部返回 None 时返回 None（表示继续正常流程）。
    """
    for callback in HOOKS[event]:
        result = callback(*args, **kwargs)
        if result is not None:
            return result
    return None
