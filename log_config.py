"""
日志配置 — 项目日志的统一入口，使用 Python logging dictConfig。

导入即启用:
    import log_config

日志输出:
  - 控制台 (stdout)        — DEBUG 及以上
  - logs/agent.log 文件     — DEBUG 及以上，完整时间戳

获取 logger:
    import logging
    logger = logging.getLogger("agent")
"""

import logging
import logging.config
import sys
from pathlib import Path

_LOG_DIR = Path("logs")
_LOG_DIR.mkdir(exist_ok=True)

LOGGING_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,

    "formatters": {
        "console": {
            "format": "[%(asctime)s] %(levelname)-5s agent: %(message)s",
            "datefmt": "%H:%M:%S",
        },
        "file": {
            "format": "%(asctime)s %(levelname)-5s agent: %(message)s",
            "datefmt": "%Y-%m-%d %H:%M:%S",
        },
    },

    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "stream": sys.stdout,
            "formatter": "console",
            "level": "DEBUG",
        },
        "file": {
            "class": "logging.FileHandler",
            "filename": str((_LOG_DIR / "agent.log").absolute()),
            "encoding": "utf-8",
            "formatter": "file",
            "level": "DEBUG",
        },
    },

    "loggers": {
        "agent": {
            "handlers": ["console", "file"],
            "level": "DEBUG",
            "propagate": False,
        },
    },
}

logging.config.dictConfig(LOGGING_CONFIG)
