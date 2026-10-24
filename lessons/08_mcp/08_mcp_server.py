"""
========================================================================
第 8 课：MCP Server —— 把我们的工具包装成标准协议，供 Cursor/Claude 调用
========================================================================

对应第 8 课。用官方 mcp SDK 的 FastMCP，把前几课写过的工具
（计算器、当前时间、文件读写）包装成一个标准 MCP Server。

对比感受：
  - 第 5 课我们自己实现的 @agent.tool 装饰器
  - 这里的 @mcp.tool() 装饰器
  两者几乎一模一样！因为 MCP 做的就是把"工具"这个概念标准化。
  区别在于：@agent.tool 只有你的 agent 能用；
            @mcp.tool() 则任何支持 MCP 的客户端(Cursor/Claude)都能用。

【如何运行】
  这个文件不是给你直接 python 运行来聊天的，
  而是作为一个"服务"被 Cursor 等 MCP 客户端启动和调用。
  配置方法见本文件末尾注释，或 README。

  想本地快速自测，可以用官方工具：
      mcp dev 08_mcp_server.py
  它会打开一个网页版的 Inspector，让你手动点按钮测试每个工具。
"""

from datetime import datetime
from pathlib import Path

from mcp.server.fastmcp import FastMCP

# 创建一个 MCP Server 实例，起个名字（客户端里会显示这个名字）
mcp = FastMCP("my-first-agent-tools")

# 沿用第 4 课的沙箱思路：文件操作限制在 workspace 目录内
WORKSPACE = (Path(__file__).resolve().parents[2] / "workspace").resolve()
WORKSPACE.mkdir(exist_ok=True)


def _safe_path(relative_path: str) -> Path:
    """路径安全校验：确保只能访问 workspace 内的文件。"""
    target = (WORKSPACE / relative_path).resolve()
    if WORKSPACE not in target.parents and target != WORKSPACE:
        raise ValueError(f"拒绝访问：'{relative_path}' 超出了沙箱允许的范围")
    return target


# ======================================================================
# 用 @mcp.tool() 注册工具 —— 和第 5 课的 @agent.tool 几乎一样！
# 同样是靠函数签名 + docstring 自动生成给模型看的 schema。
# ======================================================================

@mcp.tool()
def calculator(expression: str) -> str:
    """计算一个数学表达式并返回结果。当需要精确数学计算时使用。

    Args:
        expression: 合法的数学表达式，例如 "(12 + 8) * 3"
    """
    try:
        return str(eval(expression, {"__builtins__": {}}, {}))
    except Exception as e:
        return f"计算出错: {e}"


@mcp.tool()
def get_current_time() -> str:
    """获取当前的日期和时间。"""
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


@mcp.tool()
def list_files(directory: str = ".") -> str:
    """列出工作目录下某个文件夹里的所有文件。

    Args:
        directory: 相对工作目录的路径，默认 '.' 表示工作目录根。
    """
    try:
        target = _safe_path(directory)
        if not target.exists():
            return f"目录不存在: {directory}"
        items = [("📁 " if p.is_dir() else "📄 ") + p.name for p in sorted(target.iterdir())]
        return "\n".join(items) if items else "(空目录)"
    except Exception as e:
        return f"出错: {e}"


@mcp.tool()
def read_file(path: str) -> str:
    """读取 workspace 下某个文件的文本内容。

    Args:
        path: 要读取的文件路径（相对工作目录）。
    """
    try:
        target = _safe_path(path)
        if not target.exists():
            return f"文件不存在: {path}"
        return target.read_text(encoding="utf-8")
    except Exception as e:
        return f"出错: {e}"


@mcp.tool()
def write_file(path: str, content: str) -> str:
    """把文本内容写入 workspace 下的某个文件（会覆盖已有文件）。

    Args:
        path: 要写入的文件路径（相对工作目录）。
        content: 要写入的文本内容。
    """
    try:
        target = _safe_path(path)
        target.write_text(content, encoding="utf-8")
        return f"已写入 {path}（共 {len(content)} 个字符）"
    except Exception as e:
        return f"出错: {e}"


if __name__ == "__main__":
    # 以 stdio 方式运行（标准输入输出），这是 Cursor/Claude Desktop 最常用的接入方式。
    mcp.run(transport="stdio")


# ======================================================================
# 【如何接入 Cursor】
# ----------------------------------------------------------------------
# 在项目根目录创建 .cursor/mcp.json（或编辑你全局的 MCP 配置），加入：
#
# {
#   "mcpServers": {
#     "my-first-agent-tools": {
#       "command": "d:\\Data\\Project\\github\\agent-step-by-step\\.venv\\Scripts\\python.exe",
#       "args": ["d:\\Data\\Project\\github\\agent-step-by-step\\08_mcp_server.py"]
#     }
#   }
# }
#
# 保存后在 Cursor 设置里启用这个 MCP server，就能让 Cursor 调用上面这些工具了。
# ======================================================================
