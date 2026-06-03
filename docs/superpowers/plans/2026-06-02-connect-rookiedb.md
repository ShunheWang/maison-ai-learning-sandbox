# 单元 4：接上 rookieDB 实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 新建 `04_connect_rookiedb.py`，把 mock 数据替换成真实 rookieDB socket 连接，端到端验证完 8 步 CRUD 场景。

**Architecture:** 复用 `03_agent_loop.py` 的 Agent 循环，封装 `RookieDBConnection` 类管理 socket 连接。启动时连接一次，会话复用，结束时断开。

**Tech Stack:** Python 3, `socket` (标准库), Anthropic SDK (DeepSeek 兼容层)

**注意:** 本项目无测试框架，验收方式为手动执行 8 步 CRUD 场景，观察输出确认正确。

---

## 文件结构

- **Create:** `04_connect_rookiedb.py` — 完整学习单元，独立可运行
- **Modify:** `notes/learning-journal.md` — 添加学习记录
- **Modify:** `notes/db-agent-plan.md` — 勾选单元 4

每个文件职责：
- `04_connect_rookiedb.py`：RookieDBConnection 类 + execute_sql 函数 + Agent 循环 + CRUD 验证
- 跟 03 关系：Agent 循环照搬，只替换 execute_sql 和 tool 定义

---

### Task 1: 创建文件骨架和环境变量加载

**Files:**
- Create: `04_connect_rookiedb.py`

- [ ] **Step 1: 创建文件头部（导入、环境变量加载）**

```python
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
            os.environ.setdefault(key.strip(), value.strip())

client = anthropic.Anthropic(
    base_url=os.environ.get("ANTHROPIC_BASE_URL", "https://api.anthropic.com"),
)
```

### Task 2: 实现 RookieDBConnection 类

**Files:**
- Modify: `04_connect_rookiedb.py`

- [ ] **Step 1: 写 RookieDBConnection 类**

```python
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
```

### Task 3: 定义 Tool

**Files:**
- Modify: `04_connect_rookiedb.py`

- [ ] **Step 1: 写 tool 定义（修正 DDL 描述）**

根据 `rookiedb-review.md` 发现，rookieDB 实际支持 DDL，修正 description：

```python
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
```

### Task 4: 实现 Agent 循环（含 execute_sql 工厂）

**Files:**
- Modify: `04_connect_rookiedb.py`

设计要点：`db` 不应该用全局变量。用闭包（`make_execute_sql`）捕获 `db` 引用，`run_agent` 通过参数接收 `execute_sql_fn`。

- [ ] **Step 1: 写 make_execute_sql 工厂函数和 run_agent**

```python
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
            max_tokens=500,
            system=(
                "你是一个数据库管理助手，连接着真实的 rookieDB 数据库。"
                "用户问数据库相关问题时，使用 execute_sql 工具执行查询。"
                "在回答用户问题之前，先使用工具查询数据库获取最新数据。"
            ),
            messages=messages,
            tools=[execute_sql_tool],
        )

        tool_uses = []
        for block in response.content:
            if block.type == "text":
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
```

### Task 5: 写主流程和 CRUD 验证

**Files:**
- Modify: `04_connect_rookiedb.py`

- [ ] **Step 1: 写 __main__ 入口（8 步 CRUD 验证）**

```python
# ============================================================
# 5. 跑 — 验证 8 步 CRUD
# ============================================================
if __name__ == "__main__":
    db = RookieDBConnection()

    try:
        db.connect()
        execute_sql_fn = make_execute_sql(db)

        # 1. Read — 列出所有表
        run_agent("帮我查一下数据库里有哪些表", execute_sql_fn)

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
```

- [ ] **Step 2: 检查完整文件结构确保连贯**

确认文件自上而下的结构：
1. `"""docstring"""` 学习说明
2. 导入 + `.env` 加载 + `client` 初始化
3. `ROOKIEDB_HOST/PORT` 常量
4. `RookieDBConnection` 类
5. `execute_sql_tool` 定义
6. `make_execute_sql(db)` 工厂函数
7. `run_agent(question, execute_sql_fn)` Agent 循环
8. `if __name__ == "__main__":` 入口 + 8 步 CRUD

### Task 6: 验证

**Files:**
- (无新建)

- [ ] **Step 1: 启动 rookieDB Server**

```bash
cd /Users/shunhewang/melbourne/cs186/berkeley-sp26-rookiedb
java -cp target/classes edu.berkeley.cs186.database.cli.Server &
```

确认输出中有 "=> " 提示符。

- [ ] **Step 2: 运行 04_connect_rookiedb.py**

```bash
python3 /Users/shunhewang/melbourne/idea-warehouse/maison-ai-learning-sandbox/04_connect_rookiedb.py
```

- [ ] **Step 3: 观察 8 步 CRUD 输出**

对照验证：

| 步骤 | 预期 |
|------|------|
| 1. 查表 | 输出包含 Students、Courses、Enrollments |
| 2. CS 学生 | 返回 CS 专业的学生列表，含 GPA 等字段 |
| 3. 插入 | INSERT 成功，Claude 确认插入 |
| 4. 验证插入 | 返回学号 999 的记录，GPA=3.5 |
| 5. 更新 | UPDATE 成功，Claude 确认更新 |
| 6. 验证更新 | 学号 999 的 GPA=4.0 |
| 7. 删除 | DELETE 成功，Claude 确认删除 |
| 8. 验证删除 | 学号 999 不存在，Claude 说明已删除或查不到 |

- [ ] **Step 4: 如有问题，修正代码**

如果输出不符合预期，检查：
- rookieDB Server 是否正常启动
- socket 通信是否正常（可以先用 `client.py` 测试连接）
- Claude 是否返回了正确的 SQL

### Task 7: 更新学习笔记

**Files:**
- Modify: `notes/learning-journal.md`
- Modify: `notes/db-agent-plan.md`

- [ ] **Step 1: 更新 learning-journal.md**

在文件末尾添加：

```markdown
---

## 2026-06-02 晚 — 单元 4：接上 rookieDB

**产出**：`04_connect_rookiedb.py`

**核心收获**：
- Python socket 连 Java 进程：纯文本协议，发送 SQL → 接收结果
- 把 mock 替换成真实数据库，Agent 循环逻辑完全不用改
- 连接生命周期：单连接复用，try/finally 保证关闭
- execute_sql 通过闭包捕获 db 引用，避免全局变量

**验证结果**：8 步 CRUD（Read × 4, Create × 1, Update × 1, Delete × 1, 每步验证）全部通过

**修正**：Tool description 之前错误声明"不支持 DDL"，实际 rookieDB 完整支持 CREATE/DROP TABLE/INDEX
```

- [ ] **Step 2: 更新 db-agent-plan.md**

把 `- [ ] 单元 4 接 rookieDB` 改为：
```markdown
- [x] 单元 4 接 rookieDB — `04_connect_rookiedb.py`
```

### Task 8: 提交

- [ ] **Step 1: 提交所有变更**

```bash
git add 04_connect_rookiedb.py notes/learning-journal.md notes/db-agent-plan.md
git commit -m "feat: 单元 4 — 接上 rookieDB，端到端 CRUD 验证通过"
```
