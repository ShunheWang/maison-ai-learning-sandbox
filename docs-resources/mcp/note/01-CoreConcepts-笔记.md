# MCP 核心概念：Client-Server 架构、消息协议、三大原语

> 来源：mcp-for-beginners Module 1 — Core Concepts
> 整理时间：2026-06-04

---

## 一句话总结

**MCP 是一个基于 JSON-RPC 2.0 的 Client-Server 协议，Host 通过 Client 连 Server，Server 暴露 Tools/Resources/Prompts 三种能力。**

---

## 1. 架构：三大角色（比 Module 0 更精确的定义）

```
┌──────────────────────────────────┐
│ Host（宿主应用）                  │
│  e.g. Claude Desktop, VS Code,   │
│  我们的 03_agent_loop.py         │
│                                  │
│  ┌────────┐  ┌────────┐         │
│  │Client A│  │Client B│  ...     │  ← 每个 Client 1:1 连一个 Server
│  └───┬────┘  └───┬────┘         │
└──────┼───────────┼──────────────┘
       │ STDIO     │ STDIO
┌──────┴──┐  ┌─────┴───┐
│Server A │  │Server B │            ← 独立进程，暴露工具/数据/提示词
│  execute_sql        │
│  show_tables        │
└─────────┘  └─────────┘
```

| 角色 | 干什么 | 关键点 |
|------|--------|--------|
| **Host** | 运行 LLM 的应用，管理 UI 和用户交互 | Host 不是 Agent 本身，是**运行 Agent 的环境** |
| **Client** | 协议连接器，Host 内部创建，跟 Server 1:1 | 负责 JSON-RPC 通信、能力协商、转发请求 |
| **Server** | 独立进程，暴露具体能力 | 工具的执行者，对 LLM 和 Agent 逻辑一无所知 |

**Host 包含 Client，Client 连接 Server**。一个 Host 可以同时连多个 Server。

Host 的 5 个职责（来自官方定义）：
- **编排 AI 模型**：执行 LLM 调用、协调 Agent 工作流
- **管理 Client 连接**：每连一个 Server 就创建一个 Client
- **控制用户界面**：处理对话流、用户交互、回复展示
- **执行安全策略**：控制权限、安全约束、认证
- **处理用户同意**：数据共享和工具执行前需要用户确认

---

## 2. Server 三种原语（Tool/Resource/Prompt 的精确定义）

### 2.1 Tools — 可执行函数（"动词"）

**LLM 调用来"做事情"**。每个 Tool 有唯一名称、参数 JSON Schema、返回结构化数据。

```
tools/list   → 发现有哪些工具
tools/call   → 调用指定工具
```

支持 **Tool Annotations**：工具可以标注自己的行为属性，让 Client 做更智能的权限判断：

| 标注 | 含义 | 例子 |
|------|------|------|
| `readOnlyHint` | 提示 Client 这个工具只读不写 | SELECT 查询 |
| `destructiveHint` | 提示 Client 这个工具有破坏性操作 | DROP TABLE、DELETE |
| `idempotentHint` | 提示 Client 这个工具重复调结果一样 | 幂等更新 |

Client 可以基于这些标注决定要不要弹窗确认、要不要限流。

```python
@mcp.tool()
def get_weather(location: str) -> dict:
    """Gets current weather for a location."""
    return {"temperature": 72.5, "conditions": "Sunny", "location": location}
```

### 2.2 Resources — 数据源（"名词"）

**给 LLM 提供上下文信息**，只读。用 URI 标识，支持动态内容。

```
resources/list  → 发现有哪些数据
resources/read  → 读取指定资源
```

URI 示例：
```
file://documents/project-spec.md
database://production/users/schema
api://weather/current
```

### 2.3 Prompts — 提示词模板（"话术"）

**预定义的交互模板**，支持变量替换，可参数化。跟 System Prompt 不同，Prompt 是**可被用户选择的对话模板**。和 Tool、Resource 一样，Prompt 也是我们在 Server 代码里注册的。

```
prompts/list → 发现有哪些模板
prompts/get  → 获取指定模板（可传参数替换变量）
```

示例：
```markdown
Generate a {{task_type}} for {{product}} targeting {{audience}}
```

对我们当前项目用处不大——System Prompt 已经在 Host 脚本里写好了，不需要放到 Server 里。

### 对应我们的项目

| 原语 | 对应什么 |
|------|---------|
| Tools | `execute_sql`（现有）、`show_tables`、`get_lock_info`（未来） |
| Resources | 表结构信息、schema |
| Prompts | 可选的，System Prompt 模板化 |

---

