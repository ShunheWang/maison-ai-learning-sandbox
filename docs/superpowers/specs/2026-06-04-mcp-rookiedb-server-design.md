# Spec: Phase 3 — execute_sql 包装为 MCP Tool

**状态**：待审批
**日期**：2026-06-04

---

## 目标

把 Step 1 的 `execute_sql` + `RookieDBConnection` 从 Agent 代码里拆出来，变成独立的 MCP Server。Agent 通过 MCP Client + LLM 自然语言操作 rookieDB。

核心验证：工具定义和执行在 Server 进程，Agent 只管发现和转发——MCP 解耦原则落地。

## 范围

### 做

- `10_rookiedb_mcp_server.py` — MCP Server，包含：
  - `RookieDBConnection` 类（从 06 复制，自包含）
  - `@mcp.tool() execute_sql(sql)` — 数据库操作
  - `@mcp.resource("database://schema")` — 表结构信息
  - 启动时连接 rookieDB，失败则打印警告继续运行
- `11_agent_mcp_rookiedb.py` — Agent + MCP Client，包含：
  - 自动启动 10 Server（StdioServerParameters）
  - `list_tools()` 发现工具 + `read_resource()` 获取 schema
  - Schema 注入 System Prompt
  - Agent 循环：LLM 判断 → `call_tool()` → Server 执行 → 结果回传
  - API 调用重试（指数退避，复用 06 的 `call_claude_with_retry` 模式）
- 工具调用异常 try/except（is_error 标记传回 LLM）
- 端到端测试：rookieDB 运行状态下，自然语言查 Students 表

### 不做

- 连接池、并发连接（留到 Step 3 多 Agent）
- 连接池、并发连接（留到 Step 3 多 Agent）
- 修改 06 或 Step 1 任何文件（独立文件，不破坏已有代码）
- 处理 rookieDB 断线后的重连（06 的 reconnect 代码复制过来直接用）

## 架构

```
11_agent_mcp_rookiedb.py (Agent + MCP Client)
  │
  │ StdioServerParameters → 自动启动 10 Server
  │
  ├── list_tools()      → 发现 execute_sql
  ├── read_resource()   → 获取 schema → System Prompt
  │
  │ Agent 循环:
  │   用户输入 → LLM 判断 → call_tool("execute_sql", {sql: ...})
  │   → Server 执行 → 结果回传 → LLM 回复
  │
  └── STDIO / JSON-RPC ──→ 10_rookiedb_mcp_server.py (MCP Server)
                               │
                               ├── RookieDBConnection
                               │     └── TCP socket :18600 → rookieDB (Java)
                               │
                               ├── @mcp.tool() execute_sql
                               └── @mcp.resource() database://schema
```

## 关键决策

| 决策 | 选择 | 原因 |
|------|------|------|
| RookieDBConnection 来源 | 复制到 10 | 06 文件名以数字开头无法 import，且学习文件应自包含 |
| 连接时机 | 启动时连接 | 启动就能发现问题，不等第一次查询报错 |
| 表结构信息 | MCP Resource | 用上 Resource 原语，Server 是 schema 权威源 |
| 错误处理 | 保留在 Server | Agent 不知道 socket 存在，Server 封装所有 DB 细节 |

<br>

## 文件设计

### 10_rookiedb_mcp_server.py

```
配置 (HOST/PORT)
  ↓
RookieDBConnection 类（connect, execute, _reconnect, _recv_until_prompt, close, is_connected）
  ↓
mcp = FastMCP("rookieDB")
  ↓
@mcp.tool() execute_sql(sql: str) → str
  ├── db 未连接 → 返回错误信息
  ├── db.execute(sql) → 结果文本
  └── 异常 → 返回错误信息
  ↓
@mcp.resource("database://schema") → str
  └── 返回 Students/Courses/Enrollments 表结构
  ↓
main: db.connect() → mcp.run()
```

### 11_agent_mcp_rookiedb.py

```
加载 .env + Anthropic Client
  ↓
server_params → stdio_client → ClientSession
  ↓
session.initialize()
  ↓
list_tools() → mcp_tool_to_anthropic()
read_resource("database://schema") → schema_text
  ↓
System Prompt = 基础提示 + schema_text
  ↓
用户输入 → Agent 循环
  ├── LLM 判断 (stop_reason == "tool_use"?)
  ├── session.call_tool("execute_sql", {sql: ...})
  │     └── try/except: 异常 → is_error tool_result
  ├── tool_result 塞回 messages
  └── 循环直到 end_turn
```

## 测试场景

| 场景 | 前置条件 | 输入 | 预期 |
|------|---------|------|------|
| 正常查询 | rookieDB 运行 | "列出所有学生" | Agent 自动调 execute_sql，返回学生列表 |
| rookieDB 未启动 | rookieDB 未运行 | 任意查询 | Agent 收到连接错误，LLM 告知用户 |
| SQL 错误 | rookieDB 运行 | 查不存在的表 | execute_sql 返回 DB 错误，LLM 告知用户 |
| 多步查询 | rookieDB 运行 | 复杂问题 | LLM 可能多次调 execute_sql |

## 验证方式

```bash
# 1. 启动 rookieDB
cd /Users/shunhewang/melbourne/cs186/berkeley-sp26-rookiedb
java -cp target/classes edu.berkeley.cs186.database.cli.Server &

# 2. 测试 MCP Server（可选）
mcp dev step2-mcp/10_rookiedb_mcp_server.py

# 3. 端到端
python3 step2-mcp/11_agent_mcp_rookiedb.py
```