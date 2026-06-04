"""
单元 1.2：Tool 定义 — 告诉 Claude 它可以做什么

学习点：
  1. Tool 的 JSON Schema 结构：name, description, input_schema
  2. 在 messages.create() 里传入 tools 参数
  3. 观察 Claude 的响应：text 还是 tool_use？
  4. stop_reason 的不同值：end_turn vs tool_use
"""

import anthropic
import os
import json
from pathlib import Path

# 兼容 IDE 直接运行：从 .env 文件加载环境变量
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
# 定义工具：execute_sql
# ============================================================
# 这是给 Claude 的"菜单"——告诉它「你可以调这个函数，参数是这样」
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
# 场景 1：问一个不需要工具的问题
# ============================================================
print("=" * 60)
print("场景 1：不需要工具的普通提问")
print("=" * 60)

response = client.messages.create(
    model="deepseek-v4-pro",
    max_tokens=200,
    system="你是一个数据库管理助手。用户问数据库相关问题时，使用 execute_sql 工具执行查询。",
    messages=[
        {"role": "user", "content": "你好，请问 SQL 是什么意思？"}
    ],
    tools=[execute_sql_tool]  # ← 关键！把工具列表传进去
)

print(f"stop_reason: {response.stop_reason}")
print(f"回复内容：")
for block in response.content:
    if block.type == "thinking":
        print(f"  [思考] {block.thinking[:200]}...")
    elif block.type == "text":
        print(f"  [文本] {block.text}")
    elif block.type == "tool_use":
        print(f"  [工具调用!] name={block.name}, input={json.dumps(block.input, ensure_ascii=False)}")
    else:
        print(f"  [未知类型] {block.type}")

# ============================================================
# 场景 2：问一个需要工具的问题
# ============================================================
print()
print("=" * 60)
print("场景 2：需要工具的数据库查询")
print("=" * 60)

response = client.messages.create(
    model="deepseek-v4-pro",
    max_tokens=200,
    system="你是一个数据库管理助手。用户问数据库相关问题时，使用 execute_sql 工具执行查询。",
    messages=[
        {"role": "user", "content": "帮我查一下 Students 表里有哪些学生"}
    ],
    tools=[execute_sql_tool]
)

print(f"stop_reason: {response.stop_reason}")
print(f"回复内容：")
for block in response.content:
    if block.type == "thinking":
        print(f"  [思考] {block.thinking[:200]}...")
    elif block.type == "text":
        print(f"  [文本] {block.text}")
    elif block.type == "tool_use":
        print(f"  [工具调用!]")
        print(f"    id:   {block.id}")
        print(f"    name: {block.name}")
        print(f"    input: {json.dumps(block.input, ensure_ascii=False)}")
    else:
        print(f"  [未知类型] {block.type}")

# ============================================================
# 关键观察点（学完后自己对着看）：
# ============================================================
# 1. 场景 1 的 stop_reason 应该是 "end_turn"（Claude 觉得不需要工具）
# 2. 场景 2 的 stop_reason 应该是 "tool_use"（Claude 决定调用工具）
# 3. tool_use block 里有什么？
#    - name: 它要调哪个工具
#    - input: 它填了什么参数
#    - id: 每轮工具调用的唯一 ID，后面给 tool_result 时要对应
# 4. 对比两次 response.content，结构不同：
#    - 不用工具 → content 里只有 text blocks
#    - 用工具 → content 里同时有 text + tool_use blocks
print()
print("=" * 60)
print("单元 1.2 学完 — 你知道了：")
print("  1. Tool 怎么定义（name + description + input_schema）")
print("  2. 怎么传给 API（tools=[...]）")
print("  3. Claude 什么时候调用工具（stop_reason='tool_use'）")
print("  4. tool_use block 里有什么信息")
print("=" * 60)