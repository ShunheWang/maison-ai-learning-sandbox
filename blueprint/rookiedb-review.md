# rookieDB 代码阅读评估报告

**阅读时间**：2026-06-02
**项目位置**：`/Users/shunhewang/melbourne/cs186/berkeley-sp26-rookiedb`

---

## 1. 总体结论

**rookieDB 完全满足 DB-Agent 项目的需求，甚至超出了 MVP 范围。**

- 数据库功能完备，demo 数据就绪
- 锁管理器完整实现了多粒度锁，但**没有死锁检测** — 这正是我们要做的
- Socket 通信协议简单清晰，Python 对接无障碍
- 195 个 Java 源文件，但对外接口清晰，只需关注少数几个核心类

---

## 2. 通信协议（Socket 层）

### 2.1 Server 启动

```bash
java -cp target/classes edu.berkeley.cs186.database.cli.Server
# 监听 localhost:18600
```

每个连接创建独立线程，复用同一个 Database 实例（所有 session 共享数据）。

### 2.2 协议格式

纯文本，跟 MySQL CLI 一致：

```
发送: SELECT * FROM Students WHERE age > 20;\n
接收: [查询结果文本]
      => 
```

- 每条 SQL 以换行结尾（分号可有可无，跟 mysql 一样）
- 响应以 `=> ` 提示符结束
- 退出：发送 `exit\n`
- 欢迎信息在连接建立时发送，需跳过

### 2.3 Python 对接方式

已有关方 `client.py` 作为参考实现。核心逻辑：
```python
sock.connect(("localhost", 18600))
sock.send((sql + "\n").encode("utf-8"))
response = recv_until_prompt()  # 读到 "=> " 为止
```

跟 `04_agent_with_db.py` 里的 `RookieDBConnection` 逻辑完全一致。

---

## 3. 数据库能力

### 3.1 支持的操作

| 操作 | 支持 | 备注 |
|------|------|------|
| CREATE TABLE | ✓ | 完整 schema 定义 |
| DROP TABLE | ✓ | |
| CREATE INDEX | ✓ | B+ 树索引 |
| DROP INDEX | ✓ | |
| SELECT | ✓ | 支持 WHERE、JOIN、GROUP BY、ORDER BY、LIMIT |
| INSERT | ✓ | 单行插入 |
| UPDATE | ✓ | 支持 WHERE 条件 |
| DELETE | ✓ | 支持 WHERE 条件 |
| BEGIN/COMMIT/ROLLBACK | ✓ | 事务支持 |
| SAVEPOINT | ✓ | 需 recovery 模块 |

### 3.2 连接算法

5 种连接算法：SNLJ（简单嵌套循环）、PNLJ（页嵌套循环）、BNLJ（块嵌套循环）、SMJ（排序归并）、GHJ（Grace Hash）。

### 3.3 Demo 数据

Server 启动时自动加载 3 张表：

| 表名 | 行数 | 字段 |
|------|------|------|
| Students | 200 | sid (int), name (string), major (string), gpa (float) |
| Courses | 15 | cid (int), name (string), department (string) |
| Enrollments | 1000 | sid (int), cid (int) — 多对多关联表 |

数据量足够做测试，schema 简单但有代表性（有 JOIN 场景）。

---

## 4. 并发控制（重点）

### 4.1 锁类型

完整多粒度锁（Project 4 已完成）：

| 锁类型 | 含义 | 兼容自身 |
|--------|------|----------|
| NL | 无锁 | ✓ |
| IS | 意向共享 | ✓ |
| IX | 意向排他 | ✓ |
| S | 共享 | ✓ |
| SIX | 共享意向排他 | ✗ |
| X | 排他 | ✗ |

锁层级：`database → table → page`（通过 `LockContext` 的树结构维护）

### 4.2 锁管理器核心机制

**LockManager**（`concurrency/LockManager.java`）：

