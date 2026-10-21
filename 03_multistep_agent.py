"""
========================================================================
第 3 个 Agent：多步推理（Multi-step Reasoning）
========================================================================

对应第 3 课。核心逻辑和第 2 课一样（还是那个内层 while 循环），
但我们做了三个增强，让「多步思考」看得见、更安全：

  1. 打印每一步的轮次编号，让你看清 agent 走了几步
  2. 打印模型在调工具时附带的「思考文字」（如果有）
  3. 加入 max_steps 步数上限，防止 agent 陷入死循环

试一个一步做不完的任务，例如：
  「现在几点？从现在到今晚 24:00 还有多少分钟？」
它必须：先查时间 → 再基于查到的时间去计算 → 最后组织答案。
"""

import json
import os
from datetime import datetime

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
# 工具定义（和第 2 课相同）
# ======================================================================

def calculator(expression: str) -> str:
    try:
        result = eval(expression, {"__builtins__": {}}, {})
        return str(result)
    except Exception as e:
        return f"计算出错: {e}"


def get_current_time() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


AVAILABLE_TOOLS = {
    "calculator": calculator,
    "get_current_time": get_current_time,
}

TOOLS_SCHEMA = [
    {
        "type": "function",
        "function": {
            "name": "calculator",
            "description": "计算一个数学表达式并返回结果。当需要精确数学计算时使用。",
            "parameters": {
                "type": "object",
                "properties": {
                    "expression": {
                        "type": "string",
                        "description": "合法的数学表达式，例如 '(24*60) - (14*60+30)'",
                    }
                },
                "required": ["expression"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_current_time",
            "description": "获取当前的日期和时间。当需要知道现在的时间时使用。",
            "parameters": {"type": "object", "properties": {}},
        },
    },
]


# ======================================================================
# Agent Loop（多步版：带轮次打印 + 步数上限）
# ======================================================================

def run_agent(messages: list, max_steps: int = 8) -> str:
    """
    执行多步「思考-行动」循环，直到模型给出最终答案，或达到步数上限。

    max_steps：这是一个「安全阀」。
      如果模型因为某种原因一直要求调工具、停不下来，
      我们最多让它走 max_steps 步就强制结束，避免无限循环烧钱/卡死。
    """
    for step in range(1, max_steps + 1):
        print(f"\n   ┌─ 第 {step} 步 ───────────────────────")

        # 把 [记忆 + 工具清单] 发给大脑
        response = client.chat.completions.create(
            model=MODEL,
            messages=messages,
            tools=TOOLS_SCHEMA,
        )
        msg = response.choices[0].message

        # 如果模型在调工具的同时还说了些「思考」的话，打印出来，
        # 让你看到它的推理过程（不是所有模型都会给，有就显示）
        if msg.content:
            print(f"   │ 💭 思考: {msg.content}")

        # ---- 判断：模型给出最终答案了吗？ ----
        if not msg.tool_calls:
            print(f"   └─ ✅ 第 {step} 步给出最终答案，循环结束")
            messages.append({"role": "assistant", "content": msg.content})
            return msg.content

        # ---- 否则：执行模型要求的工具 ----
        messages.append(msg)  # 先保留模型这条「要调工具」的消息

        for tool_call in msg.tool_calls:
            tool_name = tool_call.function.name
            tool_args = json.loads(tool_call.function.arguments)

            print(f"   │ 🔧 调用: {tool_name}({tool_args})")

            func = AVAILABLE_TOOLS.get(tool_name)
            result = func(**tool_args) if func else f"未知工具 {tool_name}"

            print(f"   │ 📥 结果: {result}")

            messages.append({
                "role": "tool",
                "tool_call_id": tool_call.id,
                "content": str(result),
            })

        print(f"   └─ 第 {step} 步完成，带着工具结果继续下一步...")

    # 走到这里说明步数用完了还没结束 —— 触发安全阀
    return "⚠️ 达到最大步数上限，已强制停止。可能任务太复杂，或模型卡在循环里了。"


def main():
    print("=" * 60)
    print("🤖 多步推理 Agent 已启动")
    print("   试试需要连续多步的任务，例如：")
    print("   『现在几点？从现在到今晚24:00还有多少分钟？』")
    print("   观察它如何「走一步、看结果、再走下一步」。")
    print("   输入 quit 退出。")
    print("=" * 60)

    messages = [
        {
            "role": "system",
            "content": (
                "你是一个善于分步解决问题的中文助手。"
                "遇到需要多个步骤的任务时，一步一步地使用工具，"
                "每一步都基于上一步的结果来决定下一步做什么。"
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
