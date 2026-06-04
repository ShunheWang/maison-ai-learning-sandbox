# DDA（DB Deadlock Agent）设计讨论

> 时间：2026-06-04 晚
> 状态：讨论记录，非最终设计

---

## 核心定位

**DDA = 死锁检测 Agent，是项目的最终产出。**

Step 3 学 Multi-Agent 是为了给 DDA 搭台——先让多个 Agent 能并发操作 rookieDB，DDA 才有存在的必要。

---

## 三层架构（讨论结论）

```
用户（自然语言）
  │
  ▼
编排层：Orchestrator Agent
  拆任务、分派、汇总
       │
       ├──→ Worker A（独立 Agent + 独立事务）
       ├──→ Worker B（独立 Agent + 独立事务）
       └──→ Worker C（独立 Agent + 独立事务）
              │
              ▼
       MCP Server → rookieDB
              │
              ▼
       DDA（安全层）
         读锁状态 → wait-for graph → BFS 找环 → 选 victim → 回滚
```

| 层 | 谁 | 怎么做 | 为什么 |
|----|----|--------|--------|
| 编排层 | Orchestrator Agent | LLM 拆任务 → 分派 Worker | 开放式问题 |
| 执行层 | Worker Agent | LLM → SQL → execute_sql | 每 Worker 独立事务 |
| 安全层 | DDA | 传统代码（图算法）+ LLM（victim 判断）| 图算法确定，选 victim 需语义 |
| 数据层 | MCP Server + rookieDB | 确定性代码 | SQL、锁、事务 |

**关键认知**：Agent 不替代代码，Agent 编排代码。这跟阿里业务 Agent 的思路一致。

---

## 操作粒度

DDA 的操作粒度是**事务（Transaction）**，不是 Agent。

- 一个 Worker Agent 可能同时持有多个事务
- 死锁是事务之间的循环等待
- 杀 Agent 太粗暴，杀事务才是正确粒度

---

## 方案 A vs 方案 B

### 方案 A：DDA 直接操作数据库
```
DDA 检测到死锁 → DDA 自己发 ROLLBACK → Worker 下次 execute_sql 发现事务被回滚 → LLM 自己处理
```
- 优：简单，不需要 Agent 间通信
- 劣：Worker 被动发现

### 方案 B：DDA → Worker 直接通信
```
DDA 检测到死锁 → DDA 通知 Worker："你的事务是 victim" → Worker LLM 决定回滚/重试/解释
```
- 优：Worker 有机会优雅处理
- 劣：需实现 Agent 间通信

**结论**：Phase 2/3 先做方案 A，跑通链路。方案 B 后续迭代。

---

## DDA 内部模块分工

| 模块 | 实现方式 | 理由 |
|------|---------|------|
| Wait-for graph 构建 | 传统 Python 代码 | 确定性算法 |
| BFS/DFS 找环 | 传统 Python 代码 | 确定性算法 |
| Victim selection | LLM Agent | 需要语义判断（优先级、业务价值）|
| 执行回滚 | DDA 直接 ROLLBACK | 简单直接 |

**DDA 本身不一定是 Multi-Agent**——死锁检测是单点问题，一个 DDA 就够了。真正需要 Multi-Agent 的是业务层（多个 Worker 并发干活）。

---

## 未来可探索的方向（DDA 之后）

### 1. 检测策略演进
- **被动**：定时轮询 LockManager
- **主动声明意图**：Agent 执行前声明"我要拿哪些锁"→ 调度器预判冲突
- **事务阻塞超时触发**：Agent 等太久 → 主动上报 DDA
- **Lock Escalation 协商**：Agent 间协商要不要 escalate 锁

### 2. 解决策略演进
- **固定规则**：持有锁最少/最年轻的事务当 victim
- **LLM 判断**：DDA 用 LLM 分析上下文选 victim
- **Agent 辩论**：DDA 提名候选 → 各自辩护 → DDA 裁决
- **Agent 直接协商**：Agent A 和 B 自己聊"你还要多久？"
- **竞价**：每个 Agent 有优先级分，低分让高分

### 3. 通信拓扑演进
- **Hub-spoke**：DDA ↔ 所有 Agent（当前方案 A）
- **Blackboard**：共享消息板，Agent 读写，松耦合
- **Pub-Sub**：DDA 发事件，订阅者自己决定
- **Mesh**：Agent 两两直连（最去中心化）
- **Hierarchical**：上层 DDA 管下层 DDA，分布式检测

### 4. 价值感知 victim selection
- 报表查询 vs 支付事务 → 支付显然不该当 victim
- 用户等待 vs 后台任务 → 用户面事务优先保
- 短事务 vs 长事务 → 杀长事务浪费更多工作
- **谁来判断优先级？** 每个 Agent 自己声明还是 DDA 统一判断？

### 5. 去中心化自组织（极端探索）
- 没有 DDA
- Agent 群体自组织：遇到死锁 → 两两协商 → 民主投票选 victim
- DDA 是"平等 Agent"而非"特权 Agent"，靠说服力而非强制力

---

## 阿里业务 Agent（参考）

阿里 2025-2026 在做的事：
- **Agent 编排层**，不是替代后端代码
- 底层仍是微服务/API/数据库，Agent 只做编排
- 千问云：150+ API 封装为 Skills/CLI 工具，Agent 自然语言调用
- R2C Agent：MRD → 生成前后端代码，50%+ 代码采纳率
- 1688 AI 员工、天猫超喵：Agent 调后台服务，不替代后台

**跟我们做的事不直接相关**，但架构思路一致：Agent 在编排层，确定性代码在底层兜底。

---

## 跟现有学习计划的关系

不改现有 Phase 1-3 的计划。这些讨论是 Phase 3 之后的迭代方向，先记下来，到时候再挖。
