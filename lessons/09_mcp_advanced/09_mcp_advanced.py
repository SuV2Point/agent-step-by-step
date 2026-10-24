"""
========================================================================
第 9 课：MCP 进阶 —— Tools + Resources + Prompts 完整版
========================================================================

对应第 9 课。在第 8 课（只有 Tools）的基础上，补齐 MCP 的另外两类能力：

  Tools（工具）     -> 模型主动调用的"动作"（第 8 课已学，这里沿用）
  Resources（资源） -> 应用/用户挂给模型当背景的"只读数据"（本课新增）
  Prompts（模板）   -> 用户可选用的"提示词模板"（本课新增）

核心区别记忆法（用 REST 类比）：
  Resource ≈ GET  (只读数据，无副作用，被动提供给模型)
  Tool     ≈ POST (执行动作，可能有副作用，模型主动调用)

这个文件可作为第 8 课 MCP server 的升级替代，接入 Cursor 后，
除了能调用工具，还能看到可挂载的资源和可选用的提示模板。
"""

from datetime import datetime
from pathlib import Path

from mcp.server.fastmcp import FastMCP

mcp = FastMCP("agent-course-tools")

WORKSPACE = (Path(__file__).resolve().parents[2] / "workspace").resolve()
WORKSPACE.mkdir(exist_ok=True)


def _safe_path(relative_path: str) -> Path:
    """路径安全校验：确保只能访问 workspace 内的文件。"""
    target = (WORKSPACE / relative_path).resolve()
    if WORKSPACE not in target.parents and target != WORKSPACE:
        raise ValueError(f"拒绝访问：'{relative_path}' 超出了沙箱允许的范围")
    return target


# ======================================================================
# 一、Tools（工具）—— 模型主动调用的"动作"（沿用第 8 课）
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


# ======================================================================
# 二、Resources（资源）—— 被动提供给模型的"只读数据"
# ----------------------------------------------------------------------
# 用 @mcp.resource(uri) 注册。每个资源有一个 URI（统一资源标识符），
# 客户端(Cursor)通过这个 URI 来读取资源内容。
# 注意：资源是"被读取"的，模型不会像调工具那样主动触发它。
# ======================================================================

@mcp.resource("workspace://files")
def list_workspace_files() -> str:
    """【动态资源】列出 workspace 目录下的所有文件及其大小。

    这是"动态"资源：每次被读取时，都会实时扫描目录，反映最新状态。
    """
    if not WORKSPACE.exists():
        return "(workspace 目录不存在)"
    lines = []
    for p in sorted(WORKSPACE.iterdir()):
        if p.is_file():
            lines.append(f"{p.name}  ({p.stat().st_size} 字节)")
        else:
            lines.append(f"{p.name}/  (目录)")
    return "\n".join(lines) if lines else "(workspace 为空)"


@mcp.resource("guide://agent-course")
def course_guide() -> str:
    """【静态资源】返回本 Agent 课程的学习进度说明。

    这是"静态"资源：内容基本固定，适合当作背景知识挂给模型。
    """
    return (
        "# Agent 从 0 学习课程进度\n"
        "1. 最小对话循环（大脑+记忆+循环）\n"
        "2. 工具调用（Function Calling）\n"
        "3. 多步推理\n"
        "4. 文件工具 + 沙箱\n"
        "5. 工程化重构（可复用 Agent 类）\n"
        "6. 流式输出\n"
        "7. 联网工具（搜索+抓取）\n"
        "8. MCP 协议（Tools）\n"
        "9. MCP 进阶（Resources + Prompts）<- 当前\n"
    )


# ======================================================================
# 三、Prompts（提示模板）—— 用户可选用的"提示词模板"
# ----------------------------------------------------------------------
# 用 @mcp.prompt() 注册。函数参数就是模板的"填空位"，
# 返回的字符串就是展开后的完整提问。
# 在 Cursor/Claude 里，用户能从菜单选中这个 prompt、填入参数来使用。
# ======================================================================

@mcp.prompt()
def summarize_project(project_file: str) -> str:
    """生成一个"总结项目周报"的标准提问模板。

    Args:
        project_file: 要总结的项目文件名，例如 project_a.txt
    """
    return (
        f"请阅读 workspace 目录下的 {project_file} 文件，"
        "然后用中文总结以下三点：\n"
        "1. 本周核心进展（量化的数字要保留）\n"
        "2. 存在的遗留问题\n"
        "3. 你建议的下一步行动\n"
        "请用简洁的 Markdown 列表输出。"
    )


@mcp.prompt()
def code_review(file_path: str) -> str:
    """生成一个"代码审查"的标准提问模板。

    Args:
        file_path: 要审查的代码文件路径。
    """
    return (
        f"请审查 {file_path} 这个文件的代码，重点关注：\n"
        "- 命名是否清晰\n"
        "- 异常处理是否完善\n"
        "- 是否存在安全隐患\n"
        "- 有没有可以简化的地方\n"
        "请按「问题 -> 建议」的格式逐条列出。"
    )


if __name__ == "__main__":
    mcp.run(transport="stdio")
