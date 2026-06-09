# Spec: rookieDB 锁状态查询接口

> 日期：2026-06-09
> 状态：已实现

---

## 背景

demo 14（死锁场景复现）需要从 Python 端实时查看 rookieDB 的锁状态——哪个事务持有什么锁、哪个事务在等什么锁。rookieDB CLI 已有 `\locks` metacommand，但它只显示当前线程的事务锁，无法获取全局锁快照。

**核心需求**：从 Python socket 连接调一个命令，拿到所有事务的锁状态。

---

## 方案对比

### 方案 A：加 SQL/CLI 命令（推荐）

**做法**：在 rookieDB 侧加一个命令（`SHOW LOCKS` 或 `\alllocks`），Python 通过 socket 发送命令，rookieDB 返回 LockManager 完整状态。

**具体步骤**：
1. LockManager.java 加 `getAllLockInfo()` 方法，dump `transactionLocks` 和 `resourceEntries` 两个 Map
2. 在 CLI 的 `parseMetaCommand()` 里加 `\alllocks`，调用上述方法
3. 重新编译，重启 Server
4. Python `db.execute("\\alllocks")` 拿到真实锁状态

**优点**：
- 改动最小（加一个方法 + 一个命令）
- 走现有 CLI 框架，不引入新协议
- Python 端跟调用普通 SQL 一样，零学习成本

**缺点**：
- 需要改 rookieDB 源码 + 重新编译
- `\alllocks` 通过 socket 输出纯文本，并发多个 Worker 时输出可能混扰

### 方案 B：Python 直连 Java JVM

**做法**：Python 启动一个 JVM（JPype/PyJNIus），加载 rookieDB classpath，调 LockManager API。

**优点**：
- 不改 rookieDB 源码
- 能拿结构化数据（Java 对象），不依赖文本解析

**缺点**：
- 跨进程拿 LockManager 实例极难：LockManager 是 Server 进程里的 Java 对象，Python 启动的是另一个 JVM，拿不到那个内存里的对象
- 要跨进程读取，要么用 JMX 远程 attach，要么用 Debug 接口，复杂度远超需求
- 引入 JVM 依赖，破坏 Python 项目的简洁性

**结论**：杀鸡用牛刀，否决。

### 方案 C：Python 推断锁状态

**做法**：解析 Worker 执行的 SQL 文本，根据"SQL 超时了"推测"可能在等锁"，构建虚拟锁状态。

**优点**：
- 不改 rookieDB 源码
- 不依赖外部工具

**缺点**：
- 不精确——推断的是"应该"的锁状态，不是 rookieDB 真实状态
- 页级锁/表级锁等细节无法推断
- 残留事务、锁排队等复杂情况完全不可见
- DDA Phase 3 需要真实锁状态才能建 wait-for graph

**结论**：demo 14 勉强可用，Phase 3 不可用。

---

## 选取方案

**选方案 A**。理由：

1. 改动最小，收益最大——一个方法 + 一个命令
2. 走现有 CLI metacommand 框架，Server 无需改
3. Phase 3 的 DDA 必须用真实锁状态
4. 方案 B 太重，方案 C 不够用

---

## 实现内容

### 修改文件

| 文件 | 改动 |
|------|------|
| `concurrency/LockManager.java` | 新增 `getAllLockInfo()` 方法，dump `transactionLocks` + `resourceEntries` |
| `cli/CommandLineInterface.java` | 新增 `\alllocks` metacommand，调用 `getAllLockInfo()` |

### LockManager.getAllLockInfo()

```java
public synchronized String getAllLockInfo() {
    StringBuilder sb = new StringBuilder();
    sb.append("=== LockManager State ===\n");
    sb.append("transactionLocks: ").append(transactionLocks).append("\n");
    sb.append("resourceEntries:\n");
    for (Map.Entry<ResourceName, ResourceEntry> entry : resourceEntries.entrySet()) {
        sb.append("  ").append(entry.getKey()).append(" => ")
          .append(entry.getValue().toString()).append("\n");
    }
    return sb.toString();
}
```

### CLI \alllocks metacommand

```java
} else if (cmd.equals("alllocks")) {
    this.out.println(db.getLockManager().getAllLockInfo());
}
```

### Python 使用

```python
result = db.execute("\\alllocks")
# 输出:
# === LockManager State ===
# transactionLocks: {1=[T1: X(database/students/160000000001)]}
# resourceEntries:
#   database/students/160000000001 => Active Locks: [T1: X(...)], Queue: []
#   database/courses/170000000001 => Active Locks: [T2: X(...)], Queue: []
```

---

## 已知问题

1. **并发输出混扰**：多个 Worker 同时调 `\alllocks` 时，socket 字节流可能混杂。Phase 3 DDA 需用独立 socket 连接轮询，或加请求 ID 匹配
2. **出队不可见**：`\alllocks` 是快照，只能看到死锁当下的锁状态。DDA 需要定时轮询来捕获死锁

---

## 验证

```bash
# 重启 rookieDB
kill $(lsof -ti :18600) && java -cp target/classes ... Server &

# Python 测试
python3 -c "
db = RookieDBConnection()
db.connect()
db.execute('BEGIN;')
db.execute('UPDATE Students SET gpa = 4.0 WHERE sid = 1;')
print(db.execute('\\alllocks'))
"
# 输出: T1: X(database/students/160000000001) ← 真实锁
```
