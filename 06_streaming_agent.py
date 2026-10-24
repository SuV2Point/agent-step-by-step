"""
========================================================================
第 6 个 Agent：流式输出（Streaming）
========================================================================

对应第 6 课。和第 5 课功能一样，但回答会【逐字蹦出来】，
就像 ChatGPT 那样，体验好很多。

核心变化只有一处：把 agent.chat(...) 换成 agent.chat_stream(...)。
流式的所有复杂逻辑（逐字打印 + 工具调用碎片拼接）都封装在
agent_core.py 的 _run_loop_stream 里了。

试试：
  - 「写一首关于秋天的短诗」          -> 看它逐字蹦出（纯文字，无工具）
  - 「现在几点？再帮我算 999*888」     -> 看流式下工具调用照样正常工作
"""

from datetime import datetime

from agent_core import Agent

agent = Agent(system_prompt="你是一个中文助手，需要时请使用工具。")


@agent.tool
def calculator(expression: str) -> str:
    """计算一个数学表达式并返回结果。当需要精确数学计算时使用。"""
    try:
        return str(eval(expression, {"__builtins__": {}}, {}))
    except Exception as e:
        return f"计算出错: {e}"


@agent.tool
def get_current_time() -> str:
    """获取当前的日期和时间。当需要知道现在时间时使用。"""
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def main():
    print("=" * 55)
    print("🤖 流式输出 Agent（回答会逐字蹦出来）")
    print("   试试：『写一首关于秋天的短诗』")
    print("   或：『现在几点？再帮我算 999*888』")
    print("   输入 quit 退出。")
    print("=" * 55)

    while True:
        user_input = input("\n你: ").strip()
        if user_input.lower() in ("quit", "exit", "q"):
            print("👋 再见！")
            break
        if not user_input:
            continue

        # 唯一变化：用 chat_stream 代替 chat
        agent.chat_stream(user_input)


if __name__ == "__main__":
    main()
