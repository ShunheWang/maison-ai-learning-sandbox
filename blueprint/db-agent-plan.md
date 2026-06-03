# DB-Agent 项目方案

## 目标

做一个**死锁检测 Agent 系统**：
- 多个 Agent 并发操作 rookieDB
- Agent 自动检测死锁
- 构建 wait-for graph
- 策略决策 kill 哪个事务

## 架构

```
Agent (Python) ──TCP socket :18600──→ rookieDB Server (Java)
  │                                     ├─ LockManager（已实现）
  ├─ Anthropic SDK                      ├─ Transaction（已实现）
  ├─ Tool: execute_sql(sql)             └─ 死锁检测（待做）
  ├─ Tool Calling Loop
  └─ 后续：Deadlock Detector
```

Agent 循环模式：
1. 用户提问 → `client.messages.create(model, system, messages, tools)`
2. Claude 返回 `stop_reason="tool_use"` → 执行工具 → 把 `tool_result` 塞回 `messages` → 循环
3. Claude 返回 `stop_reason="end_turn"` → 输出最终回复，结束

**rookieDB 位置**：`/Users/shunhewang/melbourne/cs186/berkeley-sp26-rookiedb`
**启动**：`java -cp target/classes edu.berkeley.cs186.database.cli.Server`（端口 18600）

## 四步路线

```
Step 1: 单 Agent + Tool Calling     ← ✅ 完成
        → Anthropic SDK, Tool Calling Loop, System Prompt, 错误处理

Step 2: MCP                        ← 学习中
        → MCP 协议, Server/Client, Transport

Step 3: Multi-Agent
        → 多 Agent 协作, 通信模式, Orchestration

Step 4: RAG
        → Embedding, Vector DB, 检索管道
```

## 技术选型

| 决策 | 选择 | 原因 |
|------|------|------|
| Agent 语言 | Python | AI 生态最好 |
| LLM | Claude (deepseek 兼容) | Anthropic SDK |
| 框架 | 原生 Anthropic SDK | 先学原理，不碰 LangChain |
| 数据库 | rookieDB（Java） | CS186 项目 |
| 通信 | Python socket → rookieDB | 已有 client.py |

## 环境配置

```bash
ANTHROPIC_API_KEY=sk-...     # DeepSeek 的 key
ANTHROPIC_BASE_URL=https://api.deepseek.com/anthropic
```

两个来源：终端靠 `~/.zshrc`，IDE 直接运行时靠项目根目录的 `.env` 文件。

## 运行

```bash
# 直接跑（不依赖 rookieDB）
python3 step1-agent-toolcalling/01_hello_claude.py
python3 step1-agent-toolcalling/02_define_tool.py
python3 step1-agent-toolcalling/03_agent_loop.py

# 后续接 rookieDB 时需要先启动 Server
cd /Users/shunhewang/melbourne/cs186/berkeley-sp26-rookiedb
java -cp target/classes edu.berkeley.cs186.database.cli.Server &
```

## MVP 范围

**做**：1 个 Agent，1 个 Tool（execute_sql），自然语言查数据库

**不做**：多 Agent、死锁检测、Web 界面、LangChain

---

## 学习进度

### Step 1：单 Agent + Tool Calling ✅

- [x] **01_hello_claude.py** — Claude API 基础调用
- [x] **02_define_tool.py** — Tool 定义（JSON Schema）
- [x] **03_agent_loop.py** — Tool Calling 循环（mock 数据）
- [x] **rookieDB 代码评估** — `blueprint/rookiedb-review.md`
- [x] **04_connect_rookiedb.py** — 接上真实 rookieDB，socket 通信
- [x] **05_system_prompt.py** — System Prompt 设计（5 个对比实验）
- [x] **06_error_handling.py** — 错误处理：重试、重连、参数校验

### Step 2：MCP ← 当前

- [ ] 学习 MCP 协议规范
- [ ] 实现 MCP Server（封装 execute_sql）
- [ ] 实现 MCP Client（Agent 端发现和调用）

### Step 3：Multi-Agent

- [ ] 多 Agent 并发操作 rookieDB
- [ ] 死锁检测算法（wait-for graph + BFS/DFS 找环）
- [ ] Victim selection 策略

### Step 4：RAG

- [ ] Embedding + Vector DB
- [ ] 接入 schema 文档和知识库

---

## 学习日志

### 2026-06-01 晚 — 01：Hello World

**产出**：`step1-agent-toolcalling/01_hello_claude.py`

