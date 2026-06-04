# MCP Client：从手动调用到 LLM 驱动的 Agent

> 来源：mcp-for-beginners Module 3 — 02-client + 03-llm-client
> 整理时间：2026-06-04

---

## 一句话总结

**MCP Client 做三件事：连接 Server → 发现能力 → 调用工具。加上 LLM 后，用户用自然语言交互，LLM 自动选工具——这就是我们 Step 1 Agent 循环的 MCP 版本。**

---

## 1. 两个模块的关系

```
02-client            →  手动 MCP Client（类似 Inspector，但在代码里）
                         你需要自己决定调哪个工具、传什么参数

03-llm-client        →  LLM 驱动的 MCP Client（类似我们的 Agent 循环）
                         用户说自然语言，LLM 判断调哪个工具
```

02 是基础，03 是目标。两个加起来就是：**写 Python 代码连 MCP Server，让 LLM 自动判断调用哪个工具。**

---

## 2. 纯 MCP Client（02-client）

### 2.1 Client 的核心能力

MCP Client 跟 Server 的交互就 6 个方法：

```
发现层：
  list_tools()       → Server 有什么工具？
  list_resources()   → Server 有什么数据？
  list_prompts()     → Server 有什么提示词模板？

调用层：
  call_tool(name, args)        → 执行一个工具
  read_resource(uri)           → 读取一个资源
  get_prompt(name, args)       → 获取一个提示词模板
```

对比我们 Step 1 的 Agent：发现层相当于我们手写 `tools=[...]` 列表，调用层相当于我们 `execute_sql()` 函数。区别是 MCP 自动发现，不用手写。

### 2.2 Python 代码（完整流程）

```python
import asyncio
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

# 1. 指定 Server 怎么启动
server_params = StdioServerParameters(
    command="mcp",              # 用什么命令启动 Server
    args=["run", "server.py"],  # 参数
    env=None,                    # 环境变量（可选）
)

async def run():
    # 2. 启动 Server + 建立 STDIO 连接
    async with stdio_client(server_params) as (read, write):
        # 3. 创建 Client 会话
        async with ClientSession(read, write) as session:
            # 4. 握手（initialize）
            await session.initialize()

            # 5. 发现：列出所有工具
            tools = await session.list_tools()
            for tool in tools.tools:
                print(f"Tool: {tool.name}, Schema: {tool.inputSchema}")

            # 6. 调用：执行一个工具
            result = await session.call_tool("add", arguments={"a": 3, "b": 5})
            print(f"Result: {result.content}")

            # 7. 读取资源
            content, mime_type = await session.read_resource("greeting://World")
            print(f"Resource: {content}")

if __name__ == "__main__":
    asyncio.run(run())
```

### 2.3 关键设计点

**Client 负责启动 Server 进程。** 注意 `StdioServerParameters(command="mcp", args=["run", "server.py"])` —— Client 能自动启动 Server 子进程，不等用户手动开。

```
Client.start()
  ├── 启动 Server 子进程（mcp run server.py）
  ├── 建立 STDIO 管道
  ├── initialize 握手
  └── 进入交互循环
```

这跟 Inspector 不一样——Inspector 是测试工具，你手动配置 Command。Client 代码里写好就行。

**Client 也能连已经在运行的 Server。** 原文说了："clients can connect to running servers as well"。比如远程场景下 Server 已经跑在另一台机器上，Client 直接连过去就行，不需要启动它。

### 2.4 跟 FastMCP 的关系

注意：`02-client` 用 `from mcp import ClientSession`（底层 SDK），而我们 `07_first_mcp_server.py` 用的是 `from mcp.server.fastmcp import FastMCP`（高层封装）。两者不冲突：

```
FastMCP = 高层封装（我们写 Server 用的）
ClientSession = 底层 SDK（写 Client 用的）
```

FastMCP 内部也依赖底层 SDK，只是帮我们省了 boilerplate。

---

## 3. LLM 驱动的 MCP Client（03-llm-client）

### 3.1 为什么需要 LLM？

纯 MCP Client 的问题是：**你需要在代码里显式指定调哪个工具、传什么参数。** 用户不能说"帮我算 3+5"，你得写 `session.call_tool("add", {"a": 3, "b": 5})`。

加上 LLM 后：用户说自然语言 → LLM 判断 → 自动调工具。这跟我们 Step 1 的 Agent 循环完全一样。

### 3.2 完整流程（4 步）

