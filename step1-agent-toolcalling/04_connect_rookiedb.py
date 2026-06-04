"""
单元 4：接上 rookieDB — 端到端 Agent

学习点：
  1. Python socket 连 Java 进程通信
  2. 把 mock 替换成真实数据库操作
  3. 端到端：自然语言 → SQL → 真实结果 → 自然语言回复
  4. 连接生命周期管理（单连接复用）
"""

import anthropic
import os
import json
import socket
from pathlib import Path

# 加载 .env（兼容 IDE 直接运行）
env_file = Path(__file__).parent / ".env"
if env_file.exists():
    for line in env_file.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, _, value = line.partition("=")
            os.environ[key.strip()] = value.strip()

client = anthropic.Anthropic(
    base_url=os.environ.get("ANTHROPIC_BASE_URL", "https://api.anthropic.com"),
)

# ============================================================
# 1. rookieDB 连接管理
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
        """建立连接，跳过欢迎信息"""
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.settimeout(10)
        self.sock.connect((self.host, self.port))
        self._recv_until_prompt()
        print(f"  🔌 已连接 rookieDB ({self.host}:{self.port})")

    def execute(self, sql: str) -> str:
        """发送 SQL，接收完整结果"""
        if self.sock is None:
            raise ConnectionError("未连接 rookieDB，请先调用 connect()")
        if not sql.strip().endswith(";"):
            sql += ";"
        self.sock.send((sql + "\n").encode("utf-8"))
        response = self._recv_until_prompt()
        return response.strip()

    def _recv_until_prompt(self) -> str:
        """读取数据直到遇到 '=> ' 提示符"""
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
        """关闭连接"""
        if self.sock:
            try:
                self.sock.send(b"exit\n")
            except Exception:
                pass
            self.sock.close()
            self.sock = None
            print("  🔌 已断开 rookieDB")


# ============================================================
# 2. Tool 定义
# ============================================================
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
                "description": "要执行的 SQL 语句。例如：SELECT * FROM Students WHERE gpa > 3.5"
            }
        },
        "required": ["sql"],
    },
}


# ============================================================
# 3. 工具实现（闭包捕获 db）
# ============================================================
def make_execute_sql(db):
    """返回 execute_sql 函数，通过闭包捕获 db 连接"""
    def execute_sql(sql: str):
        result = db.execute(sql)
        print(f"  🔧 [rookieDB] {sql[:80]}...")
        return result
    return execute_sql


# ============================================================
# 4. Agent 循环
# ============================================================
def run_agent(user_question: str, execute_sql_fn):
    """
    Agent 循环：跟 03 一样，execute_sql_fn 替代 mock
    """
    messages = [{"role": "user", "content": user_question}]

    print("=" * 60)
    print(f"用户: {user_question}")
    print("=" * 60)

    while True:
        response = client.messages.create(
            model="deepseek-v4-pro",
            max_tokens=1024,
            system=(
                "你是一个数据库管理助手，连接着真实的 rookieDB 数据库。"
                "用户问数据库相关问题时，使用 execute_sql 工具执行查询。"
                "在回答用户问题之前，先使用工具查询数据库获取最新数据。"
                "数据库中有三张表：Students（学生，字段 sid, name, major, gpa）、"
                "Courses（课程，字段 cid, name, department）、"
                "Enrollments（选课记录，字段 sid, cid）。"
                "无需查询表列表，直接使用这些表。"
                "注意：rookieDB 不支持带 '.' 的表名（如 _metadata.tables）。"
            ),
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

        # 执行工具并塞结果
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
# 5. 跑 — 验证 8 步 CRUD
# ============================================================
if __name__ == "__main__":
    db = RookieDBConnection()

    try:
        db.connect()
        execute_sql_fn = make_execute_sql(db)

        # 1. Read — 查看 Students 表数据
        run_agent("帮我查一下 Students 表里有哪些学生，只看前 5 条", execute_sql_fn)

        # 2. Read — 条件查询
        run_agent("帮我查一下 Students 表里 CS 专业的学生", execute_sql_fn)

        # 3. Create — 插入新记录
        run_agent(
            "帮我往 Students 表插入一条新学生记录："
            "学号 999，名字 '测试学生'，专业 'CS'，GPA 3.5",
            execute_sql_fn
        )

        # 4. Read — 验证插入
        run_agent("帮我查一下学号 999 的学生信息", execute_sql_fn)

        # 5. Update — 更新记录
        run_agent("把学号 999 的学生的 GPA 改成 4.0", execute_sql_fn)

        # 6. Read — 验证更新
        run_agent("帮我确认学号 999 的学生现在 GPA 是多少", execute_sql_fn)

        # 7. Delete — 删除记录
        run_agent("帮我把学号 999 的学生记录删掉", execute_sql_fn)

        # 8. Read — 验证删除
        run_agent("帮我确认学号 999 的学生还在不在数据库里", execute_sql_fn)

    finally:
        db.close()
