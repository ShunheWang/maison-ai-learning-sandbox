"""
单元 2.2：System Prompt 设计 — 对比实验

学习点：
  1. 角色设定：不同角色 → 不同行为
  2. 护栏：限制权限 → Agent 拒绝超权限操作
  3. 知识缺失：不告诉表结构 → Agent 会不会乱猜
  4. 反幻觉：要求老实说不知道 → Agent 不会编数据

实验方法：同一条问题，不同的 system prompt，观察行为变化。
"""

import anthropic
import os
import json
import socket
from pathlib import Path

# 加载 .env
env_file = Path(__file__).parent / ".env"
if env_file.exists():
    for line in env_file.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, _, value = line.partition("=")
            os.environ.setdefault(key.strip(), value.strip())

client = anthropic.Anthropic(
    base_url=os.environ.get("ANTHROPIC_BASE_URL", "https://api.anthropic.com"),
)

# ============================================================
# rookieDB 连接（复用单元 4 的 RookieDBConnection）
# ============================================================
ROOKIEDB_HOST = "localhost"
ROOKIEDB_PORT = 18600


class RookieDBConnection:
    """管理 rookieDB 的 socket 连接"""

    def __init__(self, host=ROOKIEDB_HOST, port=ROOKIEDB_PORT):
        self.host = host
        self.port = port
        self.sock = None

    def connect(self):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.settimeout(10)
        self.sock.connect((self.host, self.port))
        self._recv_until_prompt()
        print(f"  🔌 已连接 rookieDB ({self.host}:{self.port})")

    def execute(self, sql: str) -> str:
        if self.sock is None:
            raise ConnectionError("未连接 rookieDB，请先调用 connect()")
        if not sql.strip().endswith(";"):
            sql += ";"
        self.sock.send((sql + "\n").encode("utf-8"))
        response = self._recv_until_prompt()
        return response.strip()

    def _recv_until_prompt(self) -> str:
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
        if self.sock:
            try:
                self.sock.send(b"exit\n")
            except Exception:
                pass
            self.sock.close()
            self.sock = None
            print("  🔌 已断开 rookieDB")


# ============================================================
# Tool 定义（和单元 4 一样）
# ============================================================
execute_sql_tool = {
    "name": "execute_sql",
    "description": (
        "在 rookieDB 数据库上执行一条 SQL 语句。"
        "支持 SELECT、INSERT、UPDATE、DELETE 操作。"
        "也支持 CREATE TABLE、DROP TABLE 等 DDL 操作。"
        "查询结果以表格形式返回。"
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "sql": {
                "type": "string",
                "description": "要执行的 SQL 语句。"
            }
        },
        "required": ["sql"],
    },
}


def make_execute_sql(db):
    def execute_sql(sql: str):
        result = db.execute(sql)
        print(f"  🔧 [rookieDB] {sql[:80]}...")
        return result
    return execute_sql


# ============================================================
# Agent 循环
# ============================================================
def run_agent(user_question: str, execute_sql_fn, system_prompt: str):
    messages = [{"role": "user", "content": user_question}]

    print(f"用户: {user_question}")
    print(f"System Prompt: {system_prompt[:100]}...")
    print("-" * 40)

    while True:
        response = client.messages.create(
            model="deepseek-v4-pro",
            max_tokens=1024,
            system=system_prompt,
            messages=messages,
            tools=[execute_sql_tool],
        )

        tool_uses = []
        for block in response.content:
            if block.type == "thinking":
                continue
            elif block.type == "text":
                print(f"\n  💬 [Claude] {block.text}")
            elif block.type == "tool_use":
                tool_uses.append(block)
                print(f"\n  🔨 [tool_use] {block.name}({json.dumps(block.input, ensure_ascii=False)})")

        if response.stop_reason != "tool_use":
            print(f"\n  ✅ 结束 (stop_reason={response.stop_reason})")
            break

        # 追加 assistant 消息
        assistant_content = []
        for block in response.content:
            if block.type == "text":
                assistant_content.append({"type": "text", "text": block.text})
            elif block.type == "tool_use":
                assistant_content.append({
                    "type": "tool_use",
                    "id": block.id,
                    "name": block.name,
                    "input": block.input,
                })
        messages.append({"role": "assistant", "content": assistant_content})

        # 执行工具
        tool_results = []
        for tool_use in tool_uses:
            if tool_use.name == "execute_sql":
                result = execute_sql_fn(tool_use.input["sql"])
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": tool_use.id,
                    "content": result,
                })
            else:
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": tool_use.id,
                    "content": f"Error: 未知工具 {tool_use.name}",
                    "is_error": True,
                })

        messages.append({"role": "user", "content": tool_results})
        print(f"  🔄 [结果塞回，继续...]")