```
步骤 1: 连接 Server + 发现工具
─────────────────────────────────
session.list_tools()
  → Server 返回: [{name: "add", inputSchema: {a: int, b: int}}, ...]

步骤 2: 转换工具格式（MCP → LLM）
─────────────────────────────────
MCP 格式:  {name: "add", inputSchema: {properties: {a: {type: "integer"}, b: {type: "integer"}}}}
           ↓ 转换函数
LLM 格式:  {type: "function", function: {name: "add", description: "...", parameters: {...}}}

步骤 3: 用户输入 + 调 LLM
─────────────────────────────────
用户: "帮我算 3+5"
  → LLM（带着工具列表）
  → LLM 返回: tool_calls = [{name: "add", arguments: {a: 3, b: 5}}]

步骤 4: 执行工具 + 返回结果
─────────────────────────────────
Client 收到 LLM 的决定 → session.call_tool("add", {a: 3, b: 5})
  → Server 执行 → 返回 8
  → 结果喂回 LLM → LLM: "3+5 等于 8"
```

### 3.3 步骤 2 是核心：工具格式转换

MCP Server 返回的工具格式和 LLM（OpenAI）期望的工具格式不一样，需要一个转换函数：

```python
def convert_to_llm_tool(tool):
    """MCP Tool → OpenAI Function Calling 格式"""
    return {
        "type": "function",
        "function": {
            "name": tool.name,
            "description": tool.description,
            "parameters": {
                "type": "object",
                "properties": tool.inputSchema["properties"],
                "required": tool.inputSchema.get("required", [])
            }
        }
    }

# 使用
functions = [convert_to_llm_tool(tool) for tool in tools.tools]
```

**为什么需要转换？** MCP 的 `inputSchema` 是 JSON Schema 格式，LLM 的 tool definition 也是 JSON Schema 格式——两者其实很像，但字段名和结构略有不同。转换函数就是做这层适配。

核心认识：**这就是 FastMCP 在 Server 端帮我们省掉的活——Client 端目前还是要自己写的。** `@mcp.tool()` 自动生成 JSON Schema 给 Server，但 Client 拿到的 Schema 需要再转成 LLM 认识的格式。

### 3.4 Python 版本的 LLM 调用函数

原文用的是 Azure AI Inference + GitHub Models，但我们用 Anthropic SDK —— 格式是一样的，都是 OpenAI 风格的 tool calling：

```python
def call_llm(prompt, functions):
    """调 LLM，返回需要调用的工具列表"""
    response = client.messages.create(
        model="deepseek-v4-pro",
        system="You are a helpful assistant.",
        messages=[{"role": "user", "content": prompt}],
        tools=functions,          # ← 从 MCP Server 转换来的工具
        max_tokens=1000,
    )

    # 检查 LLM 是否想调工具
    functions_to_call = []
    for block in response.content:
        if block.type == "tool_use":
            functions_to_call.append({
                "name": block.name,
                "args": block.input
            })

    return functions_to_call
```

### 3.5 完整的 LLM Client 主流程

```python
async def run():
    # 1. 连 Server
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            # 2. 发现工具并转换
            tools = await session.list_tools()
            functions = [convert_to_llm_tool(t) for t in tools.tools]

            # 3. 用户自然语言输入
            prompt = "帮我算 3+5"

            # 4. LLM 判断要调什么工具
            functions_to_call = call_llm(prompt, functions)

            # 5. 执行 LLM 选择的工具
            for f in functions_to_call:
                result = await session.call_tool(f["name"], arguments=f["args"])
                print(f"工具 {f['name']} 返回: {result.content}")
```

---

## 4. 跟我们 Step 1 的对比（重要）

### 4.1 流程对比

```
Step 1 Agent 循环                        MCP LLM Client
──────────────────                      ──────────────
1. 手写 tools=[{JSON Schema}]            1. tools = session.list_tools()
                                            → convert_to_llm_tool()
2. LLM 返回 tool_use                     2. LLM 返回 tool_use
3. if name == "execute_sql":            3. session.call_tool(name, args)
      result = execute_sql(sql)            → Server 执行

代码在哪？                               代码在哪？
  工具定义 = Agent 脚本里                    工具定义 = MCP Server 里
  工具执行 = Agent 脚本里                    工具执行 = MCP Server 里
  工具选择 = LLM                            工具选择 = LLM
```

### 4.2 核心区别只有一个

```
Step 1: execute_sql() 定义和执行都在 Agent 进程里
MCP:     execute_sql() 定义和执行都在 Server 进程里
         Agent 只负责：发现 → 转发 LLM 的调用 → 拿结果
```

