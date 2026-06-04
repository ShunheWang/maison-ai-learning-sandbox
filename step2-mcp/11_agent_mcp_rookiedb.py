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

                # 4b. 存 assistant 消息（过滤掉 thinking block）
                assistant_blocks = [
                    b for b in response.content if b.type != "thinking"
                ]
                messages.append({"role": "assistant", "content": assistant_blocks})

                # 4c. 执行每个 tool_use（跳过 thinking）
                for block in response.content:
                    if block.type == "tool_use":
                        print(f"\n🔧 LLM 决定调: {block.name}({json.dumps(block.input, ensure_ascii=False)})")

                        # 通过 MCP Client 调用（try/except 保护）
                        try:
                            result = await session.call_tool(
                                block.name, arguments=block.input
                            )
                            if result.content and hasattr(result.content[0], "text"):
                                result_text = str(result.content[0].text)
                            else:
                                result_text = str(result)
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