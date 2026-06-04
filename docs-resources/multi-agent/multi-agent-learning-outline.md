# Step 3 Multi-Agent 学习大纲

> 目标：理解多 Agent 编排和通信模式，构建多 Agent 并发操作 rookieDB 的系统。
> 死锁原理（wait-for graph、BFS 找环、victim selection）属于 CS 基础，暂不纳入学习范围。

## 学习路径（3 阶段）

```
Phase 1: 概念              Phase 2: 动手              Phase 3: 应用到项目
  多 Agent 是什么          写多 Agent demo              多个 Agent 并发
  为什么需要多个 Agent     跑通编排和通信               操作 rookieDB
  核心编排模式             对比单 Agent 的差异          模拟真实并发场景
  ──────────────────────────────────────────────────→
         2 天                      2 天                      2 天
```

---

## Phase 1：多 Agent 概念（为什么需要、怎么编排）

### 主线教程：Microsoft ai-agents-for-beginners

> 跟 Step 2 用的 `mcp-for-beginners` 是同一系列，结构一致：每课有 README + 视频 + 可运行代码。
> **注意**：教程代码示例用 Azure AI Foundry / Microsoft Agent Framework，不是 Anthropic SDK。
> 我们**只学概念和设计模式**，代码实现用 Anthropic SDK。

