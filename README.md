# 从 0 开始学 Agent 底层

一步一步手搓一个 Agent，不依赖任何 agent 框架（LangChain / AutoGen 等），
只用 LLM 的 OpenAI 兼容 API，把 Agent 的底层原理彻底看透。

## 环境准备

```powershell
# 1. 创建并激活虚拟环境
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# 2. 安装依赖
pip install -r requirements.txt

# 3. 配置模型（复制模板后填入你自己的 base_url / api_key / model）
Copy-Item .env.example .env
```

## 核心心智模型

> **Agent = LLM（大脑） + 让它循环「思考→行动→观察」的程序外壳。**

Agent 只有 4 个零件：

| 零件 | 作用 | 代码里对应 |
|------|------|-----------|
| ① 大脑 (Model) | 做决策、生成文字 | 调用 LLM API |
| ② 记忆 (Memory) | 存对话历史和工具结果 | `messages` 列表 |
| ③ 工具 (Tools) | 让 agent 能真正做事 | 普通的 Python 函数 |
| ④ 循环 (Loop) | 把三者串起来反复跑 | `while` 循环 |

## 课程进度

| 文件 | 主题 | 学到的东西 |
|------|------|-----------|
| `01_minimal_agent.py` | 最小对话循环 | 大脑 + 记忆 + 循环；messages 如何逐轮变长 |
| `02_agent_with_tools.py` | 工具调用 (Function Calling) | 模型如何决定调工具；tool_calls / role=tool |
| `03_multistep_agent.py` | 多步推理 | 走一步看结果再走下一步；步数上限安全阀 |

> 🏆 **里程碑**：学完前 3 课，你已经手搓出了一个完整 agent 的内核。
> 所有主流框架（LangChain / AutoGen / CrewAI）剥到最底层，就是这三份代码做的事。

## 进阶路线（待学）

- 安全与健壮：替换危险的 `eval`、异常处理、超时
- 真实世界工具：读写本地文件、联网搜索
- 流式输出：像 ChatGPT 一样逐字蹦字
- 多工具协作 / 子任务拆解
- 对比引入框架（如 LangGraph），看它到底帮你封装了什么

## 运行方式

```powershell
python 01_minimal_agent.py
python 02_agent_with_tools.py
```
