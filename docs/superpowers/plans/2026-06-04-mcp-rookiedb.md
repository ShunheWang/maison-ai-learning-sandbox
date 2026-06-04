# Phase 3: execute_sql → MCP Tool 实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 把 Step 1 的 `execute_sql` + `RookieDBConnection` 拆成独立 MCP Server，Agent 通过 MCP 自然语言操作 rookieDB

**Architecture:** 两个独立 Python 文件。10 = MCP Server（socket + rookiedb + schema resource），11 = Agent + MCP Client + LLM（发现工具、获取 schema、自然语言查询）。10 是工具提供方，11 是工具消费方，通过 STDIO + JSON-RPC 通信

**Tech Stack:** Python 3, FastMCP (Server), mcp SDK (Client), Anthropic SDK (LLM), TCP socket (rookieDB)

**Spec:** `docs/superpowers/specs/2026-06-04-mcp-rookiedb-server-design.md`

---

## 文件结构

| 文件 | 职责 | 创建/复用 |
|------|------|---------|
| `step2-mcp/10_rookiedb_mcp_server.py` | MCP Server：封装 rookieDB 连接 + execute_sql 工具 + schema 资源 | 创建 |
| `step2-mcp/11_agent_mcp_rookiedb.py` | Agent + MCP Client：发现工具、获取 schema、Agent 循环、API 重试 | 创建 |

复用关系：
- 从 `step1-agent-toolcalling/06_error_handling.py` 复制 `RookieDBConnection` 类
- 从 `step2-mcp/09_agent_with_mcp.py` 参考 Agent 循环 + `mcp_tool_to_anthropic` 模式
- 从 `step2-mcp/07_first_mcp_server.py` 参考 FastMCP Server 模式

---

### Task 1: 建立 10_rookiedb_mcp_server.py 骨架

**Files:**
- Create: `step2-mcp/10_rookiedb_mcp_server.py`

- [ ] **Step 1: 创建文件框架**

```python
"""
10_rookiedb_mcp_server.py — MCP Server for rookieDB

学习点：
  - 把原有 TCP socket 服务包装成 MCP Tool
  - @mcp.tool() 注册数据库操作工具
  - @mcp.resource() 暴露数据库 schema
  - Server 管理连接生命周期（启动连接、断线重连）
  - Agent 不知道 socket 存在，只看到 MCP 接口

运行：
  python3 step2-mcp/10_rookiedb_mcp_server.py
  mcp dev step2-mcp/10_rookiedb_mcp_server.py  # 可视化测试
"""

import socket
import sys
import time
from mcp.server.fastmcp import FastMCP

# ============================================================
# 配置
# ============================================================
ROOKIEDB_HOST = "localhost"
ROOKIEDB_PORT = 18600

# ============================================================
# RookieDBConnection（从 06 复制，自包含）
# ============================================================
# （Task 2 填充）

# ============================================================
# FastMCP Server 实例
# ============================================================
mcp = FastMCP("rookieDB")

# （Task 3 填充工具和资源）

# ============================================================
# 启动
# ============================================================
if __name__ == "__main__":
    # （Task 4 填充启动逻辑）
    mcp.run()
```

- [ ] **Step 2: 运行验证骨架能启动**

```bash
python3 step2-mcp/10_rookiedb_mcp_server.py
```
Expected: Server 启动（因工具未注册会报空 Server 错误，正常，后续 Task 补）

- [ ] **Step 3: Commit**

```bash
git add step2-mcp/10_rookiedb_mcp_server.py
git commit -m "feat: 10_rookiedb_mcp_server.py 骨架"
```

---

### Task 2: 复制 RookieDBConnection 类

**Files:**
- Modify: `step2-mcp/10_rookiedb_mcp_server.py`

- [ ] **Step 1: 从 06 复制完整的 RookieDBConnection 类，并添加 is_connected()**

在 `# RookieDBConnection` 注释下方插入：

