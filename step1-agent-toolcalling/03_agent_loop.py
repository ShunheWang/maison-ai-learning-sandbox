"""
单元 2.1：Tool Calling 循环 — Agent 的大脑

流程：
  用户提问
    ↓
  调用 Claude（带 tools）
    ↓
  Claude 返回 text？→ 打印回复，结束
  Claude 返回 tool_use？→ 执行工具 → 把结果塞回去 → 再调 Claude
    ↑_______________________________________________↓
                  循环，直到 Claude 不再要调工具

学习点：
  1. tool_use → 去执行 → tool_result → 再调 Claude 的完整循环
  2. 消息数组怎么积累（每轮的消息都要拼进去）
  3. tool_use_block.id 跟 tool_result 的 tool_use_id 要对应
"""

import anthropic
import os
import json
from pathlib import Path

# 兼容 IDE 直接运行：从 .env 文件加载环境变量
# 终端跑会从 ~/.zshrc 加载，IDE 跑不会，所以手动读一下
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
# 1. 定义工具（跟 1.2 一样）
# ============================================================
execute_sql_tool = {
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


# ============================================================
# 2. 真正执行工具的函数（先 mock，单元 4 再换真实现）
# ============================================================
def execute_sql(sql: str):
    """假的数据库，硬编码返回一些数据"""
    print(f"\n  🔧 [执行工具] execute_sql(sql={sql!r})")

    if "Students" in sql:
        return [
            {"id": 1, "name": "张三", "age": 20, "major": "计算机科学"},
            {"id": 2, "name": "李四", "age": 22, "major": "软件工程"},
            {"id": 3, "name": "王五", "age": 21, "major": "数据科学"},
        ]
    elif "Courses" in sql:
        return [
            {"id": 1, "name": "数据库原理", "teacher": "王教授", "credits": 3},
            {"id": 2, "name": "操作系统", "teacher": "刘教授", "credits": 4},
        ]
    else:
        return [{"message": "查询成功，0 条结果"}]


# ============================================================
# 3. Agent 循环
# ============================================================
def run_agent(user_question: str):
    """
    Agent 的核心循环：
    只要 Claude 返回 tool_use，就执行工具、塞结果、继续问。
    直到 Claude 返回 end_turn（说完了）才结束。
    """

    # 消息历史 — 先从用户问题开始
    messages = [
        {"role": "user", "content": user_question}
    ]

    print("=" * 60)
    print(f"用户: {user_question}")
    print("=" * 60)

    while True:
        # 调用 Claude
        response = client.messages.create(
            model="deepseek-v4-pro",
            max_tokens=500,
            system="你是一个数据库管理助手。用户问数据库相关问题时，使用 execute_sql 工具执行查询。",
            messages=messages,
            tools=[execute_sql_tool],
        )

        # ------------------------------------------
        # 处理 Claude 的回复
        # ------------------------------------------
        tool_uses = []       # Claude 想调用的工具
        assistant_text = []  # Claude 说的文字

        for block in response.content:
            if block.type == "text":
                assistant_text.append(block.text)
                print(f"\n  💬 [Claude 文字] {block.text}")
            elif block.type == "tool_use":
                tool_uses.append(block)
                print(f"\n  🔨 [Claude 要调工具] {block.name}")
                print(f"     参数: {json.dumps(block.input, ensure_ascii=False)}")

        # 如果 Claude 没有要调工具 → 对话结束
        if response.stop_reason != "tool_use":
            print(f"\n  ✅ 对话结束 (stop_reason={response.stop_reason})")
            break

        # ------------------------------------------
        # Claude 要调工具 → 执行，然后继续循环
        # ------------------------------------------

        # 先把 Claude 的完整回复拼进消息历史
        # (assistant 消息里的 content 是它返回的原样)
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

        messages.append({
            "role": "assistant",
            "content": assistant_content
        })

        # 执行每个工具，拼出 tool_result
        tool_results = []
        for tool_use in tool_uses:
            if tool_use.name == "execute_sql":
                result = execute_sql(tool_use.input["sql"])
            else:
                result = {"error": f"未知工具: {tool_use.name}"}

            tool_results.append({
                "type": "tool_result",
                "tool_use_id": tool_use.id,      # ← 必须对应！告诉 Claude 这是哪个调用的结果
                "content": json.dumps(result, ensure_ascii=False),
            })

        # 把结果作为 user 消息塞回消息历史
        messages.append({
            "role": "user",
            "content": tool_results
        })

        print(f"\n  🔄 [把结果塞回给 Claude，继续...]")

    # 循环结束
    print()
    print("=" * 60)
    print("最终消息历史 (供学习查看)：")
    print("=" * 60)
    for i, msg in enumerate(messages):
        role = msg["role"]
        content = msg["content"]
        if isinstance(content, str):
            print(f"[{i}] {role}: {content[:100]}")
        elif isinstance(content, list):
            for c in content:
                if isinstance(c, dict):
                    if c.get("type") == "text":
                        print(f"[{i}] {role}.text: {c['text'][:80]}")
                    elif c.get("type") == "tool_use":
                        print(f"[{i}] {role}.tool_use: {c['name']}({json.dumps(c.get('input', {}), ensure_ascii=False)})")
                    elif c.get("type") == "tool_result":
                        print(f"[{i}] {role}.tool_result: id={c['tool_use_id'][:30]}..., content={c['content'][:60]}")


# ============================================================
# 跑！
# ============================================================
if __name__ == "__main__":
    run_agent("帮我查一下 Students 表里有哪些学生")