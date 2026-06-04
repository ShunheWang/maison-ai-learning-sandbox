# Step 3 Phase 1 学习计划：多 Agent 概念

> 目标：理解多 Agent 的编排模式、通信方式和设计原则。
> 方法：Microsoft 教程打底（概念层）→ Anthropic 博客补充（SDK 层）→ Claude Patterns 收尾（速查卡）。

## 学习顺序（5 个 Session）

```
Session 1: 基础扫盲           Session 2: 设计模式          Session 3: 多Agent 核心
  Lesson 1: Agent是什么        Lesson 3: Agentic             Lesson 8: Multi-Agent
  Lesson 2: 框架概览           Design Patterns                Design Pattern
  ───────────────────────────────────────────────────────────────→
       1 小时                          2 小时                       2 小时

Session 4: SDK 实战            Session 5: 模式速查
  Anthropic 官方博客            Claude Agentic Patterns
  Orchestrator-Worker           7 种模式对照卡片
  ─────────────────────────────────────────→
       1.5 小时                       1 小时
```

---

## Session 1：基础扫盲（快速过）

### 1.1 Agent 是什么 & 什么时候用

**阅读**：`ai-agents-for-beginners-main/01-intro-to-ai-agents/README.md`

**要搞清楚的问题**：
- AI Agent 的三个核心组成部分（Environment / Sensors / Actuators）是什么？
- 7 种 Agent 类型分别代表什么？Hierarchical 和 Multi-Agent 的区别？
- 什么时候该用 Agent、什么时候不该用？
- 跟我们已做的 Step 1/2 对照：我们的 Agent 属于哪种类型？

**产出**：笔记 `01-Lesson1-笔记.md`

### 1.2 框架概览（了解即可）

**阅读**：`ai-agents-for-beginners-main/02-explore-agentic-frameworks/README.md`

**要搞清楚的问题**：
- 市面上有哪些 Agent 框架？（LangChain、CrewAI、AutoGen、MAF...）
- 各自的定位和适用场景是什么？
- 为什么我们选 Anthropic 原生 SDK 而不是用框架？

**注意**：这课的目的是建立全局视野，不需要深入任何框架的代码。学完后的结论应该是"我知道为什么不用它们了"。

**产出**：笔记 `02-Lesson2-笔记.md`

---

## Session 2：Agentic Design Patterns（核心基础）

**阅读**：`ai-agents-for-beginners-main/03-agentic-design-patterns/README.md`

**要搞清楚的问题**：
- Agentic Pattern 是什么？和普通 prompt engineering 有什么区别？
- 每种 Pattern 的核心思想、适用场景、代码实现思路
- 哪些 Pattern Step 1/2 已经用过了？（Tool Use、Agent Loop）
- 哪些 Pattern 是 Step 3 需要重点学的？（Multi-Agent、Orchestrator）
- Prompt Chaining vs Orchestrator 的区别？
- Planning Design Pattern 怎么工作的？（Agent 自己制定计划 → 执行 → 评估）

**产出**：笔记 `03-Lesson3-笔记.md`

---

## Session 3：Multi-Agent Design Pattern（Step 3 最重要的内容）

**阅读**：`ai-agents-for-beginners-main/08-multi-agent/README.md`

**要搞清楚的问题**：
- 多 Agent 系统的核心架构模式有哪些？
  - Sequential（串行流水线）
  - Parallel（并行执行）
  - Orchestrator-Worker（一个 Leader + 多个 Worker）
  - Debate（多个 Agent 辩论）
  - Hierarchical（多层嵌套）
- 每种模式的通信方式是什么？（共享消息 vs 消息传递）
- Agent 之间怎么协调？（投票、评分、排队、竞争）
- 什么时候用哪种模式？
- 多 Agent 系统常见的坑？（上下文爆炸、无限循环、协调失败）

**产出**：笔记 `08-Lesson8-笔记.md`

---

## Session 4：Anthropic 实战（SDK 层面的多 Agent）

**阅读**：[Anthropic: Building a Multi-Agent Research System](https://www.anthropic.com/engineering/multi-agent-research-system)

**为什么现在读**：学完 Microsoft 的通用概念后，再看 Anthropic 官方怎么用同一套 SDK 实现 Orchestrator-Worker。概念已经懂了，读这篇就是看"代码怎么写"。

**要搞清楚的问题**：
- Anthropic 的 Orchestrator-Worker 架构具体怎么实现？
- Subagent 怎么设计？（single responsibility、独立 context）
- 工具怎么在不同 Agent 之间分配？（最小权限原则）
- 90.2% 性能提升是怎么来的？拆分的代价和收益？
- 跟我们 Step 3 的关系：死锁检测场景下，Orchestrator 和 Worker 分别干什么？

**产出**：笔记 `04-Anthropic-Blog-笔记.md`

---

## Session 5：模式速查卡（收尾 + 对照）

**阅读**：[Claude Agentic Patterns](https://github.com/anthropics/claude-cookbooks/issues/303)

**为什么最后读**：这 7 种模式前面的课程都讲过了，这篇是可视化对照 + Anthropic SDK 代码。当作"速查卡"来用，不需要逐字读。

**要搞清楚的问题**：
- 7 种模式分别对应我们学过的哪个概念？
- 每种模式在我们项目里的映射是什么？
- 哪些模式 Step 3 用得上？哪些可以先不管？

**产出**：笔记 `05-Claude-Patterns-笔记.md`（简短，主要是对照表）

---

## 学习资料位置

| 资料 | 路径 | 优先级 |
|------|------|--------|
| Microsoft Lesson 1 | `docs-resources/multi-agent/ai-agents-for-beginners-main/01-intro-to-ai-agents/README.md` | ⭐ |
| Microsoft Lesson 2 | `docs-resources/multi-agent/ai-agents-for-beginners-main/02-explore-agentic-frameworks/README.md` | ⭐ |
| Microsoft Lesson 3 | `docs-resources/multi-agent/ai-agents-for-beginners-main/03-agentic-design-patterns/README.md` | ⭐⭐⭐ |
| Microsoft Lesson 8 | `docs-resources/multi-agent/ai-agents-for-beginners-main/08-multi-agent/README.md` | ⭐⭐⭐ |
| Anthropic Blog | https://www.anthropic.com/engineering/multi-agent-research-system | ⭐⭐⭐ |
| Claude Patterns | https://github.com/anthropics/claude-cookbooks/issues/303 | ⭐⭐ |

## 跳过清单

- ❌ Microsoft Lesson 4 Tool Use（Step 1/2 已覆盖，需要时复习）
- ❌ Microsoft Lesson 5-7, 9-18（跟 Step 3 无关）
- ❌ 所有代码示例（Azure SDK，我们用 Anthropic SDK 重写）
- ❌ Claude Agent SDK Best Practices（生产级内容，Step 3 用不上，等做 DB-Agent 时再回来看）
- ❌ AI Agents from Scratch（等 Phase 2 动手时再参考）
- ❌ PicoAgents（备查，不需要主动学）

## 学习节奏

假设每天 2-3 小时：

| 天 | Session | 内容 | 预计 |
|----|---------|------|------|
| 今晚 | Session 1 + 2 | Lesson 1 + 2 + 3 | 2.5h |
| 明天 | Session 3 | Lesson 8（重点） | 2h |
| 后天 | Session 4 + 5 | Anthropic Blog + Claude Patterns | 2h |

3 天完成 Phase 1，然后进入 Phase 2 动手写 demo。