```python
class RookieDBConnection:
    """管理 rookieDB 的 socket 连接，支持自动重连"""

    def __init__(self, host=ROOKIEDB_HOST, port=ROOKIEDB_PORT):
        self.host = host
        self.port = port
        self.sock = None
        self._reconnect_count = 0

    def connect(self):
        """建立 TCP 连接并等待欢迎提示"""
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.settimeout(10)
        self.sock.connect((self.host, self.port))
        self._recv_until_prompt()
        print(f"[rookieDB] 已连接 {self.host}:{self.port}", file=sys.stderr)

    def execute(self, sql: str) -> str:
        """执行 SQL，自动加 ';'，断线自动重连一次"""
        if self.sock is None:
            raise ConnectionError("未连接 rookieDB，请先调用 connect()")
        if not sql.strip().endswith(";"):
            sql += ";"

        try:
            self.sock.send((sql + "\n").encode("utf-8"))
            response = self._recv_until_prompt()
            return response.strip()
        except (socket.timeout, ConnectionError, OSError) as e:
            print(f"[rookieDB] 连接异常，尝试重连: {e}", file=sys.stderr)
            self._reconnect()
            self.sock.send((sql + "\n").encode("utf-8"))
            response = self._recv_until_prompt()
            return response.strip()

    def _reconnect(self):
        """关闭旧连接，建立新连接"""
        self._reconnect_count += 1
        try:
            self.sock.close()
        except Exception:
            pass
        self.sock = None
        time.sleep(0.5)
        self.connect()
        print(f"[rookieDB] 重连成功 (第 {self._reconnect_count} 次)", file=sys.stderr)

    def _recv_until_prompt(self) -> str:
        """收数据直到看到 '=> ' 提示符"""
        data = b""
        while True:
            chunk = self.sock.recv(4096)
            if not chunk:
                break
            data += chunk
            if b"=> " in data:
                break
        return data.decode("utf-8", errors="replace")

    def close(self):
        """发送 exit 命令并关闭连接"""
        if self.sock:
            try:
                self.sock.send(b"exit\n")
            except Exception:
                pass
            self.sock.close()
            self.sock = None
            print("[rookieDB] 已断开连接", file=sys.stderr)

    def is_connected(self) -> bool:
        """检查连接是否活跃"""
        return self.sock is not None
```

- [ ] **Step 2: 验证导入**

```bash
python3 -c "exec(open('step2-mcp/10_rookiedb_mcp_server.py').read().split('if __name__')[0]); print('导入成功')"
```

Expected: 无错误，打印"导入成功"

- [ ] **Step 3: Commit**

```bash
git add step2-mcp/10_rookiedb_mcp_server.py
git commit -m "feat: 添加 RookieDBConnection 类到 10"
```

---

### Task 3: 注册 execute_sql 工具 + schema 资源

**Files:**
- Modify: `step2-mcp/10_rookiedb_mcp_server.py`

- [ ] **Step 1: 在 `mcp = FastMCP("rookieDB")` 后添加工具和资源**

```python
# ============================================================
# 数据库连接（模块级变量，启动时初始化）
# ============================================================
_db: RookieDBConnection | None = None


def get_db() -> RookieDBConnection | None:
    return _db


# ============================================================
# MCP Tool: execute_sql
# ============================================================
@mcp.tool()
def execute_sql(sql: str) -> str:
    """Execute a SQL statement on the rookieDB database.

    Supports SELECT, INSERT, UPDATE, DELETE, CREATE TABLE, DROP TABLE.
    The database contains three tables:
      Students (sid, name, major, gpa)
      Courses (cid, name, department)
      Enrollments (sid, cid)
    """
    db = get_db()
    if db is None or not db.is_connected():
        return (
            "ERROR: Cannot connect to rookieDB on localhost:18600. "
            "Please ensure the rookieDB server is running."
        )
    try:
        result = db.execute(sql)
        return result
    except Exception as e:
        return f"ERROR: {e}"


# ============================================================
# MCP Resource: database schema
# ============================================================
@mcp.resource("database://schema")
def get_schema() -> str:
    """Get the database schema (tables and columns)."""
    return (
        "Database: rookieDB\n"
        "\n"
        "Table: Students\n"
        "  Columns: sid (INTEGER), name (TEXT), major (TEXT), gpa (FLOAT)\n"
        "\n"
        "Table: Courses\n"
        "  Columns: cid (INTEGER), name (TEXT), department (TEXT)\n"
        "\n"
        "Table: Enrollments\n"
        "  Columns: sid (INTEGER), cid (INTEGER)\n"
    )
```

- [ ] **Step 2: 替换 `if __name__ == "__main__":` 块**

```python
if __name__ == "__main__":
    db = RookieDBConnection()
    try:
        db.connect()
        _db = db
    except ConnectionRefusedError:
        print(
            "WARNING: rookieDB not running on localhost:18600. "
            "execute_sql will return an error until it's started.",
            file=sys.stderr,
        )
        _db = db

    mcp.run()
```

- [ ] **Step 3: 验证 — 用 mcp dev 测试（需要 rookieDB 运行中）**

```bash
mcp dev step2-mcp/10_rookiedb_mcp_server.py
```
Expected: Inspector 打开，Tools 中看到 execute_sql，Resources 中看到 database://schema

