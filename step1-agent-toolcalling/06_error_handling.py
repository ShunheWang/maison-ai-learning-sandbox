"""
单元 2.3：错误处理 — Agent 不会因为一个错误就崩掉

学习点：
  1. API 调用失败 → 重试（指数退避）
  2. Claude 传的参数不对 → is_error 标记，让 Claude 自己修正
  3. rookieDB 连接断开 → 检测 + 自动重连
  4. 工具执行失败 → 返回错误让 Claude 自己处理

测试方法：每个场景刻意触发错误，观察 Agent 是否优雅恢复。
"""

import anthropic
import os
import json
import socket
import time
from pathlib import Path

# 加载 .env
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
# 1. rookieDB 连接管理（带重连）
# ============================================================
ROOKIEDB_HOST = "localhost"
ROOKIEDB_PORT = 18600


class RookieDBConnection:
    """管理 rookieDB 的 socket 连接，支持自动重连"""

    def __init__(self, host=ROOKIEDB_HOST, port=ROOKIEDB_PORT):
        self.host = host
        self.port = port
        self.sock = None
        self._reconnect_count = 0

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

        try:
            self.sock.send((sql + "\n").encode("utf-8"))
            response = self._recv_until_prompt()
            return response.strip()
        except (socket.timeout, ConnectionError, OSError) as e:
            # 连接断了 → 尝试重连一次
            print(f"  ⚠️ [重连] 连接异常: {e}")
            self._reconnect()
            # 重连后重试
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
        print(f"  🔄 [重连成功] (第 {self._reconnect_count} 次重连)")

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
# 2. Tool 定义
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


# ============================================================
# 3. 工具实现
# ============================================================
def make_execute_sql(db):
    def execute_sql(sql: str):
        result = db.execute(sql)
        print(f"  🔧 [rookieDB] {sql[:80]}...")
        return result
    return execute_sql


# ============================================================
# 4. API 调用（带重试）
# ============================================================
MAX_RETRIES = 3

def call_claude_with_retry(model, max_tokens, system, messages, tools):
    """调用 Claude API，失败时指数退避重试"""
    for attempt in range(MAX_RETRIES):
        try:
            return client.messages.create(
                model=model,
                max_tokens=max_tokens,
                system=system,
                messages=messages,
                tools=tools,
            )
        except Exception as e:
            if attempt == MAX_RETRIES - 1:
                raise  # 最后一次也失败，不吞了
            wait = 2 ** attempt
            print(f"  ⚠️ [API 重试] {e}，{wait}s 后重试 (第 {attempt + 1} 次)...")
            time.sleep(wait)


def validate_tool_input(tool_use):
    """校验 Claude 传的参数，返回 (valid, error_msg)"""
    if tool_use.name != "execute_sql":
        return False, f"未知工具: {tool_use.name}"

    sql = tool_use.input.get("sql")
    if not sql:
        return False, "参数错误: sql 不能为空"
    if not isinstance(sql, str):
        return False, f"参数类型错误: 期望字符串，实际是 {type(sql).__name__}"
    if len(sql.strip()) == 0:
        return False, "参数错误: sql 是空白字符串"

    return True, None


# ============================================================
# 5. Agent 循环
# ============================================================
def run_agent(user_question: str, execute_sql_fn):
    messages = [{"role": "user", "content": user_question}]

    print("=" * 60)
    print(f"用户: {user_question}")
    print("=" * 60)

    while True:
        # API 调用（带重试）
        try:
            response = call_claude_with_retry(
                model="deepseek-v4-pro",
                max_tokens=1024,
                system=(
                    "你是一个数据库管理助手，连接着真实的 rookieDB 数据库。"
                    "用户问数据库相关问题时，使用 execute_sql 工具执行查询。"
                    "如果工具返回了错误信息，分析错误原因后修正 SQL 重试，"
                    "不要放弃，直到查到正确结果。"
                    "数据库中有三张表：Students（sid, name, major, gpa）、"
                    "Courses（cid, name, department）、"
                    "Enrollments（sid, cid）。"
                ),
                messages=messages,
                tools=[execute_sql_tool],
            )
        except Exception as e:
            print(f"\n  ❌ [API 失败] 重试 {MAX_RETRIES} 次仍然失败: {e}")
            break

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

        # 执行工具（带参数校验 + 执行错误处理）
        tool_results = []
        for tool_use in tool_uses:
            # 参数校验
            valid, error_msg = validate_tool_input(tool_use)
            if not valid:
                print(f"  ❌ [参数校验] {error_msg}")
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": tool_use.id,
                    "content": error_msg,
                    "is_error": True,
                })
                continue

            # 执行工具
            try:
                result = execute_sql_fn(tool_use.input["sql"])
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": tool_use.id,
                    "content": result,
                })
            except Exception as e:
                print(f"  ❌ [工具执行失败] {e}")
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": tool_use.id,
                    "content": f"执行失败: {e}。请检查 SQL 语句并重试。",
                    "is_error": True,
                })

        messages.append({"role": "user", "content": tool_results})
        print(f"  🔄 [结果塞回，继续...]")


# ============================================================
# 6. 错误场景测试
# ============================================================
if __name__ == "__main__":
    db = RookieDBConnection()
    db.connect()
    execute_sql_fn = make_execute_sql(db)

    # ---- 场景 1: Claude 自己犯了语法错误，应该自我修正 ----
    print("=" * 60)
    print("场景 1：SQL 语法错误 → Agent 自动修正")
    print("=" * 60)
    run_agent(
        "帮我查一下 Students 表里 GPA 最高的 3 个学生",
        execute_sql_fn
    )

    # ---- 场景 2: 参数校验 — 如果 Claude 传了空 sql ----
    print()
    print("=" * 60)
    print("场景 2：正常查询，验证参数校验逻辑不误伤")
    print("=" * 60)
    run_agent(
        "帮我查一下 Courses 表里有哪些课程",
        execute_sql_fn
    )

    # ---- 场景 3: 不存在的表 — rookieDB 返回错误，Agent 应识别 ----
    print()
    print("=" * 60)
    print("场景 3：查不存在的表 → Agent 应正确处理错误信息")
    print("=" * 60)
    run_agent(
        "帮我查一下 Teachers 表里有哪些老师",
        execute_sql_fn
    )

    db.close()