**收获**：
- Anthropic SDK 初始化：`anthropic.Anthropic()`，API key 从环境变量读
- `messages.create()` 四个核心参数：`model`、`max_tokens`、`system`、`messages`
- response.content 是一个列表，遍历拿 `block.text`
- `response.usage` 能看到 input/output token 消耗
- 三种角色：system（设规矩）、user（提问）、assistant（回复）

---

### 2026-06-02 上午 — 02：Tool 定义

**产出**：`step1-agent-toolcalling/02_define_tool.py`

**收获**：
- Tool 就是给 LLM 看的"函数说明书"，JSON 格式
- 三个核心字段：`name`（叫啥）、`description`（干什么）、`input_schema`（参数格式）
- `description` 写得好不好，直接决定 Claude 会不会正确调用
- 通过 `tools=[...]` 传给 `messages.create()`，每次调用都要传
- Claude 根据 description 自己判断要不要用工具、用什么工具
- 判断依据看 `stop_reason`：`end_turn` = 不需要工具，`tool_use` = 要调工具
- tool_use block 包含 `id`（唯一标识）、`name`（工具名）、`input`（参数）
- **Claude 不会执行工具**，它只会说"我想调用 X，参数是 Y"。执行是你的事

---

### 2026-06-02 下午 — 03：Tool Calling 循环（Agent 核心）

**产出**：`step1-agent-toolcalling/03_agent_loop.py`（mock 数据）

**收获**：
- Agent 循环 = while 循环，直到 Claude 不再要调工具
- 流程：用户提问 → 调 Claude → Claude 返回 tool_use → 执行工具 → 塞 tool_result → 再调 Claude → 循环
- 消息数组（messages）要不断积累，不能丢历史
- assistant 消息的 content 是 content blocks 列表（text + tool_use）
- tool_result 必须带 `tool_use_id`，跟原始 tool_use 的 id 对应
- 最终 Claude 看了结果，用自然语言回复用户

**关键代码模式**：
```python
while True:
    response = client.messages.create(messages=messages, tools=[...])
    if response.stop_reason != "tool_use":
        break  # 对话结束
    # 1. 把 assistant 回复拼进历史
    # 2. 执行每个 tool_use
    # 3. 把 tool_result 塞回历史
    # 4. 继续循环
```

**踩坑**：
- IDE 直接跑 Python 不会加载 ~/.zshrc 的环境变量，需要 .env 文件
- API key 格式要跟 base URL 匹配（deepseek 的 key 跟 anthropic 原生 key 不同）

---

### 2026-06-02 下午 — Tool Use 专题

**产出**：`docs-resources/tool/note/tool-use-complete-guide.md`（笔记）+ `docs-resources/tool/note/demo_improved_tool.py`（demo）

**收获**：

1. **Tool 定义最佳实践**：
   - description 写 3-4 句：做什么 + 何时用 + 参数说明 + 限制
   - 加 `strict: true` + `additionalProperties: false` 防止参数错误
   - 复杂参数加 `input_examples` 给 Claude 看例子

2. **tool_result 格式规则**：
   - tool_result 必须在 user 消息 content 最前面
   - 多个 tool_result 放同一条 user 消息里
   - tool_use_id 必须对应

3. **错误处理**：
   - `is_error: true` 标记工具失败
   - 错误信息要写清楚原因 + 建议
   - Claude 看到 is_error 会自动重试 2-3 次修正

4. **tool_choice 控制**：auto（默认）够用了，一般不需要改

5. **不相关的内容**：server tools、bash/text_editor/computer use、web search/fetch、prompt caching — DB-Agent 项目不需要

---

### 2026-06-02 晚 — 04：接上 rookieDB

**产出**：`step1-agent-toolcalling/04_connect_rookiedb.py`

**收获**：
- Python socket 连 Java 进程：纯文本协议，send SQL + recv until prompt
- Agent 循环逻辑完全不用改，只替换 execute_sql 实现
- 连接生命周期：单连接复用，try/finally 保证关闭
- `make_execute_sql(db)` 闭包工厂替代全局变量
- rookieDB parser 需要分号 `;` 结束语句，不然死等
- rookieDB 不支持中文字符
- system prompt 中告知表结构很重要，避免 Claude 盲目乱试

**验证结果**：8 步 CRUD 全部通过（Read × 4, Create × 1, Update × 1, Delete × 1, 每步带验证）

**修正**：Tool description 去掉"不支持 DDL"的限制，实际 rookieDB 支持 CREATE/DROP TABLE/INDEX

