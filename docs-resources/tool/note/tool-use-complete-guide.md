# Tool Use 完整笔记

> 基于 Anthropic 官方文档整理，筛选与 DB-Agent 项目最相关的内容。

---

## 一、Tool 是什么

Tool 是你和 Claude 之间的**合同**。你告诉 Claude "我能做这些事"（定义 tool），Claude 决定什么时候调用、怎么填参数，**你的代码负责真正执行**，把结果塞回去。

```
你定义 Tool（菜单）→ Claude 点菜（tool_use）→ 你执行（run function）→ Claude 看结果再回复
```

**核心认知**：Claude 只负责"决策"，不负责"执行"。执行永远是你的事。

---

## 二、Tool 的分类（只看你需要的）

| 类型 | 谁执行 | 例子 | 你需要吗 |
|------|--------|------|----------|
| **用户自定义工具** | 你的代码 | `execute_sql` | ✅ 就是你的项目 |
| Anthropic 内置客户端工具 | 你的代码 | `bash`、`text_editor` | ❌ 跟你的项目无关 |
| 服务端工具 | Anthropic 服务器 | `web_search`、`code_execution` | ❌ 跟你的项目无关 |

你的 DB-Agent 只需要**用户自定义工具**。

---

## 三、定义 Tool（核心技能）

### 3.1 最简结构

```python
tool = {
    "name": "execute_sql",          # 工具名，只能 a-z A-Z 0-9 _ -
    "description": "...",            # 详细描述，最重要的字段！
    "input_schema": {                # 参数 JSON Schema
        "type": "object",
        "properties": { ... },
        "required": [ ... ]
    }
}
```

### 3.2 description 怎么写

**description 是决定 Claude 会不会正确调用的最关键因素。**

差的 description：
```json
"description": "执行 SQL"
```

好的 description（3-4 句）：
```json
"description": "在 rookieDB 数据库上执行一条 SQL 语句。支持 SELECT、INSERT、UPDATE、DELETE。查询结果以表格形式返回。当用户需要查询、插入、更新或删除数据库中的数据时使用此工具。注意：此工具不返回数据库 schema 信息，如需了解表结构请先执行 DESCRIBE 语句。"
```

**description 必须覆盖**：
1. 工具做什么
2. 什么时候用（什么时候不用）
3. 每个参数的含义
4. 任何限制或注意事项

### 3.3 input_schema 怎么写

```python
{
    "type": "object",
    "properties": {
        "参数名": {
            "type": "类型",          # string / integer / number / boolean / array / object
            "description": "参数说明",
            "enum": ["选项1", "选项2"]  # 可选，限定值范围
        }
    },
    "required": ["必填参数1", "必填参数2"]  # 必填参数列表
}
```

### 3.4 你的 execute_sql 工具（优化版）

```python
execute_sql_tool = {
    "name": "execute_sql",
    "description": (
        "在 rookieDB 数据库上执行一条 SQL 语句。"
        "支持 SELECT、INSERT、UPDATE、DELETE 操作。"
        "查询结果以 JSON 数组形式返回，每条记录是一个对象。"
        "当用户需要查询、插入、更新或删除数据库中的数据时使用此工具。"
        "注意：此工具不支持 DDL（CREATE/ALTER/DROP TABLE），"
        "如需了解表结构请使用 'SELECT * FROM information_schema.tables'。"
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "sql": {
                "type": "string",
                "description": "要执行的 SQL 语句。仅支持 DML 操作。例如：SELECT * FROM Students WHERE age > 20"
            }
        },
        "required": ["sql"]
    }
}
```

### 3.5 可选：input_examples

对于复杂参数，可以给 Claude 看几个例子：

```python
"input_examples": [
    {"sql": "SELECT * FROM Students"},
    {"sql": "INSERT INTO Students VALUES (4, '赵六', 23, '人工智能')"},
    {"sql": "SELECT name, age FROM Students WHERE major = '计算机科学'"}
]
```

---

## 四、处理 Tool 调用（核心技能）

### 4.1 Claude 返回什么

当 Claude 决定调用工具时，`stop_reason` = `"tool_use"`，content 里包含：

