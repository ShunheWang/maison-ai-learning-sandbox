# Spec: 单元 4 — 接上 rookieDB

**状态**：待审批
**日期**：2026-06-02

---

## 目标

把 `03_agent_loop.py` 的 mock 数据替换成真实 rookieDB socket 连接，打通"自然语言 → SQL → 真实数据库 → 自然语言回复"端到端链路，并通过完整 CRUD 场景验证。

## 范围

### 做

- 新文件 `04_connect_rookiedb.py`，独立完整的学习单元
- 封装 `RookieDBConnection` 类，管理 socket 连接
- `execute_sql()` 走真实 rookieDB
- 启动时连接，结束时断开，整个会话复用连接
- 8 个 CRUD 场景验证（Create × 1, Read × 4, Update × 1, Delete × 1 + 每条操作附带 Read 验证）

### 不做

- 连接重试、超时处理（留到单元 6 错误处理）
- 连接池、并发连接（留到 Step 3 多 Agent）
- Agent 循环架构变更（照搬 03）
- Tool 定义变更（除非需要修正 description 中关于 DDL 的错误）

## 架构

```
┌─ 04_connect_rookiedb.py ─────────────┐
│                                       │
│  RookieDBConnection                   │
│    ├─ connect()    跳过欢迎信息        │
│    ├─ execute(sql) 发送 SQL，读结果    │
│    └─ close()      发送 exit，断开    │
│                                       │
│  execute_sql(sql)                     │
│    └─ 调用 db.execute(sql)            │
│                                       │
│  run_agent(question)                  │
│    └─ 跟 03 一样的 Agent 循环         │
│                                       │
│  __main__:                            │
│    connect → 8 场景 → close           │
└──────────────┬────────────────────────┘
               │ TCP socket :18600
┌──────────────▼────────────────────────┐
│  rookieDB Server (Java)               │
│  demo 数据: Students/Courses/         │
│            Enrollments                │
└───────────────────────────────────────┘
```

## RookieDBConnection 设计

```
class RookieDBConnection:
    HOST = "localhost"
    PORT = 18600

    __init__()
        → sock = None

    connect()
        → 建立 socket，跳过欢迎信息（读到第一个 "=> "）
        → 设置 sock.settimeout(10)
        → 打印 "🔌 已连接 rookieDB"

    execute(sql) → str
        → sock.send(sql + "\n")
        → 循环 recv(4096) 直到收到 "=> "
        → 去掉末尾 "=> "，返回纯结果

    close()
        → sock.send(b"exit\n")
        → sock.close()
        → 打印 "🔌 已断开 rookieDB"
```

## Agent 循环

照搬 `03_agent_loop.py` 的核心逻辑：

```python
def run_agent(user_question):
    messages = [{"role": "user", "content": user_question}]
    
    while True:
        response = client.messages.create(
            model="deepseek-v4-pro",
            max_tokens=500,
            system="你是一个数据库管理助手...",
            messages=messages,
            tools=[execute_sql_tool],
        )
        
        if response.stop_reason != "tool_use":
            break
        
        # 追加 assistant 消息
        # 执行工具 → tool_result 塞回
        # 继续循环
```

## Tool 定义

修正之前错误的 DDL 限制声明，跟 rookieDB 实际能力对齐：

```python
execute_sql_tool = {
    "name": "execute_sql",
    "description": (
        "在 rookieDB 数据库上执行一条 SQL 语句。"
        "支持 SELECT、INSERT、UPDATE、DELETE 操作。"
        "也支持 CREATE TABLE、DROP TABLE 等 DDL 操作。"
        "查询结果以表格形式返回。"
        "当用户需要查询、插入、更新或删除数据时使用此工具。"
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "sql": {
                "type": "string",
                "description": "要执行的 SQL 语句。"
            }
        },
        "required": ["sql"]
    }
}
```

## 验证场景（8 步 CRUD）

| 步骤 | 操作 | Agent 提问 | 验证点 |
|------|------|-----------|--------|
| 1 | Read | 查数据库里有哪些表 | 能看到 Students、Courses、Enrollments |
| 2 | Read | 查 Students 表里 CS 专业的学生 | WHERE 条件正常 |
| 3 | Create | 插入学号 999 的测试学生 | INSERT 成功 |
| 4 | Read | 查学号 999 的学生 | 验证插入结果 |
| 5 | Update | 把学号 999 的 GPA 改成 4.0 | UPDATE 成功 |
| 6 | Read | 确认学号 999 的 GPA | 验证更新结果 |
| 7 | Delete | 删除学号 999 的学生 | DELETE 成功 |
| 8 | Read | 确认学号 999 不存在 | 验证删除结果 |

## 前置依赖

- rookieDB Server 已启动（`java -cp target/classes edu.berkeley.cs186.database.cli.Server`）
- `.env` 里有 API key 和 base URL
- Python 环境已装 `anthropic` 包

## 学习产出

| 学到的东西 | 关键概念 |
|-----------|---------|
| Python socket 连 Java 进程通信 | subprocess / socket |
| 把 mock 替换成真实数据库 | 关注点分离 |
| 端到端：自然语言 → SQL → 真实结果 → 自然语言回复 | Agent Tool Calling |
| 单连接复用模式 | 连接生命周期 |
