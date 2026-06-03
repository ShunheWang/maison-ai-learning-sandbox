# AI 技术全景图 & 技能清单

## 图例
- **深度**：✅ 必须掌握 / ⚠️ 了解即可 / ❌ 先不碰
- **状态**：✅ 已掌握 / ⚠️ 了解概念不熟 / ❌ 还没学

---

## 一、LLM 基础层

| 技术 | 是什么 | 深度 | 状态 | 备注 |
|------|--------|------|------|------|
| LLM API（Anthropic SDK） | 调 API 跟大模型对话 | ✅ | ✅ | 01_hello_claude.py |
| API Key 管理 | 环境变量、.env 文件 | ✅ | ✅ | |
| Token | LLM 的计费单位 | ✅ | ✅ | 01 里看了 usage.input_tokens/output_tokens |
| Message 结构 | role + content，system/user/assistant | ✅ | ✅ | |
| Context Window | 一次对话能塞多少内容 | ✅ | ⚠️ | 概念知道，没碰到上限 |
| Content Blocks | text / tool_use / tool_result | ✅ | ✅ | 03_agent_loop.py 全用过 |
| stop_reason | end_turn vs tool_use vs max_tokens | ✅ | ✅ | |
| Temperature / Top-P | 控制输出随机性 | ⚠️ | ❌ | |
| Streaming | 流式输出，一个字一个字蹦 | ⚠️ | ❌ | |
| Rate Limit | API 调用频率限制 | ⚠️ | ❌ | |

---

## 二、Agent 核心（Step 1 — 正在学）

| 技术 | 是什么 | 深度 | 状态 | 备注 |
|------|--------|------|------|------|
| **Tool Calling** | LLM 决定调哪个函数，你执行后把结果送回 | ✅ | ✅ | 02_define_tool.py + 03_agent_loop.py |
| **JSON Schema (Tool 定义)** | name + description + input_schema | ✅ | ✅ | |
| **Agent Loop** | Think → Act → Observe 循环 | ✅ | ✅ | 03_agent_loop.py |
| **多轮对话历史管理** | messages 数组拼接，tool_result 回传 | ✅ | ✅ | |
| **System Prompt 设计** | 给 Agent 定人设，控制行为 | ✅ | ❌ | 单元 2.2 |
| **错误处理** | 工具挂了不崩，把错误塞回 LLM | ✅ | ✅ | is_error + 清晰错误描述 |
| **Strict Tool Use** | `strict: true` 强制参数校验 | ✅ | ✅ | 笔记第 8 章 |
| **tool_choice** | 控制 Claude 是否强制调工具 | ⚠️ | ✅ | auto 够用，了解即可 |
| **Parallel Tool Use** | 一次调用多个工具 | ⚠️ | ✅ | 了解概念 |
| **Tool Runner (SDK)** | SDK 自动处理循环 | ⚠️ | ✅ | 了解存在，目前手动写循环 |
| Python subprocess / socket | 从 Python 连外部程序（rookieDB） | ✅ | ⚠️ | 单元 4 要用 |
| Function Calling | OpenAI 的叫法，跟 Tool Calling 一回事 | ⚠️ | ❌ | |
| ReAct Pattern | Reasoning + Acting，Agent 设计模式 | ⚠️ | ❌ | |
| Prompt Engineering | 写提示词的技巧 | ⚠️ | ❌ | |
| Structured Output | 让 LLM 返回固定格式 JSON | ⚠️ | ❌ | |

---

## 三、Agent 框架

| 框架 | 是什么 | 深度 | 状态 |
|------|--------|------|------|
| **Anthropic SDK** | 官方 Python SDK，轻量 | ✅ 本次用 | ✅ |
| LangChain | 最流行但重 | ❌ | ❌ |
| LangGraph | LangChain 状态机版 | ❌ | ❌ |
| Vercel AI SDK | 前端 TS Agent | ❌ | ❌ |
| AutoGen | 微软多 Agent 框架 | ❌ | ❌ |
| CrewAI | 多 Agent 协作 | ❌ | ❌ |

---

## 四、MCP（Model Context Protocol）— Step 2

| 概念 | 是什么 | 深度 | 状态 |
|------|--------|------|------|
| MCP 协议 | Anthropic 推的标准化 Tool 协议 | ✅ 后续 | ❌ |
| MCP Server | 工具提供方 | ✅ 后续 | ❌ |
| MCP Client | Agent 端，发现和调用 MCP Server | ✅ 后续 | ❌ |
| Transport | stdio / HTTP SSE / Streamable HTTP | ⚠️ 后续 | ❌ |

---

## 五、RAG（检索增强生成）— Step 4

| 技术 | 是什么 | 深度 | 状态 |
|------|--------|------|------|
| RAG | 先检索知识库，再让 LLM 回答 | ✅ 后续 | ❌ |
| Embedding | 文本转向量 | ✅ 后续 | ❌ |
| Vector DB | 存向量，做相似度搜索 | ⚠️ 后续 | ❌ |
| Chunking | 文档切分策略 | ⚠️ 后续 | ❌ |

---

## 六、多 Agent 协作 — Step 3

| 技术 | 是什么 | 深度 | 状态 |
|------|--------|------|------|
| Multi-Agent | 多个 Agent 各司其职 | ✅ 后续 | ❌ |
| Agent 通信 | 消息传递、共享状态 | ✅ 后续 | ❌ |
| Orchestration | 谁调度谁，平级还是层级 | ⚠️ 后续 | ❌ |

---

## 七、AI 应用类型（以后可能做的方向）

| 应用类型 | 例子 |
|----------|------|
| Chatbot / 对话助手 | 客服、问答 |
| Coding Agent | Claude Code、Cursor、Copilot |
| **Data Agent** | 自然语言查数据库 ← **你现在做的** |
| Workflow Agent | 自动跑多步骤任务 |
| Search Agent | 联网搜索 + RAG |
| Creative Agent | 写文案、生图 |
| Audit/Guard Agent | 代码审查、安全检查 |

---

## 四步路线图

```
Step 1: Agent + Tool Calling   ← 当前（60%）
        → Anthropic SDK, Tool Calling Loop, System Prompt, 错误处理

Step 2: MCP
        → MCP 协议, Server/Client, Transport

Step 3: Multi-Agent
        → 多 Agent 协作, 通信模式, Orchestration

Step 4: RAG
        → Embedding, Vector DB, 检索管道
```
