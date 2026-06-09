# Session 5 笔记：Claude Agentic Patterns 速查

> 来源：[agentic-ai-systems](https://github.com/ThibautMelen/agentic-ai-systems)（基于 Anthropic "Building Effective Agents"）
> 学习时间：2026-06-09
> 定位：速查卡，不逐字读，建立全局对照

---

## 核心概念：Workflows vs Agents

| | Workflows | Agents |
|------|-----------|--------|
| **谁控制流程** | 代码 | LLM |
| **路径** | 预定义 | 动态 |
| **可预测性** | 高 | 低 |
| **可调试性** | 容易 | 难 |
| **灵活性** | 有限 | 最大 |
| **适用** | 步骤已知 | 开放式问题 |

**一句话**：能预知步骤用 Workflow，步骤不确定用 Agent。

---

## 6 种 Workflow 模式

### 0. Baseline（基线）
```
用户输入 → 一次 LLM 调用 → 输出
```
- 无编排，无工具，就是最原始的 chat
- 我们：`01_hello_claude.py`

### 1. Prompt Chaining（提示链）
```
A 的输出 → B 的输入 → C 的输入 → 最终结果
```
- 串行流水线，上一步的输出是下一步的输入
- 适合：明确的多步骤任务，每步依赖前一步
- 我们：Step 1 的 Agent 循环每轮都依赖上轮 tool_result

### 2. Routing（路由）
```
用户输入 → 分类 → 路由到专门的处理器
                  ├─ 类型A → Handler A
                  ├─ 类型B → Handler B
                  └─ 类型C → Handler C
```
- 先分类，再分派
- 适合：输入类型明确不同，各有专门处理方式
- DDA 场景：读请求 → Worker A，写请求 → Worker B

### 3. Parallelization（并行化）
```
用户输入 → 拆成独立子任务 → 并行执行 → 汇总
             ├─ 子任务A ─┐
             ├─ 子任务B ─┼→ 汇总
             └─ 子任务C ─┘
```
- 子任务之间独立，不需要互相等
- 适合：多方向独立分析、大数据分片处理
- 我们：Phase 2 多个 Worker 同时执行各自事务

### 4. Orchestrator-Workers（编排器-工作者）
```
Orchestrator 拆任务 → 派给专职 Worker → Worker 干完回传 → 汇总
```
- 跟 Parallelization 的区别：Worker 各有所长（专职），不一定是同一类任务
- 适合：复杂任务需要不同专业的 Agent 协作
- DDA 场景：Orchestrator 拆"分析 CS186"→ Worker A 查成绩、Worker B 查课程、Worker C 生成报告

### 5. Evaluator-Optimizer（评估-优化）
```
生成器 → 产出 → 评估器 → 不通过 → 生成器修改 → 再评估 → 通过 → 输出
```
- 生成 + 审查的循环
- 适合：输出质量要求高，需要反复打磨
- DDA 场景：Worker 生成 SQL → Evaluator 检查是否可能死锁 → 警告 Worker 调整顺序

---

## 3 种 Workflow 变体

| 变体 | 基于 | 特点 |
|------|------|------|
| **Wizard Workflow** | Prompt Chaining | 每步之间加人工确认 |
| **Parallel Tool Calling** | Parallelization | 一次响应里并行调多个工具 |
| **Master-Clone** | Parallelization | 同一个 Agent 复制多份并行跑 |

---

## Autonomous Agent（自治 Agent）

```
Agent → 思考 → 决定 → 调工具 → 观察结果 → 思考 → ... 直到完成
```

- LLM 自己控制流程，不走预定义路径
- 就是我们的 Agent 循环：while + stop_reason + tool_use + tool_result
- 最大的灵活性，但最不可预测

---

## 模式选择决策树

```
任务复杂吗？
  ├─ 不复杂（1步） → Baseline
  └─ 复杂
       ├─ 步骤确定吗？
       │    ├─ 确定（2-4步串联） → Prompt Chaining
       │    ├─ 确定（分类型） → Routing
       │    ├─ 确定（可并行） → Parallelization
       │    ├─ 确定（需专职） → Orchestrator-Workers
       │    └─ 确定（需打磨） → Evaluator-Optimizer
       └─ 不确定（开放式） → Autonomous Agent
```

---

## 跟 DDA 项目的对照

| 模式 | 我们在 DDA 中怎么用 | 优先级 |
|------|-------------------|--------|
| **Baseline** | — 太简单，DDA 不需要 | — |
| **Prompt Chaining** | Detector → Analyzer → Executor 串行 | Phase 3 |
| **Routing** | DDA 判断死锁类型 → 路由到不同处理策略 | 未来 |
| **Parallelization** | 多个 Worker 同时操作 rookieDB | **Phase 2 核心** |
| **Orchestrator-Workers** | Orchestrator 拆任务 → Worker 各管各的事务 | **Phase 2 核心** |
| **Evaluator-Optimizer** | Worker 生成 SQL → DDA 审查 → 提示调整 | 未来 |
| **Autonomous Agent** | 每个 Worker 自己的 Agent 循环 | Phase 2 即用 |

---

## Session 5 小结

Phase 1 学完了。所有模式都能在我们已有的代码里找到影子，没有全新的概念——**我们已经在写这些模式了，只是没叫这些名字。**

学完后的认知变化：
- Step 1：不知道这些叫"模式"，就是手动写 while 循环和 messages 拼接
- 现在：知道每种模式的名称、适用场景、trade-off，可以主动选择