- [ ] **Step 4: Commit**

```bash
git add step2-mcp/10_rookiedb_mcp_server.py
git commit -m "feat: 注册 execute_sql 工具 + schema 资源"
```

---

### Task 4: 创建 11_agent_mcp_rookiedb.py

**Files:**
- Create: `step2-mcp/11_agent_mcp_rookiedb.py`

- [ ] **Step 1: 创建完整文件**

```python
"""
11_agent_mcp_rookiedb.py — Agent + MCP Client: 自然语言操作 rookieDB

学习点：
  - MCP Client 连真实数据库 Server（不是 Calculator）
  - 启动时 read_resource() 获取 schema → 注入 System Prompt
  - Agent 循环中 LLM 自动选工具 → call_tool → Server 执行
  - API 调用重试（指数退避）
  - 工具调用异常 → is_error 标记回传 LLM
  - Agent 完全不知道 socket/reconnect 的存在

运行：
  python3 step2-mcp/11_agent_mcp_rookiedb.py

前置条件：
  - rookieDB 运行在 localhost:18600

对比：
  06_error_handling.py: 工具和执行都在 Agent 里（紧耦合）
  11_agent_mcp_rookiedb.py: 工具和执行在 MCP Server 里（解耦）
"""

import asyncio
import os
import pathlib
import json
import time

# 加载 .env
env_path = pathlib.Path(__file__).parent.parent / ".env"
if env_path.exists():
    with open(env_path) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, _, value = line.partition("=")
                os.environ.setdefault(key.strip(), value.strip())

from anthropic import Anthropic
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

# ============================================================
# 配置
# ============================================================
MODEL = "deepseek-v4-pro"
MAX_TURNS = 10
MAX_RETRIES = 3

anthropic_client = Anthropic(
    api_key=os.environ["ANTHROPIC_API_KEY"],
    base_url=os.environ.get("ANTHROPIC_BASE_URL", "https://api.deepseek.com/anthropic"),
)


# ============================================================
# 工具函数
# ============================================================
def mcp_tool_to_anthropic(tool) -> dict:
    """MCP 工具格式 → Anthropic tool_use 格式"""
    return {
        "name": tool.name,
        "description": tool.description or "",
        "input_schema": {
            "type": "object",
            "properties": tool.inputSchema.get("properties", {}),
            "required": tool.inputSchema.get("required", []),
        },
    }


def call_claude_with_retry(model, max_tokens, system, messages, tools):
    """调用 Claude API，失败时指数退避重试"""
    for attempt in range(MAX_RETRIES):
        try:
            return anthropic_client.messages.create(
                model=model,
                max_tokens=max_tokens,
                system=system,
                messages=messages,
                tools=tools,
            )
        except Exception as e:
            if attempt == MAX_RETRIES - 1:
                raise
            wait = 2 ** attempt
            print(f"  [API 重试] {e}，{wait}s 后重试 (第 {attempt + 1} 次)...")
            time.sleep(wait)


def print_messages(messages, label):
    """打印消息历史，方便理解 Agent 循环"""
    print(f"\n{'─' * 40} {label} (共 {len(messages)} 条)")
    for i, msg in enumerate(messages):
        role = msg["role"]
        content = msg.get("content", "")
        if isinstance(content, str):
            print(f"  [{i}] {role}: {content[:80]}")
            continue
        for block in content:
            if isinstance(block, dict):
                btype = block.get("type", "text")
            else:
                btype = block.type
            if btype == "text":
                text = block.text if hasattr(block, "text") else block.get("text", "")
                if text:
                    print(f"  [{i}] {role}.text: {text[:80]}")
            elif btype == "tool_use":
                name = block.name if hasattr(block, "name") else block.get("name", "")
                inp = block.input if hasattr(block, "input") else block.get("input", "")
                print(f"  [{i}] {role}.tool_use: {name}({inp})")
            elif btype == "tool_result":
                res = block.get("content", "")
                print(f"  [{i}] {role}.tool_result: {res[:80]}")
    print(f"{'─' * 40}\n")


# ============================================================
# 主逻辑
# ============================================================
async def run():
    # --- 1. 启动 MCP Server ---
    server_file = str(pathlib.Path(__file__).parent / "10_rookiedb_mcp_server.py")
    server_params = StdioServerParameters(
        command="mcp", args=["run", server_file], env=None
    )

    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            # --- 2. 发现工具 ---
            tools_result = await session.list_tools()
            anthropic_tools = [mcp_tool_to_anthropic(t) for t in tools_result.tools]

            print("=" * 50)
            print(f"📦 从 MCP Server 发现 {len(tools_result.tools)} 个工具:")
            for t in tools_result.tools:
                print(f"  - {t.name}: {t.description}")
            print("=" * 50)

            # --- 3. 获取 schema ---
            schema_result = await session.read_resource("database://schema")
            schema_text = ""
            for content in schema_result.contents:
                schema_text += content.text

            print(f"\n📖 Schema 已加载:")
            print(schema_text)

            # --- 4. 构建 System Prompt ---
            system_prompt = (
                "You are a database assistant connected to a rookieDB database.\n"
                "Use the execute_sql tool to query the database.\n"
                "Below is the database schema:\n\n"
                f"{schema_text}\n"
                "Guidelines:\n"
                "- For read-only queries, use SELECT statements.\n"
                "- If a query returns an error, analyze it and try a corrected SQL.\n"
                "- When answering questions, first get data from the database, "
                "then provide a natural language response.\n"
                "- RookieDB requires semicolons at the end of each SQL statement.\n"
                "- Be concise in your responses."
            )

            # --- 5. 用户输入 ---
            prompt = input("\n🤔 请输入你的问题: ")

            # --- 6. Agent 循环 ---
            messages = [{"role": "user", "content": prompt}]
            print_messages(messages, "初始状态")

            for turn in range(MAX_TURNS):
                # API 调用（带重试）
                try:
                    response = call_claude_with_retry(
                        model=MODEL,
                        max_tokens=1024,
                        system=system_prompt,
                        messages=messages,
                        tools=anthropic_tools,
                    )
                except Exception as e:
                    print(f"\n  ❌ [API 失败] 重试 {MAX_RETRIES} 次仍失败: {e}")
                    break

                # 4a. LLM 不调工具 → 结束
                if response.stop_reason != "tool_use":
                    final_text = "".join(
                        block.text for block in response.content
                        if block.type == "text"
                    )
                    print(f"\n🤖 Agent: {final_text}")
                    break

                # 4b. 存 assistant 消息
                messages.append({"role": "assistant", "content": response.content})

                # 4c. 执行每个 tool_use
                for block in response.content:
                    if block.type == "tool_use":
                        print(f"\n🔧 LLM 决定调: {block.name}({json.dumps(block.input, ensure_ascii=False)})")

                        # 通过 MCP Client 调用（try/except 保护）
                        try:
                            result = await session.call_tool(
                                block.name, arguments=block.input
                            )
                            result_text = str(result.content[0].text)
                            is_error = False
                        except Exception as e:
                            result_text = f"工具调用失败: {e}"
                            is_error = True

                        print(f"   Server 返回: {result_text[:100]}...")

                        # 塞回消息历史（异常时标记 is_error）
                        tool_result_block = {
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": result_text,
                        }
                        if is_error:
                            tool_result_block["is_error"] = True

                        messages.append({
                            "role": "user",
                            "content": [tool_result_block],
                        })

                print_messages(messages, f"第 {turn + 1} 轮后")
            else:
                print("\n⚠️  达到最大轮数")


if __name__ == "__main__":
    asyncio.run(run())
```

