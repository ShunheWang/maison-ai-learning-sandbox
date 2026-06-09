"""
13_concurrent_agents.py — 多 Agent 并发操作 rookieDB

学习点：
  - 多个 Agent 同时运行，每个独立的事务和连接
  - asyncio 并发管理多 Agent
  - 对比单 Agent 串行 vs 多 Agent 并发
  - 每个 Agent 独立：Anthropic client + socket 连接 + messages 历史
  - 不连 MCP（聚焦并发模式），直接 socket 连 rookieDB
  - 正常并发场景（不制造死锁，死锁留给 demo 14）

运行方式：
  1. 先启动 rookieDB（java -cp ... Server &）
  2. python3 step3-multi-agent/13_concurrent_agents.py

Agent 角色：
  Worker 1 — 操作 Students 表
  Worker 2 — 操作 Courses 表
  Worker 3 — 操作 Enrollment 表
  三个同时跑，各管各的表，互不冲突
"""

import os
import re
import socket
import time
import pathlib
import asyncio

# 加载 .env
env_path = pathlib.Path(__file__).parent.parent / ".env"
if env_path.exists():
    with open(env_path) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, _, value = line.partition("=")
                os.environ[key.strip()] = value.strip()

from anthropic import Anthropic

# ============================================================
# 配置
# ============================================================
MODEL = "deepseek-v4-pro"
MAX_TOKENS = 1000
HOST = "localhost"
PORT = 18600

# ============================================================
# rookieDB 连接（复用 04 的实现）
# ============================================================

class RookieDBConnection:
    """TCP socket 连 rookieDB Server"""

    def __init__(self, host=HOST, port=PORT, timeout=10):
        self.host = host
        self.port = port
        self.timeout = timeout
        self.sock = None

    def connect(self):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.settimeout(self.timeout)
        self.sock.connect((self.host, self.port))
        time.sleep(0.3)  # 等 rookieDB 发完欢迎信息
        self._drain()     # 清空缓冲区（欢迎信息）

    def execute(self, sql: str) -> str:
        """发送 SQL，接收结果"""
        try:
            self.sock.sendall((sql + "\n").encode())
            result = self._recv_until_prompt()
            return result.strip()
        except (socket.timeout, ConnectionError, OSError) as e:
            return f"ERROR: {e}"

    def _drain(self):
        """清空缓冲区残留数据（欢迎信息等）"""
        try:
            self.sock.settimeout(0.3)
            while True:
                chunk = self.sock.recv(4096)
                if not chunk:
                    break
        except socket.timeout:
            pass
        finally:
            self.sock.settimeout(self.timeout)

    def _recv_until_prompt(self) -> str:
        """收数据直到出现 rookieDB 提示符"""
        data = b""
        while True:
            try:
                chunk = self.sock.recv(4096)
                if not chunk:
                    break
                data += chunk
                decoded = data.decode("utf-8", errors="replace")
                if decoded.endswith("\n") or decoded.endswith("> "):
                    break
            except socket.timeout:
                break
        result = data.decode("utf-8", errors="replace")
        # 过滤掉欢迎信息（残留的）
        if result.startswith("Welcome to RookieDB"):
            result = result.split("\n", 1)[1] if "\n" in result else ""
        return result

    def close(self):
        if self.sock:
            try:
                self.sock.close()
            except Exception:
                pass


# ============================================================
# Tool 定义
# ============================================================

EXECUTE_SQL_TOOL = {
    "name": "execute_sql",
    "description": (
        "在 rookieDB 上执行一条 SQL 语句（支持 SELECT/INSERT/UPDATE/DELETE）。"
        "不支持 LIMIT、DISTINCT、GROUP BY、ORDER BY ... ASC/DESC（只能默认升序）。"
        "支持 MAX()、COUNT()、WHERE、子查询。"
        "字符串值用单引号（如 'CS'），SQL 必须以分号 ; 结尾。"
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "sql": {
                "type": "string",
                "description": "要执行的 SQL 语句（以分号结尾）",
            }
        },
        "required": ["sql"],
    },
}

TOOLS = [EXECUTE_SQL_TOOL]

# ============================================================
# System Prompt
# ============================================================

