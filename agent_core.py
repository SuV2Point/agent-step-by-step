"""
========================================================================
agent_core.py —— 可复用的 Agent 核心库
========================================================================

对应第 5 课。把前 4 课重复的逻辑沉淀成一个 Agent 类：
  - 封装 .env 读取、client 初始化
  - 封装那个多步 Agent Loop
  - 提供 @agent.tool 装饰器：从普通函数【自动生成】工具 schema

以后写新 agent 只需要：
    agent = Agent(system_prompt="...")

    @agent.tool
    def my_tool(x: str) -> str:
        '''工具说明写在这里。'''
        return ...

    agent.chat("用户的话")
"""

import inspect
import json
import os
from typing import Callable

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()


# Python 类型 -> JSON Schema 类型 的映射表
# （JSON Schema 是 OpenAI 协议里描述参数用的格式）
_PY_TYPE_TO_JSON = {
    str: "string",
    int: "integer",
    float: "number",
    bool: "boolean",
    list: "array",
    dict: "object",
}


def _build_schema_from_func(func: Callable) -> dict:
    """
    【本课核心魔术】从一个普通 Python 函数，自动生成 OpenAI 工具 schema。

    利用「内省」提取三样东西：
      - 函数名      -> name
      - 文档字符串  -> description
      - 参数签名    -> parameters(JSON Schema)
    """
    sig = inspect.signature(func)

    properties = {}
    required = []
    for param_name, param in sig.parameters.items():
        # 根据参数的类型标注，查出对应的 JSON 类型；没标注就默认 string
        json_type = _PY_TYPE_TO_JSON.get(param.annotation, "string")
        properties[param_name] = {"type": json_type}

        # 没有默认值的参数 = 必填
        if param.default is inspect.Parameter.empty:
            required.append(param_name)

    return {
        "type": "function",
        "function": {
            "name": func.__name__,
            # 用函数的文档字符串作为描述；没写就给个兜底
            "description": (func.__doc__ or "").strip() or func.__name__,
            "parameters": {
                "type": "object",
                "properties": properties,
                "required": required,
            },
        },
    }


