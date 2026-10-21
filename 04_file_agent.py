"""
========================================================================
第 4 个 Agent：真实世界工具（文件读写 + 沙箱安全）
========================================================================

对应第 4 课。这一版给 agent 三个能操作真实文件的工具：
    list_files  -> 列目录
    read_file   -> 读文件
    write_file  -> 写文件

并引入一个重要的工程概念【沙箱 (Sandbox)】：
    限定 agent 只能在 workspace 目录内活动，
    任何试图访问 workspace 外面的路径都会被拒绝。
    这是真实 agent 产品的必备安全设计。

试试对它说：
    「把当前目录下所有 txt 文件读出来，总结成一份 summary.md」
观察它如何自己 list -> read -> 思考 -> write，多步完成任务。
"""

import json
import os
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

BASE_URL = os.getenv("LLM_BASE_URL")
API_KEY = os.getenv("LLM_API_KEY")
MODEL = os.getenv("LLM_MODEL")

if not all([BASE_URL, API_KEY, MODEL]):
    raise SystemExit("❌ 配置缺失！请检查 .env 文件。")

client = OpenAI(base_url=BASE_URL, api_key=API_KEY)


# ======================================================================
# 🛡️ 沙箱：所有文件操作都被限制在这个目录内
# ======================================================================
# WORKSPACE 是 agent 唯一被允许操作的根目录（本脚本同级的 workspace 文件夹）。
WORKSPACE = (Path(__file__).parent / "workspace").resolve()
WORKSPACE.mkdir(exist_ok=True)  # 不存在就自动创建


def _safe_path(relative_path: str) -> Path:
    """
    把用户/模型给的相对路径，解析成 workspace 内的绝对路径，
    并校验它确实落在 workspace 里面。否则抛异常，阻止越界访问。

    这就是「沙箱」的核心：一道路径安全闸门。
    """
    # 把相对路径拼到 workspace 下，再 resolve 成绝对路径（会处理掉 .. 等花招）
    target = (WORKSPACE / relative_path).resolve()

    # 关键校验：解析后的路径必须仍然在 WORKSPACE 之内
    if WORKSPACE not in target.parents and target != WORKSPACE:
        raise ValueError(f"🚫 拒绝访问：'{relative_path}' 超出了沙箱允许的范围")
    return target


# ======================================================================
# 工具定义
# ======================================================================

def list_files(directory: str = ".") -> str:
    """列出 workspace 下某个目录里的文件和子目录。"""
    try:
        target = _safe_path(directory)
        if not target.exists():
            return f"目录不存在: {directory}"
        items = []
        for p in sorted(target.iterdir()):
            kind = "📁" if p.is_dir() else "📄"
            items.append(f"{kind} {p.name}")
        return "\n".join(items) if items else "(空目录)"
    except Exception as e:
        return f"出错: {e}"


def read_file(path: str) -> str:
    """读取 workspace 下某个文件的文本内容。"""
    try:
        target = _safe_path(path)
        if not target.exists():
            return f"文件不存在: {path}"
        return target.read_text(encoding="utf-8")
    except Exception as e:
        return f"出错: {e}"


def write_file(path: str, content: str) -> str:
    """把文本内容写入 workspace 下的某个文件（会覆盖已有文件）。"""
    try:
        target = _safe_path(path)
        target.write_text(content, encoding="utf-8")
        return f"✅ 已写入 {path}（共 {len(content)} 个字符）"
    except Exception as e:
        return f"出错: {e}"


AVAILABLE_TOOLS = {
    "list_files": list_files,
    "read_file": read_file,
    "write_file": write_file,
}

TOOLS_SCHEMA = [
    {
        "type": "function",
        "function": {
            "name": "list_files",
            "description": "列出工作目录下某个文件夹里的所有文件和子目录。",
            "parameters": {
                "type": "object",
                "properties": {
                    "directory": {
                        "type": "string",
                        "description": "相对工作目录的路径，默认 '.' 表示工作目录根。",
                    }
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "读取某个文件的文本内容。",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "要读取的文件路径（相对工作目录）。",
                    }
                },
                "required": ["path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "write_file",
            "description": "把内容写入某个文件（若文件已存在会被覆盖）。",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "要写入的文件路径（相对工作目录）。",
                    },
                    "content": {
                        "type": "string",
                        "description": "要写入的文本内容。",
                    },
                },
                "required": ["path", "content"],
            },
        },
    },
]


# ======================================================================
# Agent Loop（和第 3 课一致：多步 + 步数上限 + 轮次打印）
# ======================================================================

def run_agent(messages: list, max_steps: int = 12) -> str:
    for step in range(1, max_steps + 1):
        print(f"\n   ┌─ 第 {step} 步 ───────────────────────")

        response = client.chat.completions.create(
            model=MODEL,
            messages=messages,
            tools=TOOLS_SCHEMA,
        )
        msg = response.choices[0].message

        if msg.content:
            print(f"   │ 💭 思考: {msg.content}")

        if not msg.tool_calls:
            print(f"   └─ ✅ 第 {step} 步给出最终答案，循环结束")
            messages.append({"role": "assistant", "content": msg.content})
            return msg.content

        messages.append(msg)

        for tool_call in msg.tool_calls:
            tool_name = tool_call.function.name
            tool_args = json.loads(tool_call.function.arguments)

            # 写文件的内容可能很长，打印时截断一下，避免刷屏
            preview = {
                k: (v[:40] + "...") if isinstance(v, str) and len(v) > 40 else v
                for k, v in tool_args.items()
            }
            print(f"   │ 🔧 调用: {tool_name}({preview})")

            func = AVAILABLE_TOOLS.get(tool_name)
            result = func(**tool_args) if func else f"未知工具 {tool_name}"

            result_preview = result if len(result) <= 100 else result[:100] + "..."
            print(f"   │ 📥 结果: {result_preview}")

            messages.append({
                "role": "tool",
                "tool_call_id": tool_call.id,
                "content": str(result),
            })

        print(f"   └─ 第 {step} 步完成，继续...")

    return "⚠️ 达到最大步数上限，已强制停止。"


def main():
    print("=" * 60)
    print("🤖 文件操作 Agent 已启动（带沙箱保护）")
    print(f"   沙箱目录: {WORKSPACE}")
    print("   它只能在上面这个目录里读写文件。")
    print("   试试：『把当前目录下所有 txt 文件读出来，总结成一份 summary.md』")
    print("   输入 quit 退出。")
    print("=" * 60)

    messages = [
        {
            "role": "system",
            "content": (
                "你是一个能操作文件的中文助手。你可以列目录、读文件、写文件，"
                "但只能在被允许的工作目录内操作。"
                "完成多步文件任务时，请一步步来：先了解有哪些文件，"
                "再读取需要的内容，最后写入结果。"
            ),
        }
    ]

    while True:
        user_input = input("\n你: ").strip()
        if user_input.lower() in ("quit", "exit", "q"):
            print("👋 再见！")
            break
        if not user_input:
            continue

        messages.append({"role": "user", "content": user_input})
        answer = run_agent(messages)
        print(f"\n🤖 助手: {answer}")


if __name__ == "__main__":
    main()
