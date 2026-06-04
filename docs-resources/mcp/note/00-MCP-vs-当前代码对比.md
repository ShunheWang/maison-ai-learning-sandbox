# MCP 实战对比：单工具 vs 多工具（结合我们的代码）

> 读完 Module 0 后的关键理解：MCP 怎么解决"定义多个函数"的问题

---

## 现状：我们目前的写法（04_connect_rookiedb.py）

### 目前的 3 个步骤

```
步骤 1: 手工定义 JSON Schema
步骤 2: 手工写函数实现
步骤 3: Agent 循环里手工 if/elif 分发
```

具体代码：

```python
# 步骤 1：手工定义 Tool JSON Schema
execute_sql_tool = {
    "name": "execute_sql",
    "description": "在 rookieDB 上执行 SQL...",
    "input_schema": { ... }
}

# 步骤 2：手工写函数
def make_execute_sql(db):
    def execute_sql(sql):
        return db.execute(sql)
    return execute_sql

# 步骤 3：Agent 循环里手工分发
tools=[execute_sql_tool]  # 传给 Claude

# ... Claude 返回 tool_use 后 ...
for tool_use in tool_uses:
    if tool_use.name == "execute_sql":          # ← 硬编码分发
        result = execute_sql_fn(tool_use.input["sql"])
    # elif tool_use.name == "another_tool":     # ← 每加一个工具就要加一个 elif
    #     result = another_fn(...)
```

---

## 问题：如果要加第 2 个工具怎么办

比如加一个 `show_tables` 工具（列出所有表）。目前需要改 **3 个地方**：

```python
# 1. 新定义一个 JSON Schema
show_tables_tool = {
    "name": "show_tables",
    "description": "列出数据库中所有表",
    ...
}

# 2. 新写一个函数
def show_tables():
    return db.execute("SELECT * FROM _metadata.tables;")

# 3. Agent 循环里加一个 elif
for tool_use in tool_uses:
    if tool_use.name == "execute_sql":
        ...
    elif tool_use.name == "show_tables":    # ← 新加的
        result = show_tables()

# 另外还要改 tools 列表
tools=[execute_sql_tool, show_tools_tool]  # ← 新加的
```

**每加一个工具，Agent 代码就要膨胀一次。** 10 个工具就是 10 个 JSON Schema + 10 个函数 + 10 个 if/elif。

---

## MCP 方式：工具定义和 Agent 代码完全分离

### MCP 的架构

```
┌─────────────────────────┐     ┌─────────────────────────┐
│ Agent (Python)          │     │ MCP Server (独立进程)     │
│                         │     │                         │
│ 不定义任何工具！         │     │ 定义所有工具：            │
│ 只做一件事：            │     │   execute_sql           │
│   tools/list → 发现工具  │     │   show_tables           │
│   tools/call → 调用工具  │     │   describe_table        │
│                         │     │   get_schema            │
│                         │     │   ...随你加...           │
└─────────────────────────┘     └─────────────────────────┘
         │                              │
         │  MCP 协议 (JSON-RPC)          │
         └──────────────────────────────┘
```

### MCP 方式下 Agent 的代码

```python
# Agent 代码：不再定义任何工具！
# 不再有 JSON Schema，不再有函数实现，不再有 if/elif

# 1. 发现 Server 有什么工具
tools = mcp_client.list_tools()  # → 自动拿到所有工具的 JSON Schema

# 2. 把工具列表传给 Claude
response = client.messages.create(
    messages=messages,
    tools=tools,              # ← 自动从 Server 拿到的，不用手写
)

# 3. Claude 说要调哪个工具，直接转发给 Server
for tool_use in tool_uses:
    result = mcp_client.call_tool(      # ← 不分发，直接转发
        name=tool_use.name,             # ← Server 自己知道怎么执行
        arguments=tool_use.input
    )
```

**加新工具只需要改 MCP Server，Agent 代码一行不动。**

---

## 关键认知

| | 现在的方式 | MCP 方式 |
|---|---|---|
| 工具定义在哪 | 跟 Agent 代码混在一起 | 独立的 MCP Server |
| 加新工具要改什么 | Agent 代码（3 处手动改） | 只改 Server，Agent 不动 |
| 工具发现 | 手工维护 `tools=[...]` 列表 | `tools/list` 自动返回 |
| 工具调用 | `if tool_use.name == "xxx"` | `mcp_client.call_tool(name, args)` |
| 复用 | 其他 Agent 用不了 | 任何 MCP Client 都能用 |

**MCP 的核心价值就是这个**：工具提供方（Server）和工具消费方（Agent/Client）解耦。这就是为什么 Anthropic 推 MCP——不用每个项目都手写一套 tool calling 胶水代码。

---

## Step 2 的目标

把我们现在的 `execute_sql` 从 Agent 代码里拆出去，变成独立 MCP Server：

```
现在：
  Agent → execute_sql() → socket → rookieDB
  （函数跟 Agent 代码混在一起）

Step 2 后：
  Agent → MCP Client → MCP Server → execute_sql() → socket → rookieDB
  （工具独立运行，Agent 通过 MCP 协议调用）
```

后续要加 `show_tables`、`describe_table`、`get_lock_info`（死锁检测用）……只要往 MCP Server 里加就行，Agent 代码不用动。