- [ ] **Step 2: 验证导入**

```bash
python3 -c "import ast; ast.parse(open('step2-mcp/11_agent_mcp_rookiedb.py').read()); print('语法正确')"
```

Expected: "语法正确"

- [ ] **Step 3: Commit**

```bash
git add step2-mcp/11_agent_mcp_rookiedb.py
git commit -m "feat: 11_agent_mcp_rookiedb.py — Agent + MCP 操作 rookieDB"
```

---

### Task 5: 端到端测试

**Files:** 无修改

- [ ] **Step 1: 确保 rookieDB 启动**

```bash
cd /Users/shunhewang/melbourne/cs186/berkeley-sp26-rookiedb
java -cp target/classes edu.berkeley.cs186.database.cli.Server &
```

Expected: 服务启动在 localhost:18600

- [ ] **Step 2: 测试简单查询**

```bash
echo "列出所有学生" | python3 step2-mcp/11_agent_mcp_rookiedb.py 2>&1
```

Expected: Agent 自动调 execute_sql，返回 Students 表数据

- [ ] **Step 3: 测试 schema 感知**

```bash
echo "Students 表有哪些字段" | python3 step2-mcp/11_agent_mcp_rookiedb.py 2>&1
```

Expected: Agent 根据 schema 正确回答

- [ ] **Step 4: 停止 rookieDB（可选）**

```bash
kill %1  # 或 pkill -f "edu.berkeley.cs186.database.cli.Server"
```

- [ ] **Step 5: Commit（如有修改）**

```bash
git status
# 如有修改，commit
```