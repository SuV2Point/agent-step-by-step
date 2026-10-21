"""
========================================================================
第 2 个 Agent：带工具的 Agent（Function Calling）
========================================================================

对应第 2 课。相比第 1 课，这一版补齐了第 4 个零件：
    ③ 工具 (Tools) -> 下面定义的 calculator / get_current_time 两个普通函数

关键新概念：
  1. 用 JSON 向模型「描述」有哪些工具（TOOLS_SCHEMA）
  2. 模型若决定用工具，返回里会带 tool_calls（而不是直接回答）
  3. 由【我们的程序】真正执行工具，再把结果以 role="tool" 塞回记忆
  4. Agent Loop 里新增「判断分支」：要调工具就执行后再回到开头
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
# 第一部分：定义「工具」—— 它们就是普通的 Python 函数
# ======================================================================

def calculator(expression: str) -> str:
    """计算一个数学表达式字符串，比如 "(12 + 8) * 3"。"""
    try:
        # 注意：eval 有安全风险，这里仅用于教学演示。
        # 后面课程我们会讲如何安全地执行。
        result = eval(expression, {"__builtins__": {}}, {})
        return str(result)
    except Exception as e:
        return f"计算出错: {e}"


def get_current_time() -> str:
    """返回当前的日期和时间。"""
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


# 一个「名字 -> 函数」的映射表，方便程序根据模型给的名字找到对应函数去执行。
AVAILABLE_TOOLS = {
    "calculator": calculator,
    "get_current_time": get_current_time,
}


# ======================================================================
# 第二部分：用 JSON 向模型「描述」这些工具
# ----------------------------------------------------------------------
# 这是模型能「知道」有哪些工具的唯一途径。
# 每个工具要讲清楚三件事：
#   name        -> 工具叫什么（必须和上面 AVAILABLE_TOOLS 的 key 一致）
#   description -> 这个工具是干嘛的（模型靠它判断该不该用，务必写清楚！）
#   parameters  -> 需要什么参数（用 JSON Schema 格式描述）
# ======================================================================
TOOLS_SCHEMA = [
    {
        "type": "function",
        "function": {
            "name": "calculator",
            "description": "计算一个数学表达式并返回结果。当用户需要精确的数学计算时使用。",
            "parameters": {
                "type": "object",
                "properties": {
                    "expression": {
                        "type": "string",
                        "description": "合法的数学表达式，例如 '(12 + 8) * 3'",
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
            "description": "获取当前的日期和时间。当用户询问现在几点、今天几号时使用。",
            "parameters": {
                "type": "object",
                "properties": {},  # 这个工具不需要任何参数
            },
        },
    },
]


# ======================================================================
# 第三部分：Agent Loop（升级版，带工具判断分支）
# ======================================================================

def run_agent(messages: list) -> str:
    """
    执行一轮完整的「思考-行动」循环，直到模型给出最终回答。

    注意这里有一个【内层 while】：
    因为一次用户提问，模型可能需要连续调用好几个工具才能答出来，
    所以要循环「发给模型 -> 若要调工具则执行 -> 再发给模型」，
    直到模型不再要求调工具、给出最终文字回答为止。
    """
    while True:
        # ---- 第 1 步：把 [记忆 + 工具清单] 发给大脑 ----
        response = client.chat.completions.create(
            model=MODEL,
            messages=messages,
            tools=TOOLS_SCHEMA,   # <-- 关键：把工具清单一起发过去
        )

        msg = response.choices[0].message

        # ---- 第 2 步：判断模型想干嘛 ----
        if not msg.tool_calls:
            # 分支 A：模型没要求调工具 = 它直接给出了最终回答
            messages.append({"role": "assistant", "content": msg.content})
            return msg.content

        # 分支 B：模型要求调用工具
        # 先把模型这条「要调工具」的 assistant 消息原样追加进记忆（必须保留）
        messages.append(msg)

        # ---- 第 3 步：挨个执行模型要求的工具 ----
        # （模型有可能一次要求调用多个工具，所以用 for 循环）
        for tool_call in msg.tool_calls:
            tool_name = tool_call.function.name
            # 模型给的参数是 JSON 字符串，要先解析成 Python 字典
            tool_args = json.loads(tool_call.function.arguments)

            print(f"   🔧 [调用工具] {tool_name}  参数={tool_args}")

            # 根据名字找到真正的函数并执行
            func = AVAILABLE_TOOLS.get(tool_name)
            if func is None:
                result = f"错误：未知工具 {tool_name}"
            else:
                result = func(**tool_args)

            print(f"   📥 [工具结果] {result}")

            # ---- 第 4 步：把工具结果以 role='tool' 塞回记忆 ----
            # tool_call_id 用来告诉模型「这个结果是对应你刚才哪一次调用的」
            messages.append({
                "role": "tool",
                "tool_call_id": tool_call.id,
                "content": str(result),
            })

        # for 结束后，带着新塞进去的工具结果，回到 while 开头再问一次模型。


def main():
    print("=" * 55)
    print("🤖 带工具的 Agent 已启动")
    print("   它有两个工具：计算器、获取当前时间")
    print("   试试问：'现在几点' 或 '帮我算 (123+456)*7 等于多少'")
    print("   输入 quit 退出。")
    print("=" * 55)

    messages = [
        {
            "role": "system",
            "content": "你是一个中文助手。当需要精确计算或查询当前时间时，请使用提供的工具。",
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
        print(f"🤖 助手: {answer}")


if __name__ == "__main__":
    main()
