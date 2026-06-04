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
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.settimeout(10)
            self.sock.connect((self.host, self.port))
            self._recv_until_prompt()
            print(f"[rookieDB] 已连接 {self.host}:{self.port}", file=sys.stderr)
        except Exception:
            self.sock = None
            raise

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

# ============================================================
# 数据库连接（懒初始化，兼容 python3 和 mcp run 两种启动方式）
# ============================================================
_db = None


def get_db():
    """获取数据库连接，首次调用时自动连接"""
    global _db
    if _db is None:
        db = RookieDBConnection()
        try:
            db.connect()
            _db = db
        except Exception as e:
            print(
                f"WARNING: Cannot connect to rookieDB ({e}).",
                file=sys.stderr,
            )
            _db = None
    return _db


# ============================================================
# MCP Tool: execute_sql
# ============================================================
@mcp.tool()
def execute_sql(sql: str) -> str:
    """Execute a SQL statement on the rookieDB database.

    Supports SELECT, INSERT, UPDATE, DELETE, CREATE TABLE, DROP TABLE.
    The database contains three tables:
      Students (sid, name, major, gpa)
      Courses (cid, name, department)
      Enrollments (sid, cid)
    """
    db = get_db()
    if db is None:
        return (
            "ERROR: Cannot connect to rookieDB on localhost:18600. "
            "Please ensure the rookieDB server is running."
        )
    try:
        result = db.execute(sql)
        return result
    except Exception as e:
        return f"ERROR: {e}"


# ============================================================
# 已知表结构（rookieDB 不支持 SHOW TABLES / DESCRIBE，需要硬编码）
# ============================================================
_SCHEMA = {
    "Students": {
        "columns": ["sid", "name", "major", "gpa"],
        "types": {"sid": "INTEGER", "name": "TEXT", "major": "TEXT", "gpa": "FLOAT"},
    },
    "Courses": {
        "columns": ["cid", "name", "department"],
        "types": {"cid": "INTEGER", "name": "TEXT", "department": "TEXT"},
    },
    "Enrollments": {
        "columns": ["sid", "cid"],
        "types": {"sid": "INTEGER", "cid": "INTEGER"},
    },
}


def _is_valid_table(table_name: str) -> bool:
    """检查表名是否合法，防止 SQL 注入"""
    return table_name in _SCHEMA


# ============================================================
# MCP Tool: list_tables
# ============================================================
@mcp.tool()
def list_tables() -> str:
    """List all tables in the database.

    Returns the names of all available tables in rookieDB.
    Use this to see what data is available before querying.
    """
    db = get_db()
    if db is None:
        return "ERROR: Cannot connect to rookieDB on localhost:18600."

    table_names = list(_SCHEMA.keys())
    return f"Tables ({len(table_names)}): " + ", ".join(table_names)


# ============================================================
# MCP Tool: describe_table
# ============================================================
@mcp.tool()
def describe_table(table_name: str) -> str:
    """Show the column names and types for a specific table.

    Args:
        table_name: The name of the table to describe (e.g., 'Students', 'Courses', 'Enrollments').

    Returns the column definitions for the given table.
    """
    if not _is_valid_table(table_name):
        return f"ERROR: Unknown table '{table_name}'. Available tables: {', '.join(_SCHEMA.keys())}"

    db = get_db()
    if db is None:
        return "ERROR: Cannot connect to rookieDB on localhost:18600."

    # 通过 SELECT * LIMIT 1 获取列名（解析 header 行）
    try:
        result = db.execute(f"SELECT * FROM {table_name} LIMIT 1;")
    except Exception as e:
        return f"ERROR: {e}"

    # 解析 header 行格式: " sid | name              | major     | gpa"
    lines = result.strip().split("\n")
    header_line = None
    for line in lines:
        if "|" in line and "---" not in line:
            header_line = line
            break

    if header_line is None:
        # 空表（没有数据行），用已知 schema 兜底
        schema = _SCHEMA[table_name]
        cols = [f"  {col}: {schema['types'][col]}" for col in schema["columns"]]
        return f"Table: {table_name} (empty)\n" + "\n".join(cols)

    columns = [c.strip() for c in header_line.split("|")]
    schema = _SCHEMA[table_name]
    rows = [f"  {col}: {schema['types'].get(col, 'UNKNOWN')}" for col in columns if col]

    return f"Table: {table_name}\n" + "\n".join(rows)


# ============================================================
# MCP Resource: database schema
# ============================================================
@mcp.resource("database://schema")
def get_schema() -> str:
    """Get the database schema (tables and columns)."""
    return (
        "Database: rookieDB\n"
        "\n"
        "Table: Students\n"
        "  Columns: sid (INTEGER), name (TEXT), major (TEXT), gpa (FLOAT)\n"
        "\n"
        "Table: Courses\n"
        "  Columns: cid (INTEGER), name (TEXT), department (TEXT)\n"
        "\n"
        "Table: Enrollments\n"
        "  Columns: sid (INTEGER), cid (INTEGER)\n"
    )

# ============================================================
# 启动
# ============================================================
if __name__ == "__main__":
    mcp.run()