"""
Tool Use 笔记配套 Demo

演示笔记中的关键改进：
  1. 更好的 description（3-4 句，覆盖做什么/何时用/参数说明/限制）
  2. strict mode（参数强制校验）
  3. input_examples（给 Claude 看调用例子）
  4. 错误处理（is_error + 清晰的错误信息）
  5. 对比老的 tool 定义 vs 优化后的

运行对比：python3 demo_improved_tool.py
"""

import anthropic
import os
import json
from pathlib import Path

# 加载 .env
env_file = Path(__file__).parent.parent.parent.parent / ".env"
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
# 对比一：旧 Tool 定义 vs 新 Tool 定义
# ============================================================

# 旧版（02_define_tool.py 的版本）
old_tool = {
    "name": "execute_sql",
    "description": "在 rookieDB 数据库上执行一条 SQL 语句。支持 SELECT、INSERT、UPDATE、DELETE。查询结果以表格形式返回。",
    "input_schema": {
        "type": "object",
        "properties": {
            "sql": {
                "type": "string",
                "description": "要执行的 SQL 语句，例如：SELECT * FROM Students WHERE age > 20"
            }
        },
        "required": ["sql"]
    }
}

# 新版（按最佳实践优化后）
new_tool = {
    "name": "execute_sql",
    "strict": True,  # ← 新增：强制参数校验
    "description": (
        "在 rookieDB 数据库上执行一条 SQL 语句。"
        "支持 SELECT、INSERT、UPDATE、DELETE 操作（DML）。"
        "查询结果以 JSON 数组形式返回，每条记录是一个对象。"
        "当用户需要查询、插入、更新或删除数据库中的数据时使用此工具。"
        "注意：此工具不支持 CREATE/ALTER/DROP TABLE 等 DDL 操作。"
        "如需了解表结构，请执行 SELECT * FROM information_schema.tables。"
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "sql": {
                "type": "string",
                "description": "要执行的 SQL 语句。仅支持 DML。例如：SELECT * FROM Students WHERE age > 20"
            }
        },
        "required": ["sql"],
        "additionalProperties": False  # ← strict mode 必须加
    },
    "input_examples": [  # ← 新增：给 Claude 看例子
        {"sql": "SELECT * FROM Students"},
        {"sql": "SELECT name, age FROM Students WHERE major = '计算机科学'"},
        {"sql": "INSERT INTO Students VALUES (4, '赵六', 23, '人工智能')"},
    ]
}


# ============================================================
# 演示：模拟工具执行 + 错误处理
# ============================================================

def execute_sql(sql: str):
    """模拟数据库——大部分成功，特定 SQL 触发错误看 error handling"""
    sql_lower = sql.lower().strip()

    # 模拟：DROP TABLE 不允许
    if "drop" in sql_lower:
        raise ValueError("Error: DDL 操作不允许。此工具仅支持 SELECT/INSERT/UPDATE/DELETE。")

    # 模拟：连接失败
    if "nonexistent_table" in sql_lower:
        raise ConnectionError("ConnectionError: 无法连接 rookieDB (端口 18600)。请确认 Server 已启动。")

    # 正常返回
    if "students" in sql_lower:
        return [
            {"id": 1, "name": "张三", "age": 20, "major": "计算机科学"},
            {"id": 2, "name": "李四", "age": 22, "major": "软件工程"},
            {"id": 3, "name": "王五", "age": 21, "major": "数据科学"},
        ]
    return [{"message": "查询成功，0 条结果"}]


def run_agent(user_question, system_prompt=None):
    """一次性对话（不循环），演示单个回合的工具调用与处理"""
    if system_prompt is None:
        system_prompt = "你是一个数据库管理助手。在回答用户问题之前，先使用 execute_sql 工具查询数据库。"

    messages = [{"role": "user", "content": user_question}]

    print(f"\n{'='*60}")
    print(f"用户: {user_question}")
    print(f"{'='*60}")

    while True:
        response = client.messages.create(
            model="deepseek-v4-pro",
            max_tokens=500,
            system=system_prompt,
            messages=messages,
            tools=[new_tool],  # 使用优化后的 tool
        )

        # 解析回复
        tool_uses = []
        for block in response.content:
            if block.type == "text":
                print(f"  💬 [Claude] {block.text}")
            elif block.type == "tool_use":
                tool_uses.append(block)
                print(f"  🔨 [tool_use] {block.name}({json.dumps(block.input, ensure_ascii=False)})")

        if response.stop_reason != "tool_use":
            print(f"  ✅ 结束 (stop_reason={response.stop_reason})")
            break

        # --- 执行工具 + 错误处理 ---
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

        # 执行工具（含错误处理）
        tool_results = []
        for tool_use in tool_uses:
            try:
                result = execute_sql(tool_use.input["sql"])
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": tool_use.id,
                    "content": json.dumps(result, ensure_ascii=False),
                })
            except Exception as e:
                # ★ 错误处理：is_error=True + 清晰的错误描述
                print(f"  ⚠️  [工具错误] {e}")
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": tool_use.id,
                    "content": str(e),
                    "is_error": True,  # ← 告诉 Claude 出错了
                })

        messages.append({"role": "user", "content": tool_results})
        print(f"  🔄 [塞回结果，继续循环...]")


# ============================================================
# 跑 3 个场景
# ============================================================

if __name__ == "__main__":
    print("=" * 60)
    print("Tool Use 笔记 Demo — 演示 3 个场景")
    print("=" * 60)

    # 场景 1：正常查询
    run_agent("帮我查一下 Students 表里有哪些学生")

    # 场景 2：触发 DDL 错误（Claude 会自动修正）
    run_agent("帮我把 Students 表删了重建")

    # 场景 3：触发连接错误
    run_agent("查 nonexistent_table 表的数据")
