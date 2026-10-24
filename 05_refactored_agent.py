"""
========================================================================
第 5 个 Agent：用重构后的 agent_core 库来写
========================================================================

对应第 5 课。注意看：用了 agent_core 后，
原来每课几百行的样板代码，现在加一个工具只要「函数 + @agent.tool」。

对比一下：
  - 第 2 课：定义函数 + 塞进字典 + 手写一大段 JSON schema（3 处）
  - 第 5 课：定义函数 + 一个 @agent.tool 装饰器（1 处，schema 全自动）
"""

from datetime import datetime

from agent_core import Agent

# 创建一个 agent，设定人设
agent = Agent(system_prompt="你是一个中文助手，需要时请使用工具。")


# ---- 注册工具：只要加个 @agent.tool，函数、注册、schema 全自动搞定 ----

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
    print("🤖 重构版 Agent（基于 agent_core 库）")
    print("   功能和前几课一样，但核心逻辑全在 agent_core.py 里")
    print("   输入 quit 退出。")
    print("=" * 55)

    while True:
        user_input = input("\n你: ").strip()
        if user_input.lower() in ("quit", "exit", "q"):
            print("👋 再见！")
            break
        if not user_input:
            continue

        answer = agent.chat(user_input)
        print(f"🤖 助手: {answer}")


if __name__ == "__main__":
    main()