WORKER_SYSTEM_PROMPT = """你是一个数据库 Worker Agent。你的任务是通过 execute_sql 工具查询 rookieDB。

数据库结构（只有这两张表）：
  Students(sid INT, name VARCHAR, major VARCHAR, gpa REAL)  — 201 个学生
  Courses(cid INT, name VARCHAR, department VARCHAR)        — 16 门课程

rookieDB 限制：
- 不支持 DISTINCT、GROUP BY、LIMIT
- ORDER BY 只支持默认升序，不支持 ASC/DESC 关键字
- 支持 MAX()、COUNT()、WHERE、子查询
- 字符串值用单引号括起来（如 'CS'）
- SQL 必须以分号 ; 结尾

重要规则：
- 表不存在就直说，不要用别的表的返回值凑数
- 查不到结果就说查不到，不要编造
- SQL 报错后最多重试 2 次，2 次都失败就向用户报告错误
- 每次只执行一条 SQL
- 拿到结果后，用自然语言简要总结"""


# ============================================================
# Worker Agent（独立 Agent 循环）
# ============================================================

async def run_worker(name: str, task: str, db: RookieDBConnection):
    """一个独立的 Agent 循环"""
    client = Anthropic(
        api_key=os.environ["ANTHROPIC_API_KEY"],
        base_url=os.environ.get("ANTHROPIC_BASE_URL", "https://api.deepseek.com/anthropic"),
    )

    messages = [{"role": "user", "content": task}]
    max_turns = 10

    print(f"\n{'─'*50}")
    print(f"🤖 [{name}] 启动，任务: {task}")
    print(f"{'─'*50}")

    for turn in range(max_turns):
        response = client.messages.create(
            model=MODEL,
            max_tokens=MAX_TOKENS,
            system=WORKER_SYSTEM_PROMPT,
            messages=messages,
            tools=TOOLS,
        )

        # 不需要工具 → 结束
        if response.stop_reason != "tool_use":
            final_text = "".join(
                block.text for block in response.content if block.type == "text"
            )
            print(f"💬 [{name}] 完成: {final_text[:120]}")
            return final_text

        # 需要工具 → 执行
        assistant_blocks = [
            b for b in response.content if b.type != "thinking"
        ]
        messages.append({"role": "assistant", "content": assistant_blocks})

        tool_results = []
        for block in response.content:
            if block.type == "tool_use":
                sql = block.input.get("sql", "")
                print(f"🔧 [{name}] execute_sql: {sql}")

                # 执行 SQL（同步操作，用 run_in_executor 不阻塞事件循环）
                result = await asyncio.get_event_loop().run_in_executor(
                    None, db.execute, sql
                )
                # 截断过长结果
                display_result = result[:100] + "..." if len(result) > 100 else result
                print(f"   [{name}] 结果: {display_result}")

                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": result,
                })

        if tool_results:
            messages.append({"role": "user", "content": tool_results})

    print(f"⚠️  [{name}] 达到最大轮数")
    return None


# ============================================================
# 主流程
# ============================================================

async def main():
    print("=" * 60)
    print("🚀 多 Agent 并发操作 rookieDB")
    print("=" * 60)

    # 测试场景：3 个 Worker 各查不同的表/条件
    workers = [
        {
            "name": "Worker_Students",
            "task": "查询 Students 表里共有多少个学生",
        },
        {
            "name": "Worker_Courses",
            "task": "查询 Courses 表里有哪些院系开设了课程（列出所有行，手动去重整理）",
        },
        {
            "name": "Worker_GPA",
            "task": "查询 Students 表里 GPA 最高的学生叫什么名字，GPA 是多少",
        },
    ]

    # 每个 Worker 创建独立连接
    connections = []
    try:
        print("\n📡 创建连接...")
        for w in workers:
            db = RookieDBConnection()
            db.connect()
            connections.append(db)
            print(f"   [{w['name']}] 已连接")

        print(f"\n⚡ 启动 {len(workers)} 个 Worker 并发执行...\n")

        # === 并发！===
        start = time.time()
        results = await asyncio.gather(*[
            run_worker(w["name"], w["task"], db)
            for w, db in zip(workers, connections)
        ])
        elapsed = time.time() - start

        print(f"\n{'='*60}")
        print(f"📊 结果汇总（总耗时 {elapsed:.1f}s）")
        print(f"{'='*60}")
        for w, result in zip(workers, results):
            status = "✅" if result else "❌"
            summary = result[:100] if result else "未完成"
            print(f"  {status} {w['name']}: {summary}")

        # 对比：串行执行耗时估算
        print(f"\n💡 单 Agent 串行执行耗时 ≈ {elapsed * len(workers):.0f}s（估算）")
        print(f"   并发执行实际耗时 = {elapsed:.1f}s")
        print(f"   并发优势: 3 个 Agent 几乎是同时完成的")

    finally:
        for db in connections:
            db.close()
        print("\n🔌 所有连接已关闭")


if __name__ == "__main__":
    asyncio.run(main())
