"""
========================================================================
第 7 个 Agent：联网工具（网页抓取 + 搜索）
========================================================================

对应第 7 课。给 agent 两个能"碰到真实互联网"的工具：
    fetch_url    -> 抓取一个网页，清洗成纯文本
    web_search   -> 用关键词搜索，返回标题/链接/摘要

要点（真实世界的工具必须考虑这些）：
  - 超时：网络请求必须设超时，否则可能永久卡住
  - 异常：网络随时可能失败，要捕获并返回友好信息给模型
  - 截断：网页正文可能几万字，要截断，否则塞爆上下文窗口

试试：
  - 「帮我抓取 https://example.com 看看讲了什么」
  - 「搜索一下 Python 是什么，给我总结」
"""

import requests
from bs4 import BeautifulSoup
from ddgs import DDGS

from agent_core import Agent

# 一些网站会拒绝"看起来像爬虫"的请求，伪装成浏览器能提高成功率
_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36"
    )
}

# 单个网页正文最多保留多少字符（防止塞爆上下文）
_MAX_PAGE_CHARS = 3000

agent = Agent(
    system_prompt=(
        "你是一个能联网的中文助手。你可以抓取网页、搜索信息。"
        "回答时请基于工具返回的真实内容，不要编造。"
        "如果搜索到多个结果，先挑最相关的，必要时再抓取具体网页细读。"
    )
)


@agent.tool
def fetch_url(url: str) -> str:
    """抓取指定网址的网页内容，并返回清洗后的纯文本。当需要阅读某个具体网页时使用。"""
    try:
        resp = requests.get(url, headers=_HEADERS, timeout=10)
        resp.raise_for_status()
    except Exception as e:
        return f"抓取失败: {e}"

    # 用 BeautifulSoup 把 HTML 解析掉，只留下可读的正文
    soup = BeautifulSoup(resp.text, "html.parser")

    # 去掉脚本、样式等无意义的标签
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()

    # 提取纯文本，并把多余空行压缩掉
    text = soup.get_text(separator="\n")
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    clean = "\n".join(lines)

    if len(clean) > _MAX_PAGE_CHARS:
        clean = clean[:_MAX_PAGE_CHARS] + "\n...(内容过长，已截断)"
    return clean or "(页面没有可提取的文本)"


@agent.tool
def web_search(query: str, max_results: int = 5) -> str:
    """用关键词在互联网上搜索，返回若干条结果（标题、链接、摘要）。当需要查找实时或未知信息时使用。"""
    try:
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=max_results))
    except Exception as e:
        return f"搜索失败: {e}"

    if not results:
        return "没有搜到任何结果。"

    lines = []
    for i, r in enumerate(results, 1):
        title = r.get("title", "(无标题)")
        href = r.get("href", "")
        body = r.get("body", "")
        lines.append(f"{i}. {title}\n   链接: {href}\n   摘要: {body}")
    return "\n\n".join(lines)


def main():
    print("=" * 60)
    print("🤖 联网 Agent（能抓网页、能搜索）")
    print("   试试：『搜索一下 Python 是什么，帮我总结』")
    print("   或：『抓取 https://example.com 看看讲了什么』")
    print("   输入 quit 退出。")
    print("=" * 60)

    while True:
        user_input = input("\n你: ").strip()
        if user_input.lower() in ("quit", "exit", "q"):
            print("👋 再见！")
            break
        if not user_input:
            continue

        agent.chat_stream(user_input)


if __name__ == "__main__":
    main()