# ============================================================
# 实验：同一条问题 -> 不同 system prompt -> 观察行为
# ============================================================
if __name__ == "__main__":
    db = RookieDBConnection()
    db.connect()
    execute_sql_fn = make_execute_sql(db)

    # 共用同一个测试问题
    test_question = "帮我查一下 Students 表里 GPA 低于 1.5 的学生"

    # ---- 实验 1: 默认角色（基线） ----
    print("=" * 60)
    print("实验 1：默认角色 — 数据库管理助手")
    print("=" * 60)
    run_agent(
        test_question,
        execute_sql_fn,
        system_prompt=(
            "你是一个数据库管理助手，连接着真实的 rookieDB 数据库。"
            "用户问数据库相关问题时，使用 execute_sql 工具执行查询。"
            "数据库中有三张表：Students（sid, name, major, gpa）、"
            "Courses（cid, name, department）、"
            "Enrollments（sid, cid）。"
        )
    )

    # ---- 实验 2: 不同角色 — rookieDB 开发者 ----
    print()
    print("=" * 60)
    print("实验 2：不同角色 — rookieDB 内核开发者")
    print("=" * 60)
    run_agent(
        test_question,
        execute_sql_fn,
        system_prompt=(
            "你是 rookieDB 数据库的内核开发者，参与了存储引擎和查询优化器的开发。"
            "你对 rookieDB 的内部实现非常了解，回答时喜欢解释底层原理。"
            "使用 execute_sql 工具执行查询。"
            "数据库中有三张表：Students（sid, name, major, gpa）、"
            "Courses（cid, name, department）、"
            "Enrollments（sid, cid）。"
        )
    )

    # ---- 实验 3: 护栏 — 只允许 SELECT ----
    print()
    print("=" * 60)
    print("实验 3：护栏 — 只允许 SELECT")
    print("=" * 60)
    run_agent(
        test_question,
        execute_sql_fn,
        system_prompt=(
            "你是一个数据库查询助手。"
            "重要规则：你只允许执行 SELECT 查询，绝对不允许执行 INSERT、UPDATE、DELETE、DROP 等写操作。"
            "如果用户要求写入或修改数据，礼貌拒绝并说明原因。"
            "使用 execute_sql 工具执行查询。"
            "数据库中有三张表：Students（sid, name, major, gpa）、"
            "Courses（cid, name, department）、"
            "Enrollments（sid, cid）。"
        )
    )
    # 护栏测试：额外测一个写操作请求
    print()
    print("-" * 40)
    print("护栏追加测试：尝试要求执行写操作")
    print("-" * 40)
    run_agent(
        "帮我把学号 1 的学生的 GPA 改成 4.0",
        execute_sql_fn,
        system_prompt=(
            "你是一个数据库查询助手。"
            "重要规则：你只允许执行 SELECT 查询，绝对不允许执行 INSERT、UPDATE、DELETE、DROP 等写操作。"
            "如果用户要求写入或修改数据，礼貌拒绝并说明原因。"
            "使用 execute_sql 工具执行查询。"
            "数据库中有三张表：Students（sid, name, major, gpa）、"
            "Courses（cid, name, department）、"
            "Enrollments（sid, cid）。"
        )
    )

    # ---- 实验 4: 知识缺失 — 不告诉表结构 ----
    print()
    print("=" * 60)
    print("实验 4：知识缺失 — 不告诉表结构")
    print("=" * 60)
    run_agent(
        test_question,
        execute_sql_fn,
        system_prompt=(
            "你是一个数据库管理助手。"
            "使用 execute_sql 工具执行查询。"
            "注意：你不知道数据库里有哪些表，需要自己探索。"
        )
    )

    # ---- 实验 5: 反幻觉 — 要求诚实 ----
    print()
    print("=" * 60)
    print("实验 5：反幻觉 — 查不到就老实说")
    print("=" * 60)
    run_agent(
        test_question,
        execute_sql_fn,
        system_prompt=(
            "你是一个数据库管理助手。"
            "使用 execute_sql 工具执行查询。"
            "核心规则：如果你查询了但没有找到结果，必须老实告诉用户'没查到'，绝对不要编造数据。"
            "如果查询结果为空，只需说明没有匹配的数据，不要猜测或推断。"
            "数据库中有三张表：Students（sid, name, major, gpa）、"
            "Courses（cid, name, department）、"
            "Enrollments（sid, cid）。"
        )
    )
    # 反幻觉追加测试：查一个不存在的东西
    print()
    print("-" * 40)
    print("反幻觉追加测试：查不存在的表")
    print("-" * 40)
    run_agent(
        "帮我查一下 Teachers 表里有哪些老师",
        execute_sql_fn,
        system_prompt=(
            "你是一个数据库管理助手。"
            "使用 execute_sql 工具执行查询。"
            "核心规则：如果你查询了但没有找到结果，必须老实告诉用户'没查到'，绝对不要编造数据。"
            "如果查询结果为空，只需说明没有匹配的数据，不要猜测或推断。"
            "数据库中有三张表：Students（sid, name, major, gpa）、"
            "Courses（cid, name, department）、"
            "Enrollments（sid, cid）。"
        )
    )

    db.close()