---

### 2026-06-03 — rookieDB 代码质量评估

**产出**：`blueprint/rookiedb-review.md`

**收获**：
- 工程能力中上：包结构干净，线程安全处理好，但 Database.java 1325 行太臃肿
- 抽象能力中上：Transaction/TransactionContext 分层合理，但 TransactionContext 是上帝对象（30+ 方法）
- 设计模式：Strategy（EvictionPolicy）、Null Object（DummyLockManager）、Visitor（SQL AST）、Template Method（Transaction）都用得到位
- 源码 ~30,000 行（手写 ~24,000），加测试 ~45,000 行
- **值得系统读**，优先级：concurrency > memory > recovery > query/join > table > index
- 低级编码技巧：~ 做空闲链表、virtual page number 编码、LSN 编码、Bits 位图工具类

---

### 2026-06-03 — 05：System Prompt 设计（对比实验）

**产出**：`step1-agent-toolcalling/05_system_prompt.py`，5 个实验 + 2 个追加测试

**收获**：
- System prompt 就是给 Agent 的"人设 + 规则 + 知识"，不用改代码就能改变行为
- 角色设定：从"数据库助手"改成"rookieDB 内核开发者"，Claude 的回答从简洁查询变成了解释火山模型和 B+ 树
- 护栏：加一句"只允许 SELECT"，Claude 拒绝执行 UPDATE，还主动解释原因
- 知识缺失：不告诉表结构，Claude 多绕了 3 步（SHOW TABLES → GPA → gpa）才找到正确查询
- 反幻觉：加"查不到就老实说"，查不存在的 Teachers 表时直接说"没这表"并列出实际表名

**关键发现**：同一个问题、同一个 Agent 循环、同一个数据库，只改 system prompt，行为差异巨大。System prompt 不需要"最优"，需要根据场景设计——读场景给表结构，只读场景加护栏，探索场景保留灵活性。

---

### 2026-06-03 — 06：错误处理

**产出**：`step1-agent-toolcalling/06_error_handling.py`，3 个错误场景测试

**在 04 基础上加了 4 层防护，不改核心循环逻辑**：

**防护 1：API 调用重试（指数退避）**
```python
def call_claude_with_retry(model, max_tokens, system, messages, tools):
    for attempt in range(MAX_RETRIES):      # 最多 3 次
        try:
            return client.messages.create(...)
        except Exception as e:
            if attempt == MAX_RETRIES - 1:
                raise                         # 3 次都失败，不吞异常
            wait = 2 ** attempt               # 1s, 2s, 4s
            time.sleep(wait)
```
指数退避比固定间隔好：服务端过载时固定间隔可能再次打爆，指数退避给服务端恢复时间。

**防护 2：参数校验**
```python
def validate_tool_input(tool_use):
    sql = tool_use.input.get("sql")
    if not sql:                                  # None 或空字符串
        return False, "参数错误: sql 不能为空"
    if not isinstance(sql, str):                 # 类型不对
        return False, f"参数类型错误: ..."
    if len(sql.strip()) == 0:                    # 空白字符串
        return False, "参数错误: sql 是空白字符串"
    return True, None
```
校验失败时不执行工具，直接返回 is_error，让 Claude 自己修正。

**防护 3：连接断开自动重连**
```python
def execute(self, sql):
    try:
        self.sock.send(...)
        return self._recv_until_prompt().strip()
    except (socket.timeout, ConnectionError, OSError) as e:
        self._reconnect()           # 关旧连接 → 等 0.5s → 建新连接
        self.sock.send(...)         # 重发 SQL
        return self._recv_until_prompt().strip()
```

**防护 4：工具执行 try-catch** — 异常不往外抛，变成带 is_error 标记的 tool_result 返回给 Claude。

**验证结果**：
- SQL 语法错误恢复：Claude 要查 GPA Top 3，`ORDER BY gpa DESC` 不支持 → `ORDER BY -gpa` → 子查询 `MAX(gpa)` → `OFFSET 197` → 最后全表排序手动找前 3，**6 次工具调用最终成功**
- 正常查询：参数校验不误伤
- 不存在的表：Claude 确认后列出实际 3 张表，不编造

**关键认知**：错误处理的目标不是"不犯错"，而是**让 Agent 能自己从错误中恢复**。把错误信息喂回给 LLM，它自己会分析原因并修正策略。这就是为什么 is_error 标记这么重要：它让 Claude 知道"你上次尝试失败了，原因是什么，换个方式试试"。