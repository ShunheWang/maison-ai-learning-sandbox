# MCP 学习大纲

> 目标：理解 MCP 协议，最终把 `execute_sql` 标准化为 MCP Tool（Step 2 目标）。
> 两份学习资料在 `docs-resources/mcp/` 下。本文只挑跟项目相关的部分。

## 学习路径（3 阶段）

```
Phase 1: 概念          Phase 2: 动手          Phase 3: 应用到项目
  MCP 是什么          写一个 Python MCP        把 execute_sql
  为什么需要它        Server + Client          包装成 MCP Tool
  核心架构           跑通端到端流程            替换现有实现
  ──────────────────────────────────────────────────────────→
         3 天                   2 天                      2 天
```

---

## Phase 1：MCP 概念（为什么需要、怎么工作）

### 1.1 MCP 是什么 & 为什么需要

**阅读**：`docs-resources/mcp/mcp-for-beginners-main/00-Introduction/README.md`

**要搞清楚的问题**：
- MCP 解决什么问题？（工具集成碎片化）
- USB-C 类比：MCP = AI 应用的"统一接口"
- 三大角色：Host / Client / Server 分别干什么
- 跟我们现在做的事情什么关系？（我们已经有 Tool Calling，MCP 是把 Tool 标准化、可复用）

### 1.2 核心架构 + 协议层

**阅读**：`docs-resources/mcp/mcp-for-beginners-main/01-CoreConcepts/README.md`

**重点概念**：

| 概念 | 一句话 | 对应我们项目的什么 |
|------|--------|-------------------|
| **Server** | 工具提供方，暴露 Tools/Resources/Prompts | 我们要把 `execute_sql` 做成一个 MCP Server |
| **Client** | Agent 端，发现和调用 MCP Server | 我们现有的 Agent 循环 |
| **Host** | 运行 Client 的应用（Claude Desktop、VS Code 等） | 我们的 Python 脚本 |
| **Tools** | 可执行函数，Server 暴露的核心能力 | `execute_sql` 就是一个 Tool |
| **Resources** | 数据源（文件、数据库等），给 LLM 提供上下文 | 表结构信息、schema |
| **Prompts** | 预定义的提示词模板 | System Prompt |
| **Transport** | 通信方式：STDIO（本地）或 HTTP SSE（远程） | 我们先用 STDIO |

**协议层面**：
- 数据层：JSON-RPC 2.0（所有消息都是标准 JSON 格式）
- 传输层：STDIO / Streamable HTTP with SSE
- 生命周期：initialize → 能力协商 → 工具调用 → 关闭
- 协议版本：date-based versioning，当前 `2025-11-25`

**可以跳过的内容**（跟当前目标无关）：
- Sampling（Server 反向调 Client 的 LLM）
- Elicitation（Server 向用户要输入）
- Roots（文件系统边界）
- Tasks（异步执行）
- OAuth / 复杂认证

---

## Phase 2：动手实践（Python MCP Server + Client）

### 2.1 写第一个 MCP Server

**参考**：
- `docs-resources/mcp/mcp-for-beginners-main/03-GettingStarted/01-first-server/README.md`
- Python 官方 SDK：`fastmcp` 库

**目标**：写一个最简单的 MCP Server（比如一个 weather 查询工具），用 MCP Inspector 测试。

```bash
pip install fastmcp
```

**产出**：`step2-mcp/01_first_mcp_server.py` — 一个独立可运行的 MCP Server

### 2.2 写 MCP Client + 接入 LLM

**参考**：
- `docs-resources/mcp/mcp-for-beginners-main/03-GettingStarted/02-client/README.md`
- `docs-resources/mcp/mcp-for-beginners-main/03-GettingStarted/03-llm-client/README.md`

**目标**：写一个 Python Client，连上 Server，让 LLM 能通过 MCP 调用工具。

**核心流程**：
```
Client → initialize → Server
Client → tools/list → Server（发现有哪些工具）
Client → tools/call → Server（调用工具，Server 执行后返回结果）
```

**产出**：`step2-mcp/02_mcp_client.py` — 一个能连 MCP Server 的 Client

