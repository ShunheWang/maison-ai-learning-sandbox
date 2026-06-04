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
class RookieDBConnection:
    """管理 rookieDB 的 socket 连接，支持自动重连"""

    def __init__(self, host=ROOKIEDB_HOST, port=ROOKIEDB_PORT):
        self.host = host
        self.port = port
        self.sock = None
        self._reconnect_count = 0

    def connect(self):
        """建立 TCP 连接并等待欢迎提示"""
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.settimeout(10)
        self.sock.connect((self.host, self.port))
        self._recv_until_prompt()
        print(f"[rookieDB] 已连接 {self.host}:{self.port}", file=sys.stderr)

    def execute(self, sql: str) -> str:
        """执行 SQL，自动加 ';'，断线自动重连一次"""
        if self.sock is None:
            raise ConnectionError("未连接 rookieDB，请先调用 connect()")
        if not sql.strip().endswith(";"):
            sql += ";"

        try:
            self.sock.send((sql + "\n").encode("utf-8"))
            response = self._recv_until_prompt()
            return response.strip()
        except (socket.timeout, ConnectionError, OSError) as e:
            print(f"[rookieDB] 连接异常，尝试重连: {e}", file=sys.stderr)
            self._reconnect()
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
        print(f"[rookieDB] 重连成功 (第 {self._reconnect_count} 次)", file=sys.stderr)

    def _recv_until_prompt(self) -> str:
        """收数据直到看到 '=> ' 提示符"""
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
        """发送 exit 命令并关闭连接"""
        if self.sock:
            try:
                self.sock.send(b"exit\n")
            except Exception:
                pass
            self.sock.close()
            self.sock = None
            print("[rookieDB] 已断开连接", file=sys.stderr)

    def is_connected(self) -> bool:
        """检查连接是否活跃"""
        return self.sock is not None

# ============================================================
# FastMCP Server 实例
# ============================================================
mcp = FastMCP("rookieDB")

# (Task 3 填充工具和资源)

# ============================================================
# 启动
# ============================================================
if __name__ == "__main__":
    # (Task 4 填充启动逻辑)
    mcp.run()