```python
# response.content 是一个列表，可能同时包含 text 和 tool_use
for block in response.content:
    if block.type == "text":
        print(block.text)       # Claude 的文字解释
    elif block.type == "tool_use":
        print(block.id)         # "toolu_01A09q90qw..."
        print(block.name)       # "execute_sql"
        print(block.input)      # {"sql": "SELECT * FROM Students"}
```

### 4.2 你怎么把结果塞回去

三步走：

**Step 1** — 把 Claude 的回复拼进消息历史：

```python
messages.append({
    "role": "assistant",
    "content": response.content  # 直接原样塞
})
```

**Step 2** — 执行工具，构造 tool_result：

```python
tool_results = []
for block in response.content:
    if block.type == "tool_use":
        # 执行工具
        result = your_function(block.input)
        # 构造 tool_result
        tool_results.append({
            "type": "tool_result",
            "tool_use_id": block.id,    # ← 必须对应！告诉 Claude 这是哪个调用的结果
            "content": json.dumps(result)  # 结果转成字符串
        })
```

**Step 3** — 把结果作为 user 消息塞回去：

```python
messages.append({
    "role": "user",
    "content": tool_results  # 所有 tool_result 放一条消息里
})
```

### 4.3 重要规则

- **tool_result 必须在 user 消息的 content 数组中最前面**，text 放后面
- **每个 tool_use 必须有一个对应的 tool_result**，id 必须匹配
- **一次 assistant 的多个 tool_use → 一次 user 消息包含所有 tool_result**（不要拆成多条）

❌ 错误：
```json
{"role": "user", "content": [
    {"type": "text", "text": "这是结果"},
    {"type": "tool_result", "tool_use_id": "xxx", "content": "..."}  // text 不能放前面
]}
```

✅ 正确：
```json
{"role": "user", "content": [
    {"type": "tool_result", "tool_use_id": "xxx", "content": "..."},  // tool_result 在前
    {"type": "text", "text": "接下来做什么？"}  // text 在后
]}
```

---

## 五、Agent 循环（你已经会了）

```python
while True:
    response = client.messages.create(
        model="deepseek-v4-pro",
        max_tokens=500,
        system="你是一个数据库助手...",
        messages=messages,       # ← 完整历史
        tools=[execute_sql_tool] # ← 每次都要传
    )

    if response.stop_reason != "tool_use":
        break  # 对话结束

    # 1. 保存 assistant 回复
    messages.append({"role": "assistant", "content": response.content})

    # 2. 执行工具
    tool_results = []
    for block in response.content:
        if block.type == "tool_use":
            result = do_work(block.name, block.input)
            tool_results.append({
                "type": "tool_result",
                "tool_use_id": block.id,
                "content": result
            })

    # 3. 塞回结果
    messages.append({"role": "user", "content": tool_results})
```

**三个 stop_reason 关键值**：
| stop_reason | 含义 | 你做什么 |
|-------------|------|---------|
| `tool_use` | Claude 要调工具 | 执行 → 塞结果 → 继续循环 |
| `end_turn` | Claude 说完了 | break，对话结束 |
| `max_tokens` | token 不够了 | 可以加大 max_tokens 重试 |

---

## 六、控制 Claude 何时调工具（tool_choice）

`tool_choice` 参数控制 Claude 是不是一定要调工具：

| 值 | 效果 | 什么时候用 |
|----|------|-----------|
| `auto`（默认） | Claude 自己判断 | 99% 的情况，你不需要改 |
| `any` | 必须调一个，但不指定哪个 | 强制 Claude 用工具 |
| `tool` | 强制调某个指定工具 | `{"type": "tool", "name": "execute_sql"}` |
| `none` | 不允许调工具 | 纯聊天，不用工具 |

**一般不需要改，用 `auto` 就够了。** 如果 Claude 不用工具但你觉得该用，在 system prompt 里加一句：

```
"在回答用户问题之前，先使用工具查询相关信息。"
```

---

## 七、错误处理

### 7.1 工具执行失败

用 `is_error: true` 标记：

```python
try:
    result = execute_sql(sql)
except Exception as e:
    tool_results.append({
        "type": "tool_result",
        "tool_use_id": block.id,
        "content": f"Error: {str(e)}",
        "is_error": True  # ← 告诉 Claude 这是个错误
    })
```