## 3. Client 也能暴露能力给 Server（反向调用）

### 设计哲学：Server 是有意"残缺"的

MCP 的设计者刻意让 Server 只做一件事：**执行工具、返回结果**。Server 进程里有这些东西：

```
✅ 工具实现（execute_sql 的代码）
✅ 数据库连接（socket → rookieDB）
✅ 参数校验（JSON Schema）
```

但 Server 进程里**故意没有**这些东西：

```
❌ LLM — 模型在 Host 那边
❌ UI  — 用户跟 Host 交互，不跟 Server
❌ 文件系统权限 — 只有 Host 知道能碰哪些目录
❌ 日志基础设施 — Host 才知道日志往哪存
```

**这 4 个 Client Primitives 就是对这 4 个缺失的补位通道**——Server 缺什么，就通过对应方法回头找 Host 要。

### 设计本质：单一职责做到协议层

```
Server 关心的           Server 不关心的
───────────           ──────────────
这个工具怎么执行        谁调了我
参数对不对             结果怎么展示
返回什么数据           结果记录到哪
执行安全不安全          用户同意了没有
```

Server 的哲学：**"我负责把活干好，其他事情你们自己处理。"** 不关心的事正好由 4 个 Client Primitives 补上——不是强制补，而是"你需要的时候有这个通道"。

这就是 MCP 设计最精巧的地方：Server 是纯工具执行者，不绑定模型、不依赖 UI、不假设日志存储——够纯粹，才够通用。

### 四种反向能力详解

| 能力 | Server 缺什么 | 反过来说 | 我们项目用吗 |
|------|-------------|---------|------------|
| **Sampling** | 没有 LLM | "借你模型用一下" | ❌ |
| **Roots** | 不知道权限边界 | "告诉我能碰哪些目录" | ❌ |
| **Elicitation** | 没有 UI | "帮我问一下用户" | ❌ |
| **Logging** | 没有日志系统 | "帮我记一下" | ⭐ 可能 |

### 每个能力一句话场景

- **Sampling**：Server 执行中间步骤需要 LLM 帮忙（比如把原始死锁数据翻译成人话），Server 自己不内嵌模型，通过协议借用 Host 的
- **Roots**：Server 需要读写文件时，先问 Host "我能碰哪些目录"，安全边界由 Host 定义
- **Elicitation**：Server 知道删表是危险操作，但没界面弹窗，通过协议让 Host 向用户确认
- **Logging**：Server 只管"我要记这个"（慢查询、错误），不管"记到哪"，Host 决定存储策略

**核心认知**：这 4 个是"锦上添花"，不是 MCP 的基础骨架。我们项目用 Tool 的 list + call 就够了（MCP 最核心的 20% 功能），剩下 80% 知道存在、理解设计意图就行。

---

## 4. 协议分层 + 消息格式

### 两层架构

```
┌─────────────────────────┐
│ 数据层（JSON-RPC 2.0）   │  消息格式、请求/响应/通知、生命周期管理
├─────────────────────────┤
│ 传输层                   │
│  STDIO（本地进程通信）     │
│  Streamable HTTP（远程）  │
└─────────────────────────┘
```

传输层对数据层透明，同一个 JSON 格式在不同传输方式下通用。

### JSON-RPC 2.0 三种消息

| 类型 | 格式 | 需要回复？ |
|------|------|-----------|
| **Request** | `{jsonrpc: "2.0", id: 1, method: "tools/call", params: {...}}` | ✅ 必须有 Response |
| **Response** | `{jsonrpc: "2.0", id: 1, result: {...}}` 或 `{..., error: {...}}` | — |
| **Notification** | `{jsonrpc: "2.0", method: "notifications/tools/list_changed"}` | ❌ 不需要回复，无 id |

### 5 类消息按功能分

| 类别 | 方法 | 方向 |
|------|------|------|
| **初始化** | `initialize`、`notifications/initialized` | Client ⇄ Server |
| **发现** | `tools/list`、`resources/list`、`prompts/list` | Client → Server |
| **执行** | `tools/call`、`resources/read`、`prompts/get` | Client → Server |
| **Client 能力** | `sampling/complete`、`elicitation/request` | Server → Client |
| **通知** | `notifications/tools/list_changed` 等 | Server → Client |

---

## 5. 一次完整调用的信息流（7 步）

用我们的项目做例子：

