"""
07_first_mcp_server.py — 第一个 MCP Server：Calculator

学习点：
  - FastMCP 创建 Server
  - @mcp.tool() 装饰器注册工具（类型注解自动 → JSON Schema）
  - @mcp.resource() 注册资源（URI 模板）
  - mcp.run() 启动 STDIO 传输

运行方式：
  python3 step2-mcp/07_first_mcp_server.py          # 直接跑（STDIO 等待）
  mcp dev step2-mcp/07_first_mcp_server.py          # 用 Inspector 可视化测试（推荐）

Inspector 使用步骤：
  1. 浏览器打开 http://localhost:5173
  2. Tools → listTools → 看到 add
  3. 选 add，填 a=3, b=5 → 看到结果 8
  4. Resources → listResources → 看到 greeting://{name}
"""

from mcp.server.fastmcp import FastMCP

# ============================================================
# 创建 MCP Server
# ============================================================
mcp = FastMCP("Calculator Demo")


# ============================================================
# 注册 Tool：加法
# ============================================================
@mcp.tool()
def add(a: int, b: int) -> int:
    """Add two numbers together"""
    return a + b


# ============================================================
# 注册 Tool：乘法
# ============================================================
@mcp.tool()
def multiply(a: int, b: int) -> int:
    """Multiply two numbers together"""
    return a * b


# ============================================================
# 注册 Resource：问候
# ============================================================
@mcp.resource("greeting://{name}")
def get_greeting(name: str) -> str:
    """Get a personalized greeting"""
    return f"Hello, {name}!"


# ============================================================
# 启动
# ============================================================
if __name__ == "__main__":
    print("Calculator MCP Server 启动中...")
    print("用 mcp dev step2-mcp/07_first_mcp_server.py 可以通过 Inspector 测试")
    mcp.run()
