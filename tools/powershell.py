"""PowerShell 工具 — 真实执行 PowerShell 命令"""

import subprocess

SCHEMA = {
    "name": "powershell",
    "description": (
        "执行 PowerShell 命令并返回结果。"
        "适合查看文件、进程、系统信息等只读操作。"
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "command": {
                "type": "string",
                "description": "PowerShell 命令，如 'Get-Process | Select -First 5'"
            }
        },
        "required": ["command"],
    },
}


def execute(args: dict) -> str:
    command = args["command"]
    try:
        result = subprocess.run(
            ["powershell.exe", "-NoProfile", "-Command", command],
            capture_output=True,
            text=True,
            timeout=30,
        )
        output = result.stdout.strip()
        if result.stderr.strip():
            output += "\n[stderr]\n" + result.stderr.strip()
        return output if output else "(无输出)"
    except subprocess.TimeoutExpired:
        return "错误: 命令执行超时 (30s)"
    except FileNotFoundError:
        return "错误: 找不到 powershell.exe"
    except Exception as e:
        return f"执行错误: {e}"