```
阶段 1-2：握手
─────────────────────────────
1. Host 启动 MCP Server 子进程（STDIO 通信）
2. Client ↔ Server 能力协商
   Client → initialize {protocolVersion: "2025-11-25", capabilities: {tools: {}}}
   Server → initialize response {serverInfo: {...}, capabilities: {tools: {}}}
   Client → notifications/initialized

—— 握手完成，进入循环 ——

阶段 3：用户输入
─────────────────────────────
3. 用户在 Host 界面输入："列出 GPA 最高的 3 个学生"
   Host 把这句话 + 工具列表一起发给 LLM

阶段 4-5：工具调用
─────────────────────────────
4. LLM 判断：需要查数据库 → 决定调 execute_sql
   LLM 输出 tool_use {name: "execute_sql", input: {sql: "SELECT * FROM Students ORDER BY gpa DESC LIMIT 3"}}
   Host 收到 → Client → tools/call → Server

5. Server 收到请求 → 执行 socket.send(sql) → 拿到结果 → 返回给 Client
   Server 返回: {content: [{type: "text", text: "张三 4.0\n李四 3.9\n王五 3.8"}]}

阶段 6-7：回复 + 展示
─────────────────────────────
6. Host 把结果塞回给 LLM
   LLM："GPA 最高的 3 个学生是：张三 (4.0), 李四 (3.9), 王五 (3.8)"

7. Host 展示给用户

—— 会话结束 ——
8. 连接关闭，Server 进程终止
```

### 跟我们现在代码的对比

```
现在（03_agent_loop.py）              MCP 方式
─────────────────────               ────────────────
连接：没有握手，直接 socket 连接      initialize 握手 + 能力协商
工具发现：手工写 tools=[{...}]        tools/list 自动拿
工具调用：调 Python 函数               JSON-RPC tools/call
  execute_sql(sql)                     → MCP Server 执行
返回结果：函数 return                  JSON-RPC Response
```

逻辑完全一样，区别只在：**原来直接调 Python 函数，现在通过 JSON-RPC 调独立进程。**

---

## 6. 安全机制（4 层）

| 机制 | 干什么 |
|------|--------|
| **权限控制** | Client 可限制 LLM 能用哪些 Tool |
| **认证** | Server 可要求 API key / OAuth token |
| **参数校验** | Tool 定义 JSON Schema，Server 自动校验入参 |
| **限流** | 防止滥用，按用户/会话/全局限流 |

这 4 层对当前学习阶段不重要，但知道了为什么 MCP 设计成 Client-Server 分离——**安全边界天然存在**。

---

## 7. 版本 + Tasks（简单知道）

- **协议版本**：日期制 `2025-11-25`，不是语义化版本
- **Tasks（实验性）**：给长时间运行的操作做异步状态追踪，当前不需要

---

## 8. 关键认知

1. **MCP 没有魔法**，就是一套基于 JSON-RPC 2.0 的消息协议，规定了 Host/Client/Server 三个角色的通信方式
2. **Host ≠ Client**，Host 是应用，Client 是连接器。Host 内部可以创建多个 Client 连不同的 Server
3. **Server 不知道 LLM 的存在**，它只知道"收到参数 → 执行 → 返回结果"。LLM 的调用和管理完全是 Host 的事
4. **对我们 Step 2**：要改的地方是——把 `execute_sql` 从 Agent 文件里的一个函数，变成一个独立进程（MCP Server），Agent 通过 JSON-RPC 调它
5. **Client 原语（Sampling/Roots/Elicitation/Logging）暂时不用**，Server 原语中我们主要用 Tool，Resource 和 Prompt 后续按需加

### 核心心智模型：判断、转发、执行三者分离

```
用户自然语言输入
      │
      ▼
┌─ LLM（做判断）─────────┐
│ "他想查 GPA"           │
│ "需要 execute_sql"     │  ← 选工具 + 填参数
│ "SELECT * FROM ..."   │
└───────────┬───────────┘
            │ Host 拿到 LLM 的决定，不自己判断
            ▼
┌─ Host/Client（转发）───┐
│ tools/call → Server   │  ← 只转发，不做任何逻辑
└───────────┬───────────┘
            │ JSON-RPC via STDIO
            ▼
┌─ MCP Server（执行）────┐
│ socket.send(sql)      │  ← 真正干活，连 rookieDB
│ 返回结果               │
└────────────────────────┘
```

**判断的是 LLM，转发的是 Host/Client，执行的是 Server。** 没有一个角色代劳另一个。

Server 不只是"列出工具有哪些"——它是工具的容器和运行环境。`execute_sql` 的代码、rookieDB 的 socket 连接，全在 Server 进程里。要想通这个：我们现在 `03_agent_loop.py` 里 `execute_sql()` 函数的所有代码，包括 `RookieDBConnection`，都要搬到 Server 进程里去。

---
