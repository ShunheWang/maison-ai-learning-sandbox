"""
09_agent_with_mcp.py — LLM + MCP Client：自然语言驱动工具调用

学习点：
  - 从 MCP Server 自动发现工具（不再手写 JSON Schema）
  - 转换 MCP 工具格式 → Anthropic Tool 格式
  - LLM 自然语言输入 → 自动判断调哪个工具
  - Agent 循环中 messages 的积累过程（每次 print 出来看）
  - 跟 03_agent_loop.py 对比：工具发现和调用全部走 MCP，不硬编码

运行方式：
  python3 step2-mcp/09_agent_with_mcp.py

对比：
  03_agent_loop.py:  手写 tools=[{...}] + if/elif 分发 + 手写函数
  08_mcp_client.py:  自动发现工具，但手动指定调哪个
  09_agent_with_mcp.py: 自动发现 + LLM 自动选择 + 自然语言交互
"""

import asyncio
import os
import pathlib

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
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

# ============================================================
# 配置
# ============================================================
MODEL = "deepseek-v4-pro"
MAX_TURNS = 10

anthropic_client = Anthropic(
    api_key=os.environ["ANTHROPIC_API_KEY"],
    base_url=os.environ.get("ANTHROPIC_BASE_URL", "https://api.deepseek.com/anthropic"),
)

SYSTEM_PROMPT = "You are a helpful assistant."


# ============================================================
# 工具函数
# ============================================================
def print_messages(messages, label):
    """打印消息历史，方便理解 Agent 循环每一步 messages 的变化"""
    print(f"\n{'─' * 50}")
    print(f"📋 Messages 快照: {label} (共 {len(messages)} 条)")
    print(f"{'─' * 50}")
    for i, msg in enumerate(messages):
        role = msg["role"]
        content = msg.get("content", "")

        # 简单文本消息
        if isinstance(content, str):
            print(f"  [{i}] {role}: {content}")
            continue

        # content blocks 列表
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
                tid = block.get("tool_use_id", "")
                res = block.get("content", "")
                print(f"  [{i}] {role}.tool_result: id={tid[:12]}... result={res}")
    print(f"{'─' * 50}\n")


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


# ============================================================
# 主逻辑
# ============================================================
async def run():
    # --- 1. 启动 MCP Server ---
    server_file = str(pathlib.Path(__file__).parent / "07_first_mcp_server.py")
    server_params = StdioServerParameters(
        command="mcp", args=["run", server_file], env=None
    )

    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            # --- 2. 自动发现工具 ---
            tools_result = await session.list_tools()
            anthropic_tools = [mcp_tool_to_anthropic(t) for t in tools_result.tools]

            print("=" * 50)
            print(f"📦 从 MCP Server 发现 {len(tools_result.tools)} 个工具:")
            for t in tools_result.tools:
                print(f"  - {t.name}: {t.description}")
            print("=" * 50)

            # --- 3. 用户输入 ---
            prompt = input("\n🤔 请输入你的问题: ")

            # --- 4. Agent 循环 ---
            # messages 从只有一条 user 消息开始
            messages = [{"role": "user", "content": prompt}]
            print_messages(messages, "初始状态")

            for turn in range(MAX_TURNS):
                response = anthropic_client.messages.create(
                    model=MODEL,
                    max_tokens=1000,
                    system=SYSTEM_PROMPT,
                    messages=messages,
                    tools=anthropic_tools,
                )

                # 4a. LLM 不调工具 → 结束
                if response.stop_reason != "tool_use":
                    final_text = "".join(
                        block.text for block in response.content if block.type == "text"
                    )
                    print(f"🤖 Agent: {final_text}")
                    break

                # 4b. LLM 要调工具 → 先存 assistant 消息（过滤 thinking）
                assistant_blocks = [
                    b for b in response.content if b.type != "thinking"
                ]
                messages.append({"role": "assistant", "content": assistant_blocks})

                # 4c. 执行每个 tool_use，收集所有结果到同一条 user 消息
                #     API 要求: assistant 的所有 tool_use 必须在紧随的
                #     一条 user 消息中全部给出对应的 tool_result
                tool_results = []
                for block in response.content:
                    if block.type == "tool_use":
                        print(f"🔧 LLM 决定调: {block.name}({block.input})")

                        result = await session.call_tool(block.name, arguments=block.input)
                        result_text = str(result.content[0].text)
                        print(f"   Server 返回: {result_text}")

                        tool_results.append({
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": result_text,
                        })

                if tool_results:
                    messages.append({"role": "user", "content": tool_results})

                print_messages(messages, f"第 {turn + 1} 轮后")
            else:
                print("\n⚠️  达到最大轮数")


if __name__ == "__main__":
    asyncio.run(run())