**仓库**：[microsoft/ai-agents-for-beginners](https://github.com/microsoft/ai-agents-for-beginners)（65k+ stars，18 课）

**我们要学的课**：

| 课 | 内容 | 重要度 | 说明 |
|----|------|--------|------|
| Lesson 1 | Intro to AI Agents & Use Cases | ⭐ | 快速扫一遍，大部分已知 |
| Lesson 2 | Exploring Agentic Frameworks | ⭐ | 了解即可，我们已有技术栈 |
| Lesson 3 | Agentic Design Patterns | ⭐⭐⭐ | **核心**：工具使用、规划、多Agent 等设计模式 |
| Lesson 4 | Tool Use Design Pattern | ⭐⭐ | Step 1/2 已覆盖，复习 |
| Lesson 8 | Multi-Agent Design Pattern | ⭐⭐⭐ | **最重要**：多 Agent 协作模式 |
| Lesson 11 | Agentic Protocols (MCP, A2A) | ⭐⭐ | MCP 复习 + 了解 A2A，可选 |

**跳过**：Lesson 5-7, 9-10, 12-18（RAG、生产部署、安全等，跟 Step 3 目标无关）

---

### 补充资料 1：Anthropic 官方博客（SDK 层面）

**阅读**：[Anthropic: Building a Multi-Agent Research System](https://www.anthropic.com/engineering/multi-agent-research-system)

**为什么读**：Microsoft 教程讲的是通用模式，这篇是 Anthropic SDK 的实战经验。Orchestrator-Worker 架构、subagent 设计原则、工具设计 —— 直接对应我们用的 SDK。

**要搞清楚的问题**：
- 单 Agent vs 多 Agent：什么时候该拆分成多个 Agent？
- Orchestrator-Worker 架构：一个 Leader 拆任务 → 多个 Worker 并行执行
- Subagent 设计原则：每个 subagent 只管一件事（single responsibility）
- 跟我们现在做的事情什么关系？（死锁检测场景：多个 Agent 同时操作数据库，每个 Agent 独立决策）

### 补充资料 2：编排模式速查

**阅读**：[Claude Agentic Patterns](https://github.com/anthropics/claude-cookbooks/issues/303)

**7 种模式速查**：

| 模式 | 一句话 | 我们的场景 |
|------|--------|-----------|
| **Subagent Orchestration** | 主 Agent 拆任务，派给子 Agent 并行干 | 多个 Agent 各管各的事务 |
| **Prompt Chaining** | A 的输出 → B 的输入，串行流水线 | 先查 schema → 再生成 SQL → 再执行 |
| **Parallelization** | 多个 Agent 同时干不同的事 | 多个 Agent 同时操作不同表 |
| **Evaluator-Optimizer** | 一个生成，另一个审查 | Agent A 执行 SQL，Agent B 检查是否死锁 |
| **Routing** | 分类后路由到专门 Agent | 读请求 → Agent A，写请求 → Agent B |
| **Master-Clone** | 多实例共享同一上下文 | 多个 Agent 共享 DB 连接池 |
| **Programmatic Orchestration** | 代码控制 Agent 调度 | Python 脚本控制多 Agent 生命周期 |

### 补充资料 3：生产实践经验

**阅读**：[Claude Agent SDK Best Practices](https://skywork.ai/blog/claude-agent-sdk-best-practices-ai-agents-2025/)

**重点看**：
- 最小权限原则（每个 Agent 只给必要的 tool）
- 上下文隔离（Agent 之间不共享 messages）
- 错误处理（一个 Agent 挂了不影响其他）

---

## Phase 2：动手实践（写多 Agent demo）

### 2.1 从零写多 Agent 编排

**参考**：[AI Agents from Scratch](https://github.com/niket-sharma/AI-Agents-from-scratch)
- Tutorial 05：Advanced Patterns（多 Agent 协作，75-90 min）
- Tutorial 07：CrewAI Multi-Agent Teams（60-90 min，了解即可）

**目标**：写一个最简单的多 Agent demo —— 两个 Agent，一个负责生成 SQL，一个负责审查 SQL。

```
用户提问 → Agent A (生成SQL) → Agent B (审查SQL) → 执行 → 返回结果
```

**产出**：`step3-multi-agent/12_multi_agent_basic.py` — 两个 Agent 协作

### 2.2 多 Agent 并发模式

**目标**：多个 Agent 同时操作 rookieDB，各自独立的事务。

```
Agent A: BEGIN → UPDATE Students → ... → COMMIT
Agent B: BEGIN → UPDATE Courses → ... → COMMIT
（两个 Agent 同时执行，可能互相阻塞）
```

**核心要点**：
- 每个 Agent 独立的 Anthropic client + messages 历史
- Python `asyncio` 并发管理多个 Agent
- 观察：两个 Agent 同时操作同一张表会发生什么？

**产出**：`step3-multi-agent/13_concurrent_agents.py` — 多 Agent 并发

### 2.3 死锁场景复现（不检测，先制造）

**目标**：故意制造一个死锁场景，观察 rookieDB 的行为。

```
Agent A: BEGIN → UPDATE Students WHERE sid=1 → UPDATE Courses WHERE cid=1 → COMMIT
Agent B: BEGIN → UPDATE Courses WHERE cid=1 → UPDATE Students WHERE sid=1 → COMMIT
（A 等 B 释放 Courses 的锁，B 等 A 释放 Students 的锁 → 死锁）
```

**产出**：`step3-multi-agent/14_deadlock_scenario.py` — 死锁场景复现

---

## Phase 3：应用到项目（多 Agent → rookieDB）

### 3.1 设计：多 Agent 怎么共享 rookieDB

当前架构（单 Agent）：
```
Agent (Python) → MCP Client → MCP Server → execute_sql → socket → rookieDB
```

目标架构（多 Agent）：
```
Agent A (Python) ──→ MCP Client ──→ MCP Server ──→ socket ──→ rookieDB
Agent B (Python) ──→ MCP Client ──→ MCP Server ──→ socket ──→ rookieDB
Agent C (Python) ──→ MCP Client ──→ MCP Server ──→ socket ──→ rookieDB
```

**关键问题**：
- 多个 Agent 共享一个 MCP Server 还是各自一个？
- rookieDB 的连接池够不够？（每个 Agent 一个连接）
- Agent 之间要不要通信？（还是完全独立，死锁靠检测系统发现）

### 3.2 实现

**产出**：`step3-multi-agent/15_multi_agent_rookiedb.py` — 多 Agent 并发操作 rookieDB

具体步骤：
1. 改造 `11_agent_mcp_rookiedb.py`，支持启动多个 Agent 实例
2. 每个 Agent 独立的 MCP Client + 独立的 rookieDB 连接
3. 用 asyncio 并发执行多个 Agent
4. 观察并发行为（谁先完成？有没有阻塞？）

---

## 学习资料索引

### 概念层（跟 SDK 无关）

| 要学的内容 | 资料位置 | 优先级 |
|-----------|---------|--------|
| Agent 设计模式（主线教程） | [Microsoft ai-agents-for-beginners](https://github.com/microsoft/ai-agents-for-beginners) Lesson 1-4, 8, 11 | ⭐⭐⭐ |
| 多 Agent 设计模式详解 | Microsoft Lesson 8: Multi-Agent Design Pattern | ⭐⭐⭐ |

### 代码层（Anthropic SDK 专属）

| 要学的内容 | 资料位置 | 优先级 |
|-----------|---------|--------|
| Orchestrator-Worker 实战 | [Anthropic 官方博客](https://www.anthropic.com/engineering/multi-agent-research-system) | ⭐⭐⭐ |
| 7 种编排模式 + 代码示例 | [Claude Agentic Patterns](https://github.com/anthropics/claude-cookbooks/issues/303) | ⭐⭐⭐ |
| 生产级实践（权限、隔离、容错） | [Claude Agent SDK Best Practices](https://skywork.ai/blog/claude-agent-sdk-best-practices-ai-agents-2025/) | ⭐⭐ |
| 从零写多 Agent（渐进式教程） | [AI Agents from Scratch](https://github.com/niket-sharma/AI-Agents-from-scratch) | ⭐⭐ |

### 备查

| 资料 | 说明 |
|------|------|
| [PicoAgents](https://pypi.org/project/picoagents/) | 第一性原理 + 50+ 示例，不需要时不用看 |

## 跳过清单

- ❌ Microsoft Lesson 5-7, 9-10, 12-18（RAG、生产部署、安全等，跟 Step 3 目标无关）
- ❌ CrewAI / AutoGen / LangChain 多 Agent 框架（我们用原生 Anthropic SDK）
- ❌ Google ADK / A2A 协议（Google 生态，跟我们没关系）
- ❌ 死锁检测算法（CS 基础，后补）
- ❌ 云端部署 / 生产监控
- ❌ Multi-Agent RL（强化学习，跟我们的场景无关）