**LLM 的判断逻辑不变、Agent 循环不变、消息格式不变。变的是工具在哪执行。** 这就是 Step 2 的目标。

---

## 5. 工具格式转换的完整示例

```
MCP Server 返回（list_tools）:
{
  "name": "add",
  "description": "Add two numbers",
  "inputSchema": {
    "type": "object",
    "properties": {
      "a": {"type": "integer"},
      "b": {"type": "integer"}
    },
    "required": ["a", "b"]
  }
}

转换后（LLM tool format）:
{
  "type": "function",
  "function": {
    "name": "add",
    "description": "Add two numbers",
    "parameters": {
      "type": "object",
      "properties": {
        "a": {"type": "integer"},
        "b": {"type": "integer"}
      },
      "required": ["a", "b"]
    }
  }
}
```

本质上就是包了一层 `{type: "function", function: {...}}`，内容几乎一样。

---

## 6. 原文中用到但我们会替换的技术

原文代码用的 GitHub Models（Azure AI Inference），需要 `GITHUB_TOKEN`：

```python
# 原文方式
from azure.ai.inference import ChatCompletionsClient
client = ChatCompletionsClient(endpoint="https://models.inference.ai.azure.com", ...)
```

**我们会替换成 Anthropic SDK（deepseek 兼容层）**——逻辑完全一样，只是 SDK 不同。Tool calling 的交互模式是通用的。

---

## 7. 小结：三个角色的最终分工

```
┌─ LLM ─────────────────────┐
│ 用户说 "帮我算 3+5"        │
│ LLM 判断: 调 add(3, 5)     │  ← 做判断
└──────────┬────────────────┘
           │ tool_use {name: "add", input: {a:3, b:5}}
           ▼
┌─ MCP Client（在 Agent 里）─┐
│ session.call_tool(...)    │  ← 转发（不改判断、不加逻辑）
└──────────┬────────────────┘
           │ JSON-RPC via STDIO
           ▼
┌─ MCP Server（独立进程）────┐
│ def add(a, b): return a+b │  ← 执行
└───────────────────────────┘
```

- **LLM**：理解自然语言，决定调哪个工具、传什么参数
- **MCP Client**：收 LLM 的决定，转发为 JSON-RPC 调用，拿结果
- **MCP Server**：执行工具逻辑，返回结果

三层各干各的，没有越界。这就是 MCP 设计的精髓。

---

## 8. 实战中补充的关键认知

### 8.1 07-08-09 三兄弟的关系

```
07 = MCP Server              工具定义在这里，独立进程
08 = MCP Client              连 Server，手动指定调哪个工具
09 = LLM + MCP Client        连 Server，LLM 自动判断调哪个工具

运行 08 或 09 时，不需要先手动启动 07——
Client 通过 StdioServerParameters 自动拉起 Server 子进程
Client 退出时，Server 也跟着停（父子进程关系）
```

### 8.2 messages 如何积累（Agent 循环的发动机）

每次调 LLM 都必须把**完整历史**传回去，LLM 没有记忆：

```
第 1 轮: messages = [user: "帮我算 3+5 再加 10"]
         → LLM: tool_use add(3,5)

第 2 轮: messages = [user: "...", assistant: tool_use add(3,5), user.tool_result: 8]
         → LLM: tool_use add(8,10)

第 3 轮: messages = [user: "...", ..., user.tool_result: 18]
         → LLM: "结果是 18" (end_turn)
```

每一步 `messages.append()` 不是替换，是追加。LLM 看到完整历史才能做多步推理。

### 8.3 messages 过大的问题

如果工具返回大量数据，messages 会爆炸。应对方案优先级：
1. **截断结果**（最实用）— `result[:500]`
2. **保留最近 N 轮** — `messages = messages[-10:]`
3. **LLM 总结历史** — 压缩旧消息为摘要
4. **Prompt Caching** — SDK 层面优化

### 8.4 async/await 最简理解

MCP Client 必须用 async，但浅层使用只需要知道：
- `await` = 等结果（等 Server 返回）
- 函数里有 `await` → 前面加 `async`
- `asyncio.run()` 启动一切
逻辑跟同步代码一样，只是多了这两个关键字。

---

## 9. 一句话总结两个模块

- **02-client**：学会了用代码连 Server、发现工具、调用工具（之前只能用 Inspector 手动点）
- **03-llm-client**：加 LLM 后用户说人话就行了，LLM 自动判断调什么——这就是 Agent
