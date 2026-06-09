"""
14_deadlock_scenario.py — 死锁场景复现

学习点：
  - 两个 Worker Agent 并发操作同一组行，锁获取顺序相反 → 死锁
  - 典型死锁模式：A 先锁 sid=1 再锁 sid=2，B 先锁 sid=2 再锁 sid=1
  - rookieDB LockManager 没有死锁检测 — 死锁后事务永久挂起
  - 这正是 DDA 要解决的问题（Phase 3）
  - 跟 13_concurrent_agents.py 对比：正常并发 vs 死锁并发

运行方式：
  1. 先启动 rookieDB（java -cp target/classes ... Server &）
  2. python3 step3-multi-agent/14_deadlock_scenario.py

Agent 角色：
  Worker A — BEGIN → UPDATE Students sid=1 → UPDATE Courses cid=1 → HANG
  Worker B — BEGIN → UPDATE Courses cid=1 → UPDATE Students sid=1 → HANG
  不同表保证不在同一页，锁获取顺序相反 → 死锁
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
# rookieDB 连接
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
        time.sleep(0.3)
        self._drain()

    def execute(self, sql: str, timeout_override: float = None) -> str:
        """发送 SQL，接收结果"""
        try:
            self.sock.sendall((sql + "\n").encode())
            result = self._recv_until_prompt(timeout_override)
            return result.strip()
        except (socket.timeout, ConnectionError, OSError) as e:
            return f"ERROR: {e}"

    def _drain(self):
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

    def _recv_until_prompt(self, timeout_override: float = None) -> str:
        timeout = timeout_override if timeout_override is not None else self.timeout
        data = b""
        while True:
            try:
                self.sock.settimeout(min(timeout, 1.0))
                chunk = self.sock.recv(4096)
                if not chunk:
                    break
                data += chunk
                decoded = data.decode("utf-8", errors="replace")
                if decoded.endswith("\n") or decoded.endswith("> "):
                    break
            except socket.timeout:
                break
        return data.decode("utf-8", errors="replace")

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
        "在 rookieDB 上执行一条 SQL 语句。支持 SELECT、INSERT、UPDATE、DELETE。"
        "也支持事务控制：BEGIN（开始事务）、COMMIT（提交）、ROLLBACK（回滚）。"
        "字符串值用单引号，SQL 必须以分号 ; 结尾。"
        "UPDATE 会获取行级排他锁，可能与其他事务冲突。"
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
# System Prompt（死锁 Worker）
# ============================================================

DEADLOCK_WORKER_PROMPT = """你是一个数据库 Worker Agent。你的任务是通过 execute_sql 工具执行一系列数据库操作。

重要：你必须严格按照用户指令中列出的顺序执行每一步，不要添加额外步骤，不要跳过任何步骤。

数据库只有 Students 表（sid, name, major, gpa），sid=1 到 sid=200 都有数据。