class Agent:
    """一个可复用的、支持多步工具调用的 Agent。"""

    def __init__(self, system_prompt: str = "你是一个有用的助手。", max_steps: int = 12):
        base_url = os.getenv("LLM_BASE_URL")
        api_key = os.getenv("LLM_API_KEY")
        self.model = os.getenv("LLM_MODEL")
        if not all([base_url, api_key, self.model]):
            raise SystemExit("❌ 配置缺失！请检查 .env 文件。")

        self.client = OpenAI(base_url=base_url, api_key=api_key)
        self.max_steps = max_steps

        # 记忆：对话历史
        self.messages = [{"role": "system", "content": system_prompt}]

        # 工具登记表：名字 -> 真正的函数
        self._tool_funcs: dict[str, Callable] = {}
        # 工具 schema 列表（发给模型用）
        self._tool_schemas: list[dict] = []

    # ------------------------------------------------------------------
    # 工具注册装饰器：这就是让「加工具只需几行」成为可能的关键
    # ------------------------------------------------------------------
    def tool(self, func: Callable) -> Callable:
        """
        装饰器。把被装饰的函数登记为本 agent 的一个工具，
        并自动根据它的签名/文档生成 schema。
        """
        self._tool_funcs[func.__name__] = func
        self._tool_schemas.append(_build_schema_from_func(func))
        return func  # 原样返回，不改变函数本身

    # ------------------------------------------------------------------
    # 核心：多步 Agent Loop（逻辑和第 3/4 课相同，只是搬进了类里）
    # ------------------------------------------------------------------
    def _run_loop(self, verbose: bool = True) -> str:
        for step in range(1, self.max_steps + 1):
            kwargs = {"model": self.model, "messages": self.messages}
            # 只有在确实注册了工具时，才把 tools 字段带上
            if self._tool_schemas:
                kwargs["tools"] = self._tool_schemas

            response = self.client.chat.completions.create(**kwargs)
            msg = response.choices[0].message

            if verbose and msg.content:
                print(f"   💭 {msg.content}")

            # 没有工具调用 = 最终答案
            if not msg.tool_calls:
                self.messages.append({"role": "assistant", "content": msg.content})
                return msg.content

            # 有工具调用 = 执行它们，再继续循环
            self.messages.append(msg)
            for tool_call in msg.tool_calls:
                name = tool_call.function.name
                args = json.loads(tool_call.function.arguments)

                if verbose:
                    print(f"   🔧 {name}({args})")

                func = self._tool_funcs.get(name)
                try:
                    result = func(**args) if func else f"未知工具 {name}"
                except Exception as e:
                    result = f"工具执行出错: {e}"

                if verbose:
                    preview = result if len(str(result)) <= 100 else str(result)[:100] + "..."
                    print(f"   📥 {preview}")

                self.messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": str(result),
                })

        return "⚠️ 达到最大步数上限，已强制停止。"

    def chat(self, user_input: str, verbose: bool = True) -> str:
        """对 agent 说一句话，拿到它（可能经过多步工具调用后的）最终回答。"""
        self.messages.append({"role": "user", "content": user_input})
        return self._run_loop(verbose=verbose)

    # ==================================================================
    # 第 6 课新增：流式版本
    # ==================================================================
    def _execute_tool_calls(self, tool_calls: list, verbose: bool = True) -> None:
        """执行一批工具调用，并把结果以 role=tool 追加进记忆。被流式/非流式共用。"""
        for tc in tool_calls:
            name = tc["name"]
            try:
                args = json.loads(tc["arguments"] or "{}")
            except json.JSONDecodeError:
                args = {}

            if verbose:
                print(f"\n   🔧 {name}({args})")

            func = self._tool_funcs.get(name)
            try:
                result = func(**args) if func else f"未知工具 {name}"
            except Exception as e:
                result = f"工具执行出错: {e}"

            if verbose:
                preview = result if len(str(result)) <= 100 else str(result)[:100] + "..."
                print(f"   📥 {preview}")

            self.messages.append({
                "role": "tool",
                "tool_call_id": tc["id"],
                "content": str(result),
            })

    def _run_loop_stream(self) -> str:
        """
        流式版 Agent Loop。
        核心难点：流式返回是一块块(chunk)到达的，我们要分两种情况处理：
          - delta.content   -> 模型在"说话"，逐字打印
          - delta.tool_calls -> 模型在"调工具"，碎片要自己累积拼接
        """
        for step in range(1, self.max_steps + 1):
            kwargs = {
                "model": self.model,
                "messages": self.messages,
                "stream": True,  # <-- 开启流式的唯一开关
            }
            if self._tool_schemas:
                kwargs["tools"] = self._tool_schemas

            stream = self.client.chat.completions.create(**kwargs)

            # 用来累积这一轮的产物
            content_parts: list[str] = []          # 累积正文文字
            tool_calls_buf: dict[int, dict] = {}   # 累积工具调用碎片，按 index 分组
            printed_prefix = False

            for chunk in stream:
                if not chunk.choices:
                    continue
                delta = chunk.choices[0].delta

                # 情况 1：模型在说话 —— 逐字打印
                if delta.content:
                    if not printed_prefix:
                        print("🤖 助手: ", end="", flush=True)
                        printed_prefix = True
                    print(delta.content, end="", flush=True)
                    content_parts.append(delta.content)

                # 情况 2：模型在调工具 —— 碎片累积（关键拼接逻辑）
                if delta.tool_calls:
                    for tcd in delta.tool_calls:
                        idx = tcd.index
                        # 第一次见到这个 index，初始化一个空壳
                        slot = tool_calls_buf.setdefault(
                            idx, {"id": None, "name": "", "arguments": ""}
                        )
                        if tcd.id:
                            slot["id"] = tcd.id
                        if tcd.function and tcd.function.name:
                            slot["name"] += tcd.function.name
                        if tcd.function and tcd.function.arguments:
                            # 参数是一点点拼出来的 JSON 字符串
                            slot["arguments"] += tcd.function.arguments

            full_content = "".join(content_parts)

            # 这一轮流结束了，判断模型是要调工具还是已经说完
            if not tool_calls_buf:
                # 没有工具调用 = 最终答案
                print()  # 换行收尾
                self.messages.append({"role": "assistant", "content": full_content})
                return full_content

            # 有工具调用：先把 assistant 这条（带 tool_calls）写回记忆
            ordered = [tool_calls_buf[i] for i in sorted(tool_calls_buf)]
            self.messages.append({
                "role": "assistant",
                "content": full_content or None,
                "tool_calls": [
                    {
                        "id": tc["id"],
                        "type": "function",
                        "function": {"name": tc["name"], "arguments": tc["arguments"]},
                    }
                    for tc in ordered
                ],
            })

            # 执行工具，结果塞回记忆，然后 for 继续下一步
            self._execute_tool_calls(ordered, verbose=True)

        return "⚠️ 达到最大步数上限，已强制停止。"

    def chat_stream(self, user_input: str) -> str:
        """流式版的 chat：回答会像 ChatGPT 那样逐字打印出来。"""
        self.messages.append({"role": "user", "content": user_input})
        return self._run_loop_stream()