- `acquire(transaction, resource, lockType)` — 获取锁，不兼容时阻塞排队
- `acquireAndRelease(...)` — 原子性获取新锁并释放旧锁（锁升级/降级用）
- `release(transaction, resource)` — 释放锁，自动处理等待队列
- `promote(transaction, resource, newLockType)` — 锁升级

**等待队列机制**：
- 每个资源有独立队列（`Deque<LockRequest>`）
- 不兼容时事务被 block，请求入队
- 释放锁时自动 `processQueue()`：从队头开始，逐个尝试授予，直到遇到不兼容的请求
- `acquire` 入队尾，`promote` 入队头（避免饥饿）

**锁升级（Escalation）**：
- `LockContext.escalate()` — 将子孙锁合并为父级的一个粗粒度锁
- 例如：IX(table) + S(page1) + X(page2) → X(table)

### 4.3 关键发现：没有死锁检测

通读 `LockManager.java`（457 行），确认：
- ❌ **没有 wait-for graph 构建**
- ❌ **没有死锁检测逻辑**
- ❌ **没有超时机制**
- ❌ **没有死锁解决策略（victim selection）**
- ❌ **没有 `getWaitForGraph()` 或类似接口**

当前行为：事务在请求不兼容锁时无限期阻塞，直到持有锁的事务释放。如果两个事务互相等待（T1 等 T2，T2 等 T1），就会**死锁**。

这正是我们要做的 — 在 LockManager 之上构建死锁检测 Agent。

### 4.4 LockManager 暴露的查询接口

```java
// 获取某个资源上所有持有的锁（按获取时间排序）
List<Lock> getLocks(ResourceName name);

// 获取某个事务持有的所有锁（按获取时间排序）
List<Lock> getLocks(TransactionContext transaction);

// 获取某个事务在某个资源上的锁类型
LockType getLockType(TransactionContext transaction, ResourceName name);
```

通过这些接口 + 等待队列信息（`ResourceEntry.waitingQueue`），我们可以构建 wait-for graph。但 `waitingQueue` 目前是 `private`，如果要外部访问需要：
- 方案 A：给 LockManager 加一个 `getWaitingInfo()` 方法
- 方案 B：通过 CLI 的 `\locks` 元命令获取（目前只打印当前事务的锁）
- 方案 C：在 Server 端新增一个专门的调试端点

### 4.5 CLI 元命令

- `\d` — 列出所有表
- `\d tableName` — 查看表 schema
- `\di` — 列出所有索引
- `\locks` — 查看当前事务的锁（需要在一个事务中）

---

## 5. DB-Agent 可行性评估

### 5.1 单元 4（单 Agent + rookieDB）✅ 完全可行

- Socket 通信协议简单，Python 端只需 send/receive
- SQL 解析由 rookieDB 端完成，Agent 只需生成 SQL 文本
- `03_agent_loop.py` 的架构可以直接复用，只需把 mock `execute_sql` 换成 socket 调用

### 5.2 Step 3（多 Agent + 死锁检测）✅ 架构上可行

- rookieDB Server 支持多连接并发（每个连接独立线程）
- LockManager 已有完整的锁和等待队列信息
- **需要做的工作**：
  1. 在 rookieDB 端暴露死锁检测所需的内部状态（锁表 + 等待队列）
  2. Python Agent 端构建 wait-for graph
  3. 实现死锁检测算法（BFS/DFS 找环）
  4. 实现 victim selection 策略（选最年轻的事务 kill）

### 5.3 暴露锁状态的方案

| 方案 | 优点 | 缺点 |
|------|------|------|
| A. 给 LockManager 加 getter | 最直接 | 需要改 rookieDB 代码 |
| B. 通过 socket 发元命令 | 不改代码 | 现有 `\locks` 只能看自己的锁 |
| C. 新增 debug HTTP 端点 | 分离关注点 | 需要加依赖 |

