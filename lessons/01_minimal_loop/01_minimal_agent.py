"""
========================================================================
第 1 个 Agent：最小对话循环（还没有工具）
========================================================================

对应第 1 课理论里的 4 个零件，这一版我们先实现其中 3 个：
    ① 大脑 (Model)   -> call_llm() 函数，调用 LLM API
    ② 记忆 (Memory)  -> messages 列表，存放所有对话历史
    ③ 工具 (Tools)   -> 【本版暂无，下一课加】
    ④ 循环 (Loop)    -> main() 里的 while True

本课目标：先确保你的 base_url / api_key / model 配置能打通，
         并亲眼看到「记忆（messages）如何随着对话不断变长」。
"""

import os

from dotenv import load_dotenv
from openai import OpenAI

# ------------------------------------------------------------------
# 第 0 步：读取配置
# load_dotenv() 会自动寻找同目录下的 .env 文件，把里面的变量加载进环境变量。
# ------------------------------------------------------------------
load_dotenv()

BASE_URL = os.getenv("LLM_BASE_URL")
API_KEY = os.getenv("LLM_API_KEY")
MODEL = os.getenv("LLM_MODEL")

# 一个小小的「防呆」检查：如果没配好，直接报错提示，而不是跑到一半才崩。
if not all([BASE_URL, API_KEY, MODEL]):
    raise SystemExit(
        "❌ 配置缺失！请先复制 .env.example 为 .env，并填入 "
        "LLM_BASE_URL / LLM_API_KEY / LLM_MODEL 三个值。"
    )

# ------------------------------------------------------------------
# ① 大脑：创建一个指向你的模型服务的客户端。
# 关键点：OpenAI 这个 SDK 并不是只能连 OpenAI 官方，
#        只要传入 base_url，它就能连任何「兼容 OpenAI 协议」的服务。
# ------------------------------------------------------------------
client = OpenAI(base_url=BASE_URL, api_key=API_KEY)


def call_llm(messages: list) -> str:
    """
    把【整个记忆】发给 LLM，拿回它生成的一段文字。

    注意：每次调用都要把【完整的 messages】发过去。
    LLM 本身是「无记忆」的，它能「记住」对话，完全是因为
    我们每次都把历史重新发给它。这就是为什么「记忆」要由我们程序来维护。
    """
    response = client.chat.completions.create(
        model=MODEL,
        messages=messages,
    )
    # 返回里拿出模型生成的文字内容
    return response.choices[0].message.content


def main():
    print("=" * 50)
    print("🤖 最小 Agent 已启动（纯对话，暂无工具）")
    print("   输入内容和它聊天，输入 quit 退出。")
    print("=" * 50)

    # ------------------------------------------------------------------
    # ② 记忆：就是这个普通的 Python 列表。
    # 列表里每个元素是一个 dict，有两个字段：
    #   role    -> 这句话是谁说的：system(系统设定) / user(用户) / assistant(AI)
    #   content -> 具体说了什么
    #
    # 我们先放一条 system 消息，用来给 AI 设定「人设/角色」。
    # ------------------------------------------------------------------
    messages = [
        {"role": "system", "content": "你是一个友好的中文助手，回答简洁。"}
    ]

    # ------------------------------------------------------------------
    # ④ 循环：这就是最简版的 "Agent Loop"。
    # 目前每轮循环做的事：读用户输入 -> 发给 LLM -> 打印回答。
    # （下一课我们会在这个循环里加入「调用工具」的分支。）
    # ------------------------------------------------------------------
    while True:
        user_input = input("\nuser: ").strip()
        if user_input.lower() in ("quit", "exit", "q"):
            print("👋 再见！")
            break
        if not user_input:
            continue

        # 把用户这句话【追加】进记忆
        messages.append({"role": "user", "content": user_input})

        # 把【当前完整记忆】发给大脑，拿到回答
        answer = call_llm(messages)

        # 把 AI 的回答也【追加】进记忆，这样下一轮它才能记得自己说过什么
        messages.append({"role": "assistant", "content": answer})

        print(f"🤖 助手: {answer}")

        # 【教学用】把当前记忆的长度打印出来，
        # 你会直观看到：每聊一轮，messages 就变长 2 条（你一条 + AI 一条）。
        print(f"   [调试] 当前记忆里共有 {len(messages)} 条消息")


if __name__ == "__main__":
    main()