Claude 看到错误会自动尝试修正（比如换个 SQL）或向用户解释。

**错误信息要写清楚**：别说 `"执行失败"`，说 `"ConnectionError: 无法连接 rookieDB (端口 18600)，请确认 Server 已启动"`。

### 7.2 Claude 传的参数不对

如果 Claude 漏了必填参数或传了不存在的参数，同样用 `is_error: true` 返回错误信息。Claude 会重试 2-3 次修正参数。

如果想彻底避免参数错误 → 看第八章 Strict Tool Use。

---

## 八、Strict Tool Use（参数校验）

在你的 tool 定义里加 `strict: true`，Claude 保证返回的参数**一定符合你的 schema**：

```python
execute_sql_tool = {
    "name": "execute_sql",
    "strict": True,  # ← 开启严格模式
    "description": "...",
    "input_schema": {
        "type": "object",
        "properties": { ... },
        "required": ["sql"],
        "additionalProperties": False  # 必须加这个
    }
}
```

**好处**：Claude 不会漏参数、不会发明不存在参数、类型一定对。
**代价**：input_schema 必须写得更仔细。

适合你的项目吗？**适合**。`execute_sql` 只有一个 `sql` 参数，schema 很简单，开 strict 没坏处。

---

## 九、Parallel Tool Use（并行调用）

当用户一句话需要多个工具时（比如"查 Students 表和 Courses 表"），Claude 可以一次返回多个 `tool_use`：

```python
# Claude 一次返回了 2 个 tool_use
# tool_use_1: execute_sql("SELECT * FROM Students")
# tool_use_2: execute_sql("SELECT * FROM Courses")

# 所有 tool_result 必须放在同一条 user 消息里：
messages.append({
    "role": "user",
    "content": [
        {"type": "tool_result", "tool_use_id": id1, "content": result1},
        {"type": "tool_result", "tool_use_id": id2, "content": result2},
    ]
})
```

**并行调用的工具之间是独立的** — 你可以用并发执行（`asyncio.gather`）或顺序执行，Claude 不关心。但如果 tool_2 依赖 tool_1 的结果，tool_2 会失败，用 `is_error: true` 返回，Claude 下次会单独调。

禁用并行：`disable_parallel_tool_use=True`

---

## 十、不相关的内容（跳过）

以下是官方文档有的但你的项目不需要的：

| 文档 | 为什么不需要 |
|------|-------------|
| Web Search / Web Fetch | 你的 Agent 操作本地数据库，不上网 |
| Code Execution Tool | 你的 Agent 不需要在沙箱里跑 Python |
| Bash Tool / Text Editor Tool | Anthropic 给代码 Agent 设计的，你的项目不是 |
| Computer Use Tool | 控制浏览器，跟你的项目无关 |
| Memory Tool | 给 Agent 记笔记用，你的历史管理就够了 |
| Tool Search | 你的工具只有 1 个，不需要搜索 |
| Server Tools / pause_turn | 服务端工具自动执行，你没有服务端工具 |
| Prompt Caching | 优化性能用，MVP 阶段不需要 |

---

## 十一、你的最佳实践 Checklist

定义 Tool 时：
- [ ] description 写 3-4 句：做什么、何时用、参数说明、限制
- [ ] input_schema 里每个参数都有 type + description
- [ ] required 数组列出所有必填参数
- [ ] 考虑加 `strict: true` + `additionalProperties: false`
- [ ] 复杂参数考虑加 `input_examples`

处理 Tool 调用时：
- [ ] 先检查 `stop_reason`，`tool_use` 才执行工具
- [ ] 所有 `tool_use` 的 id 都要在 `tool_result` 里对应
- [ ] `tool_result` 放 user 消息 content 最前面
- [ ] 多个 `tool_result` 放同一条 user 消息里
- [ ] 工具执行出错用 `is_error: true` + 清晰的错误描述

Agent 循环：
- [ ] while 循环，`stop_reason != "tool_use"` 时退出
- [ ] 每次 `messages.create()` 都带上完整的 tools 列表和 message 历史
- [ ] assistant 消息 → user(tool_result) 消息 交替拼接
