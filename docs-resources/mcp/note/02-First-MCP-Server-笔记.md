# 第一个 MCP Server：从零写一个 Calculator Server

> 来源：mcp-for-beginners Module 3 — 01-first-server
> 整理时间：2026-06-04
> 只保留 Python 内容，其他语言跳过

---

## 一句话总结

**用 `FastMCP` + `@mcp.tool()` 装饰器注册工具，`mcp.run()` 启动，`mcp dev` 调试。10 行代码就能跑起来。**

---

## 1. 完整代码（10 行）

```python
# server.py
from mcp.server.fastmcp import FastMCP

# 创建 Server
mcp = FastMCP("Demo")

# 注册一个 Tool
@mcp.tool()
def add(a: int, b: int) -> int:
    """Add two numbers"""
    return a + b

# 注册一个 Resource
@mcp.resource("greeting://{name}")
def get_greeting(name: str) -> str:
    """Get a personalized greeting"""
    return f"Hello, {name}!"

# 启动
if __name__ == "__main__":
    mcp.run()
```

就这么简单。对比 Step 1 手写 JSON Schema + 函数 + if/elif 分发，MCP 的写法少了一个数量级的代码。

---

## 2. 逐行拆解

### 2.1 创建 Server

```python
from mcp.server.fastmcp import FastMCP
mcp = FastMCP("Demo")          # ← 这个名字会出现在能力协商中
```

FastMCP 内部自动处理了：
- JSON-RPC 2.0 消息解析
- `tools/list` 响应（从装饰器自动生成 JSON Schema）
- 能力协商（initialize 握手）
- STDIO 传输

**你只需要给 Server 起个名字，什么都不用配。**

### 2.2 注册 Tool

```python
@mcp.tool()
def add(a: int, b: int) -> int:
    """Add two numbers"""
    return a + b
```

FastMCP 自动做的事：
- **`a: int, b: int`** → 自动生成 input_schema（类型推断）
- **`"""Add two numbers"""`** → 自动变成 tool 的 description
- **`-> int`** → 自动推断返回类型
- **函数名 `add`** → 自动变成 tool name

对比 Step 1 我们手写的：

```python
# 以前要写这么一堆
execute_sql_tool = {
    "name": "execute_sql",
    "description": "在 rookieDB 上执行 SQL 语句...",
    "input_schema": {
        "type": "object",
        "properties": {
            "sql": {"type": "string", "description": "要执行的 SQL 语句"}
        },
        "required": ["sql"]
    }
}
```

**MCP 把这堆 boilerplate 全干掉了。** Python 类型注解就是 Schema，docstring 就是 description。

### 2.3 注册 Resource

```python
@mcp.resource("greeting://{name}")
def get_greeting(name: str) -> str:
    """Get a personalized greeting"""
    return f"Hello, {name}!"
```

`"greeting://{name}"` 是 URI 模板，`{name}` 会自动跟函数参数 `name` 绑定。Client 调 `resources/read {uri: "greeting://World"}` → 返回 `"Hello, World!"`。

### 2.4 启动 Server

```python
if __name__ == "__main__":
    mcp.run()
```

`mcp.run()` 内部做的事：
1. 启动 STDIO 传输（监听 stdin，写 stdout）
2. 等待 Client 连接
3. 处理 JSON-RPC 消息（initialize、tools/list、tools/call...）
4. 进程结束自动清理

---

## 3. 运行和测试

### 3.1 两种启动方式

| 方式 | 命令 | 效果 |
|------|------|------|
| 直接跑 | `python3 server.py` | 只有 Server，等待 STDIO 输入，终端无输出 |
| Inspector | `mcp dev server.py` | Server + Inspector Web 界面，可视化测试 |

`mcp dev` 一键启动两个东西：Server 进程 + Inspector（浏览器页面）。`Ctrl+C` 两个一起停。

### 3.2 Inspector 使用步骤

1. `mcp dev server.py` → 浏览器打开 `http://localhost:6274`
2. 确认 Transport Type 为 STDIO，Command 为 `mcp`，Arguments 为 `run server.py`
3. Connect → Tools → List Tools → 选工具 → 填参数 → Call Tool

---

## 4. 关键认知

### 4.1 装饰器就是注册

```python
@mcp.tool()        # → FastMCP 内部：注册一个 Tool，名字=函数名，Schema=参数类型
@mcp.resource(...) # → FastMCP 内部：注册一个 Resource，URI=模板
@mcp.prompt()      # → FastMCP 内部：注册一个 Prompt（原文没展示，语法类似）
```

装饰器本质上等价于：
```python
def add(a: int, b: int) -> int:
    return a + b
mcp.add_tool(add, name="add", description="Add two numbers")
```

### 4.2 Python 类型注解 = JSON Schema

| Python 写法 | 自动生成的 JSON Schema |
|------------|----------------------|
| `a: int` | `{"type": "integer"}` |
| `a: str` | `{"type": "string"}` |
| `a: float` | `{"type": "number"}` |
| `name: str = "World"` | 默认值 `"World"` |
| `-> int` | 返回类型 int |

**不需要手写 JSON Schema，FastMCP 自动从类型注解推断。**

### 4.3 返回值的格式

Tool 函数直接 return 值就行，FastMCP 会自动包装成 MCP 标准响应格式：
```python
# 你写的
return a + b

# FastMCP 自动变成
{"content": [{"type": "text", "text": "8"}]}
```

### 4.4 Server 启动 = 进入事件循环

`mcp.run()` 会让 Server 进程进入 STDIO 监听状态，不退出。这就是为什么 Server 是个独立进程——它启动后就一直等着收 JSON-RPC 消息。

---

## 5. 跟我们现在代码的对比

```
现在写法（02_define_tool.py）          MCP 写法（FastMCP）
──────────────────────────            ──────────────────
手写 JSON Schema（20 行）              @mcp.tool() 一行
手写函数实现                           def + 类型注解
Agent 循环里 if/elif 分发              FastMCP 自动分发
手工拼 tool_use + tool_result         FastMCP 自动处理
```

MCP 不是"又多了一套东西要学"，而是**把我们已经手工在做的事情标准化了**。

---

## 6. 一个 Server 的完整生命周期

```
1. python3 server.py
   → FastMCP 初始化，注册所有 @mcp.tool() / @mcp.resource()
   → 启动 STDIO 传输，进程进入等待状态

2. Client 连接（通过 MCP Inspector 或 Agent 脚本）
   → initialize 握手
   → tools/list → Server: "我有 add 工具"
   → resources/list → Server: "我有 greeting 资源"

3. Client 调用
   → tools/call {name: "add", arguments: {a: 3, b: 5}}
   → Server 执行 add(3, 5) → 返回 8
   → resources/read {uri: "greeting://World"}
   → Server 执行 get_greeting("World") → 返回 "Hello, World!"

4. 进程结束
   → STDIO 关闭
   → mcp.run() 退出
```

---

## 7. 原文中跳过的内容

- 其他语言（TypeScript/Java/C#/Rust）的完整示例 — 不需要
- Maven/Spring Boot 配置 — Java 专属，不需要
- CORS 配置、API key 验证 — 本地开发用不上
- Assignment 和 Solution — 练习题，需要时再看
