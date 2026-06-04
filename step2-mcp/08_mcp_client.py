"""
08_mcp_client.py — MCP Client：用代码连 MCP Server，自动发现和调用工具

学习点：
  - StdioServerParameters: 指定 Server 如何启动（Client 负责拉起 Server）
  - stdio_client: 建立 STDIO 连接
  - ClientSession: Client 会话（initialize → list_tools → call_tool）
  - 6 个核心方法：list_tools、call_tool、list_resources、read_resource

运行方式：
  python3 step2-mcp/08_mcp_client.py

对比 07_first_mcp_server.py：
  07 = MCP Server（注册工具、等待调用）
  08 = MCP Client（发现工具、发起调用）
  两个独立进程，通过 STDIO + JSON-RPC 通信
"""

import asyncio
import os

# 屏蔽 Server 端日志，保持输出干净
os.environ["FASTMCP_LOG_LEVEL"] = "ERROR"

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


async def run():
    # ============================================================
    # 1. 指定 Server 怎么启动
    #    注意：Client 会自动启动 Server 子进程，不需要手动跑
    # ============================================================
    import pathlib
    server_file = str(pathlib.Path(__file__).parent / "07_first_mcp_server.py")
    server_params = StdioServerParameters(
        command="mcp",
        args=["run", server_file],
        env=None,
    )

    # ============================================================
    # 2. 建立连接 + 创建会话
    #    stdio_client 启动 Server 子进程 + 建立 STDIO 管道
    #    ClientSession 管理 JSON-RPC 会话
    # ============================================================
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:

            # ============================================================
            # 3. 握手（initialize）
            # ============================================================
            await session.initialize()
            print("✅ 已连接 MCP Server\n")

            # ============================================================
            # 4. 发现层：看看 Server 有什么
            # ============================================================

            # --- 列出所有工具 ---
            print("=" * 50)
            print("📦 list_tools() — 发现工具有哪些")
            print("=" * 50)
            tools_result = await session.list_tools()
            for tool in tools_result.tools:
                print(f"  Tool: {tool.name}")
                print(f"    描述: {tool.description}")
                print(f"    参数: {tool.inputSchema.get('properties', {})}")
                print()

            # --- 列出所有资源 ---
            print("=" * 50)
            print("📦 list_resources() — 发现资源有哪些")
            print("=" * 50)
            resources_result = await session.list_resources()
            if resources_result.resources:
                for resource in resources_result.resources:
                    print(f"  Resource: {resource.name}")
                    print(f"    URI: {resource.uri}")
                    print()

            # ============================================================
            # 5. 调用层：执行工具和资源
            # ============================================================

            # --- 调用 add 工具 ---
            print("=" * 50)
            print("🔧 call_tool('add', {a: 3, b: 5})")
            print("=" * 50)
            result = await session.call_tool("add", arguments={"a": 3, "b": 5})
            print(f"  返回: {result.content[0].text}")
            print()

            # --- 调用 multiply 工具 ---
            print("=" * 50)
            print("🔧 call_tool('multiply', {a: 4, b: 7})")
            print("=" * 50)
            result = await session.call_tool("multiply", arguments={"a": 4, "b": 7})
            print(f"  返回: {result.content[0].text}")
            print()

            # --- 读取 greeting 资源 ---
            print("=" * 50)
            print("📖 read_resource('greeting://MCP')")
            print("=" * 50)
            result = await session.read_resource("greeting://MCP")
            print(f"  返回: {result}")

            print("\n✅ 所有操作完成")


if __name__ == "__main__":
    asyncio.run(run())