执行每一步后，等待用户告诉你"继续"。收到"继续"后才执行下一步。"""


# ============================================================
# Worker Agent 循环（逐步执行版）
# ============================================================

def _print_lock_state(db: RookieDBConnection, who: str = ""):
    """通过 rookieDB 的 \\alllocks 命令打印真实锁状态"""
    print(f"\n   {'─'*40}")
    print(f"   🔐 真实锁状态 {who}")
    result = db.execute("\\alllocks", timeout_override=3.0)
    # 格式化缩进输出
    for line in result.strip().split("\n"):
        print(f"   | {line}")
    print(f"   {'─'*40}\n")


async def run_deadlock_worker(
    name: str,
    steps: list[str],
    db: RookieDBConnection,
    ready_event: asyncio.Event,
    other_ready_event: asyncio.Event,
    step_before_barrier: int,
):
    """
    Worker 执行固定步骤序列，在第 step_before_barrier 步后
    等待同步屏障（双方就绪后同时继续）。
    """
    client = Anthropic(
        api_key=os.environ["ANTHROPIC_API_KEY"],
        base_url=os.environ.get("ANTHROPIC_BASE_URL", "https://api.deepseek.com/anthropic"),
    )

    print(f"\n{'─'*50}")
    print(f"🤖 [{name}] 启动（{len(steps)} 步操作）")
    for i, s in enumerate(steps):
        print(f"   步骤{i+1}: {s}")
    print(f"{'─'*50}")

    task_text = (
        f"请按顺序执行以下 SQL 步骤。每执行一步后说'完成'。\n\n"
        + "\n".join(f"步骤{i+1}: {s}" for i, s in enumerate(steps))
    )

    messages = [{"role": "user", "content": task_text}]
    current_step = 0
    executed_sqls = set()  # 跟踪已执行的 SQL，避免重复

    max_turns = len(steps) + 5  # 每步 1 次调用 + 额外缓冲

    for turn in range(max_turns):
        response = client.messages.create(
            model=MODEL,
            max_tokens=MAX_TOKENS,
            system=DEADLOCK_WORKER_PROMPT,
            messages=messages,
            tools=TOOLS,
        )

        # 不需要工具 → Worker 说"完成"了
        if response.stop_reason != "tool_use":
            text = "".join(
                block.text for block in response.content if block.type == "text"
            )
            current_step += 1
            print(f"💬 [{name}] 步骤{current_step} 完成 → {text[:80]}")

            # === 关键：在死锁触发点之前同步 ===
            if current_step == step_before_barrier:
                ready_event.set()  # 通知：我准备好了
                print(f"⏳ [{name}] 等待对方就绪...")
                await other_ready_event.wait()  # 等对方
                print(f"⚡ [{name}] 双方就绪，继续执行下一步（即将死锁...）")

            if current_step >= len(steps):
                print(f"✅ [{name}] 全部步骤完成")
                return text

            # 告诉 Worker 继续下一步
            messages.append({"role": "assistant", "content": response.content})
            messages.append({"role": "user", "content": f"继续执行步骤{current_step + 1}"})
            continue

        # 需要工具 → 执行 SQL
        assistant_blocks = [
            b for b in response.content if b.type != "thinking"
        ]
        messages.append({"role": "assistant", "content": assistant_blocks})

        tool_results = []
        for block in response.content:
            if block.type == "tool_use":
                sql = block.input.get("sql", "")

                # 避免重复执行同一条 SQL
                if sql in executed_sqls:
                    continue
                executed_sqls.add(sql)

                print(f"🔧 [{name}] {sql}")

                # 执行 SQL，对于可能死锁的步骤用短超时
                result = await asyncio.get_event_loop().run_in_executor(
                    None, db.execute, sql
                )

                is_timeout = False
                display = result[:120] + "..." if len(result) > 120 else result

                if result == "" or "ERROR: timed out" in result:
                    is_timeout = True
                    display = "⏰ 超时！事务被阻塞（等待其他事务释放锁）"

                print(f"   [{name}] {'🔒 阻塞!' if is_timeout else '✅'}: {display}")

                # 打印 rookieDB 真实锁状态
                _print_lock_state(db, who=f"({name} 执行 {sql} 后)")

                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": result if not is_timeout else "TIMEOUT: 这个操作被阻塞了，可能在等待其他事务释放锁。",
                })

        if tool_results:
            messages.append({"role": "user", "content": tool_results})

    print(f"⚠️  [{name}] 达到最大轮数（死锁未解）")


# ============================================================
# 主流程
# ============================================================

async def main():
    print("=" * 60)
    print("💀 死锁场景复现")
    print("=" * 60)
    print()
    print("场景: 两个 Worker Agent 以相反顺序获取锁")
    print()
    print("   Worker A: BEGIN → UPDATE sid=1 → UPDATE sid=2 → COMMIT")
    print("   Worker B: BEGIN → UPDATE sid=2 → UPDATE sid=1 → COMMIT")
    print()
    print("   A 先锁 sid=1，B 先锁 sid=2")
    print("   A 想锁 sid=2 → 等 B 释放")
    print("   B 想锁 sid=1 → 等 A 释放")
    print("   → 死锁！rookieDB 没有死锁检测 → 永久挂起")
    print()

    # Worker A 的步骤：先锁 Students，再锁 Courses
    steps_a = [
        "BEGIN;",
        "UPDATE Students SET gpa = 4.0 WHERE sid = 1;",
        "UPDATE Courses SET department = 'TestA' WHERE cid = 1;",  # ← 需要 Courses 的锁
        "COMMIT;",
    ]

    # Worker B 的步骤：先锁 Courses，再锁 Students（顺序相反！）
    steps_b = [
        "BEGIN;",
        "UPDATE Courses SET department = 'TestB' WHERE cid = 1;",
        "UPDATE Students SET gpa = 3.0 WHERE sid = 1;",  # ← 需要 Students 的锁
        "COMMIT;",
    ]

    # 同步机制：双方都在第 2 步（第一次 UPDATE）后等待对方
    # 然后同时冲向第 3 步（第二次 UPDATE）→ 死锁
    a_ready = asyncio.Event()
    b_ready = asyncio.Event()

    db_a = RookieDBConnection()
    db_b = RookieDBConnection()

    try:
        print("📡 创建连接...")
        db_a.connect()
        db_b.connect()
        print("   两个连接已建立\n")

        print("⚡ 启动两个 Worker...\n")

        # 并发启动两个 Worker
        task_a = asyncio.create_task(
            run_deadlock_worker("Worker_A", steps_a, db_a, a_ready, b_ready, step_before_barrier=2)
        )
        task_b = asyncio.create_task(
            run_deadlock_worker("Worker_B", steps_b, db_b, b_ready, a_ready, step_before_barrier=2)
        )

        # 等待完成（其中一个会超时/死锁）
        done, pending = await asyncio.wait(
            [task_a, task_b],
            timeout=60.0,  # 最多等 60 秒
        )

        print(f"\n{'='*60}")
        print(f"📊 结果")
        print(f"{'='*60}")

        for t in [task_a, task_b]:
            name = "Worker_A" if t is task_a else "Worker_B"
            if t in done:
                if t.exception():
                    print(f"  ❌ {name}: 异常 — {t.exception()}")
                else:
                    print(f"  ✅ {name}: 完成 — {t.result()[:100] if t.result() else '无返回'}")
            else:
                print(f"  💀 {name}: 死锁 — 事务被阻塞，60秒后仍未完成")
                t.cancel()

        if pending:
            print(f"\n💀 检测到死锁：{len(pending)} 个 Worker 相互等待对方释放锁")
            print(f"   这正是 DDA 要解决的问题（Phase 3）！")
            # 清理：关闭连接（rookieDB 不支持 ROLLBACK）
            for t_name, db in [("Worker_A", db_a), ("Worker_B", db_b)]:
                try:
                    db.close()
                    print(f"   🔄 已关闭 {t_name} 连接")
                except Exception:
                    pass

    finally:
        db_a.close()
        db_b.close()
        print("\n🔌 所有连接已关闭")
        print()
        print("总结：")
        print("  1. 两个事务以相反顺序获取锁 → 死锁")
        print("  2. rookieDB 无死锁检测 → 事务永久挂起")
        print("  3. Phase 3 的 DDA 将解决这个问题：")
        print("     - 定时监控 LockManager 状态")
        print("     - 构建 wait-for graph")
        print("     - BFS/DFS 找环")
        print("     - 选择 victim → ROLLBACK")


if __name__ == "__main__":
    asyncio.run(main())