**建议方案 A**：给 `LockManager` 加一个 `getWaitForGraph()` 方法，返回所有锁和等待关系，通过 socket 用特殊命令（如 `__debug_locks__`）查询。

---

## 6. 与笔记中规划的对照

| 笔记中的假设 | 实际验证 |
|-------------|---------|
| "通过 socket 连 rookieDB" | ✅ socket 端口 18600，纯文本协议 |
| "LockManager 已实现" | ✅ 完整的多粒度锁 + 队列管理 |
| "死锁检测待做" | ✅ LockManager 完全没有死锁检测代码 |
| "支持 SELECT/INSERT/UPDATE/DELETE" | ✅ 全支持，还支持 JOIN/GROUP BY/ORDER BY |
| "不支持 DDL" | ❌ 实际支持 CREATE TABLE/DROP TABLE/CREATE INDEX |

**修正**：之前 04 代码里 tool description 写的"不支持 CREATE/ALTER/DROP TABLE"是错误的，rookieDB 完全支持 DDL。

---

## 7. Python 集成实战踩坑（单元 4 验证记录）

以下是在 `04_connect_rookiedb.py` 开发过程中踩过的坑，后续项目直接参考。

### 7.1 SQL 语句必须以分号结尾

**现象**：socket 发送 SQL 后 `recv` 超时，服务端不返回 `=> ` 提示符。

**原因**：rookieDB parser 以分号 `;` 或 EOF 作为语句结束标志。如果不加分号，parser 认为语句未结束，等待更多输入（显示 `->`），而客户端在等 `=> `，双方互相死等。

**解决**：发送前自动追加分号：

```python
def execute(self, sql: str) -> str:
    if not sql.strip().endswith(";"):
        sql += ";"
    self.sock.send((sql + "\n").encode("utf-8"))
    ...
```

### 7.2 不支持 SHOW / information_schema / _metadata 查询

**现象**：`SHOW TABLES`、`SELECT * FROM information_schema.tables`、`SELECT * FROM _metadata.tables` 全部失败。

**原因**：
- `SHOW` 不是 rookieDB 支持的 SQL 关键字
- `information_schema` 不存在（这是 MySQL 的概念）
- `_metadata.tables` 表名带 `.`，parser 把这个 `.` 当成 SQL 语法元素报错

**解决**：system prompt 中直接告知 Agent 有哪些表，不要让它自己去发现：

```
"数据库中有三张表：Students（字段 sid, name, major, gpa）、"
"Courses（字段 cid, name, department）、"
"Enrollments（字段 sid, cid）。"
```

### 7.3 不支持中文字符

**现象**：`INSERT INTO Students VALUES (999, '测试学生', 'CS', 3.5)` 失败。

**解决**：Agent 端如果涉及测试数据，用英文名。或者评估是否值得给 rookieDB 加 UTF-8 支持（大概率不值得，教学项目）。

### 7.4 DeepSeek v4-pro 返回 thinking blocks

**现象**：`response.content` 里出现 `block.type == "thinking"` 的 block，代码没有处理导致崩溃或异常显示。

**解决**：遍历 content blocks 时跳过 thinking 类型：

```python
for block in response.content:
    if block.type == "thinking":
        continue
    elif block.type == "text":
        ...
```

### 7.5 max_tokens 太小导致工具调用被截断

**现象**：Agent 调了 3 次工具，第 3 次结果还没拿到 Claude 的最终回复，`stop_reason=max_tokens` 就结束了。

**解决**：多轮 tool calling 场景至少 `max_tokens=1024`，500 不够。

### 7.6 协议细节总结

| 项目 | 值 |
|------|-----|
| 端口 | 18600 |
| 语句结束符 | 分号 `;` + 换行 `\n` |
| 响应结束符 | `=> `（注意后面有空格） |
| 退出命令 | `exit\n` |
| 编码 | ASCII/Latin-1（不支持中文） |
| 连接模式 | TCP socket，纯文本 |
| 事务模式 | 自动提交（非交互模式） |
