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

## DDA 内部模块分工（v1，2026-06-04）

| 模块 | 实现方式 | 理由 |
|------|---------|------|
| Wait-for graph 构建 | 传统 Python 代码 | 确定性算法 |
| BFS/DFS 找环 | 传统 Python 代码 | 确定性算法 |
| Victim selection | LLM Agent | 需要语义判断（优先级、业务价值）|
| 执行回滚 | DDA 直接 ROLLBACK | 简单直接 |

**DDA 本身不一定是 Multi-Agent**——死锁检测是单点问题，一个 DDA 就够了。真正需要 Multi-Agent 的是业务层（多个 Worker 并发干活）。

---

## DDA Agent 拆分设计（v2，2026-06-08，来自 Lesson 8 启发）

> **启发来源**：[Lesson 8: Multi-Agent Design Pattern](../ai-agents-for-beginners-main/08-multi-agent/README.md)
> - "专属 + 通用"拆分法：退款流程把 Agent 拆成业务专属 + 跨业务通用两类
> - Hand-off 模式：任务从 A Agent 转给 B Agent，每个 Agent 负责一个步骤
> - Collaborative Filtering 模式：多个 Agent 各从不同角度分析，协作给出综合结论
> - 6 大构建模块：通信、协调、内部架构、可观测性、模式选择、人机协作

Lesson 8 的"专属 + 通用"拆分方法 + Hand-off 模式，直接适用于 DDA 设计。

### 核心思路：DDA 不是一个 Agent，是一组 Agent

把原来"一个 DDA 包办一切"拆成三个专属 Agent，用 Hand-off 模式串联：

```
Detector Agent          Analyzer Agent          Executor Agent
  轮询 LockManager  →   分析死锁严重度    →     执行回滚
  发现死锁              选 victim                通知 Worker
  构建 wait-for graph   评估业务影响
```

### DDA 专属 Agent

| Agent | 职责 | 实现方式 |
|-------|------|---------|
| **Detector Agent** | 定时轮询 LockManager，构建 wait-for graph，BFS/DFS 找环，发现死锁后触发告警 | 传统 Python 代码（确定性算法） |
| **Analyzer Agent** | 拿到死锁信息 → 分析严重程度 → 评估各事务的优先级/业务价值 → 选定 victim | LLM Agent（需要语义判断） |
| **Executor Agent** | 执行回滚，通知受影响的 Worker，记录日志 | 传统代码（回滚）+ LLM（通知措辞） |

**Hand-off 链**：
```
Detector 发现环 → 交接给 Analyzer（附带 wait-for graph + 涉及的事务列表）
Analyzer 选 victim → 交接给 Executor（附带 victim 事务 ID + 理由）
Executor 回滚 + 通知 → 结束
```

### 通用 Agent（多 Agent 数据库系统共用）

| Agent | 职责 | 哪些场景也能用 |
|-------|------|-------------|
| **Worker Agent** | 执行数据库任务，管理事务生命周期 | 任何需要操作 DB 的 Agent |
| **MCP Server** | 数据库连接池、SQL 执行、schema 暴露 | 所有 Agent 的 DB 访问入口 |
| **Logger Agent** | 记录操作日志、死锁事件、回滚历史 | 审计、调试、监控 |
| **Notification Agent** | 死锁/异常/超时时通知相关方 | 告警、状态推送 |

### 对比 v1 vs v2

| 维度 | v1（单 DDA） | v2（多 Agent DDA） |
|------|------------|-------------------|
| 检测死锁 | DDA 内部函数调用 | Detector Agent 独立运行 |
| 选 victim | DDA 的 LLM 直接判断 | Analyzer Agent 专注分析 |
| 执行回滚 | DDA 内部函数调用 | Executor Agent 独立执行 + 通知 |
| 扩展性 | 加能力 = 改 DDA 代码 | 加能力 = 加新 Agent |
| 可观测性 | 看 DDA 日志 | 每个 Agent 独立日志 + Hand-off 节点可见 |
| 并行能力 | 串行处理 | 多个死锁场景可同时分析 |

### Phase 3 落地建议

- **Phase 3 先做 v1**（单 DDA），跑通死锁检测 → 选 victim → 回滚的完整链路
- **后续迭代 v2**：把 DDA 拆成 Detector → Analyzer → Executor 三个 Agent，用 Hand-off 串联
- **Collaborative Filtering 长远探索**：多个 Analyzer Agent 从不同角度分析（锁数量、事务时长、业务重要性），汇总裁决选 victim

### 三种 Lesson 8 模式的 DDA 映射

| 模式 | DDA 映射 | 优先级 |
|------|---------|--------|
| **Hand-off** | Detector → Analyzer → Executor 串行交接 | Phase 3 可做 |
| **Collaborative Filtering** | 多个 Analyzer 从不同角度选 victim，汇总裁决 | 未来探索 |
| **Group Chat** | Worker 之间在"群"里协商锁资源 | 未来探索 |

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