### 2.3 Transport 方式选择

**参考**：
- `docs-resources/mcp/mcp-for-beginners-main/03-GettingStarted/05-stdio-server/README.md`
- `docs-resources/mcp/mcp-for-beginners-main/03-GettingStarted/06-http-streaming/README.md`

**结论**：我们项目用 STDIO（本地进程），简单直接。HTTP 是远程场景才需要的。

### 2.4 调试工具

**参考**：`docs-resources/mcp/mcp-for-beginners-main/03-GettingStarted/13-mcp-inspector/README.md`

**工具**：MCP Inspector — 可以在不写代码的情况下测试 Server，调试工具调用是否正确。

---

## Phase 3：应用到项目（execute_sql → MCP Tool）

### 3.1 设计：怎么把 execute_sql 包装成 MCP Tool

当前架构：
```
Agent Loop (Python) → execute_sql(sql) → socket → rookieDB
```

目标架构：
```
Agent Loop (Python) → MCP Client → MCP Server → execute_sql(sql) → socket → rookieDB
```

**为什么多了一层？**
- MCP Server 标准化了 `execute_sql` 的暴露方式
- 以后其他 Agent 也能复用这个 MCP Server
- 死锁检测时，多个 Agent 可以各自通过 MCP 连同一个数据库

### 3.2 实现

**产出**：`step2-mcp/03_rookiedb_mcp_server.py` + `step2-mcp/04_agent_with_mcp.py`

具体步骤：
1. 把 `06_error_handling.py` 里的 `execute_sql` + `RookieDBConnection` 抽出来
2. 包装成一个 MCP Server（fastmcp）
3. 修改 Agent 循环，通过 MCP Client 调用工具（而不是直接调用函数）
4. 验证：功能跟 06 一致，但工具调用走了 MCP 协议

---

## 学习资料索引

| 要学的内容 | 资料位置 | 优先级 |
|-----------|---------|--------|
| MCP 是什么、为什么 | `mcp-for-beginners/00-Introduction/README.md` | ⭐⭐⭐ |
| 核心架构 + 协议 | `mcp-for-beginners/01-CoreConcepts/README.md` | ⭐⭐⭐ |
| 第一个 Server | `mcp-for-beginners/03-GettingStarted/01-first-server/README.md` | ⭐⭐⭐ |
| Client + LLM | `mcp-for-beginners/03-GettingStarted/02-client/README.md` + `03-llm-client/README.md` | ⭐⭐⭐ |
| STDIO Transport | `mcp-for-beginners/03-GettingStarted/05-stdio-server/README.md` | ⭐⭐ |
| MCP Inspector 调试 | `mcp-for-beginners/03-GettingStarted/13-mcp-inspector/README.md` | ⭐⭐ |
| HTTP Streaming | `mcp-for-beginners/03-GettingStarted/06-http-streaming/README.md` | ⭐（了解即可） |
| Security | `mcp-for-beginners/02-Security/README.md` | ⭐（后续用到再看） |
| Adversarial Multi-Agent | `mcp-for-beginners/05-AdvancedTopics/mcp-adversarial-agents/README.md` | 💡 Step 3 时回来看 |

## 跳过清单

以下内容跟当前目标无关，别浪费时间：

- ❌ Module 2：Security 深度内容（现在不需要，到生产再学）
- ❌ Module 4：Practical Implementation（太杂，多语言 SDK 细节）
- ❌ Module 6：Community Contributions
- ❌ Module 7：Lessons from Early Adoption
- ❌ Module 8：Best Practices
- ❌ Module 9：Case Studies
- ❌ Module 10：Hands-on Workshop（AI Toolkit）
- ❌ Module 11：Database Integration Labs（PostgreSQL + Azure，跟 rookieDB 没关系）
- ❌ `lets-learn-mcp-java/` 全部内容（Java，语言不对，但概念可扫一眼）
- ❌ Advanced Topics 大部分（只有 Adversarial Multi-Agent 在 Step 3 有用）

## 额外笔记空间

MCP 学习过程中的想法、启发，记到 `blueprint/db-agent-vision.md`。
