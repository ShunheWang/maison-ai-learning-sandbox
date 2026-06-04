"""
10_rookiedb_mcp_server.py — MCP Server for rookieDB

学习点：
  - 把原有 TCP socket 服务包装成 MCP Tool
  - @mcp.tool() 注册数据库操作工具
  - @mcp.resource() 暴露数据库 schema
  - Server 管理连接生命周期（启动连接、断线重连）
  - Agent 不知道 socket 存在，只看到 MCP 接口

运行：
  python3 step2-mcp/10_rookiedb_mcp_server.py
  mcp dev step2-mcp/10_rookiedb_mcp_server.py  # 可视化测试
"""

import socket
import sys
import time
from mcp.server.fastmcp import FastMCP

# ============================================================
# 配置
# ============================================================
ROOKIEDB_HOST = "localhost"
ROOKIEDB_PORT = 18600

# ============================================================
# RookieDBConnection（从 06 复制，自包含）
# ============================================================
# （Task 2 填充）

# ============================================================
# FastMCP Server 实例
# ============================================================
mcp = FastMCP("rookieDB")

# （Task 3 填充工具和资源）

# ============================================================
# 启动
# ============================================================
if __name__ == "__main__":
    # （Task 4 填充启动逻辑）
    mcp.run()