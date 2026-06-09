# Lesson 3 笔记：Agentic Design Principles（UX 设计原则）

> 来源：[Microsoft ai-agents-for-beginners Lesson 3](https://github.com/microsoft/ai-agents-for-beginners/blob/main/03-agentic-design-patterns/README.md)
> 学习时间：2026-06-08

---

## 重要：这课不是我们预期的内容

学习计划里预期的是「工程层面的设计模式」——Tool Use、Planning、Multi-Agent、Orchestrator 等。但这课讲的是 **UX 层面的设计原则**，偏产品思维。

**工程模式在本课没有覆盖。** 部分内容分散在其他课（Lesson 4 Tool Use、Lesson 8 Multi-Agent），Anthropic 博客和 Claude Patterns 会补上工程层面的内容。

下面记录本课的核心内容——这些原则虽然偏 UX，但对我们设计 Agent 系统的交互方式有参考价值。

---

## 1. Agent 的三个设计维度

### 维度 1：Space（空间）— Agent 在哪运行

- **连接，不割裂**：Agent 帮助连接人、事件、知识，不是替代人
- **易触达，可隐身**：默认在后台工作，只在合适的时候出现；多模态（语音、文字、视觉）；前/后台无缝切换

### 维度 2：Time（时间）— Agent 如何处理时间

- **过去**：反思历史，不仅是状态数据，还包括上下文。从过去事件中建立连接，主动回忆
- **现在**：轻推（nudge），不是通知轰炸。根据上下文、文化变化、用户意图动态调整
- **未来**：适应和进化。适配不同设备、平台、用户行为习惯

### 维度 3：Core（核心）— Agent 的本质

- **拥抱不确定性，但建立信任**：不确定性是 Agent 设计的核心特征（不是 bug），但透明和信任是基础
- 人类永远有控制权——Agent 的开/关、状态始终可见

---

## 2. 三条实施指南

| 原则 | 含义 | 例子 |
|------|------|------|
| **透明（Transparency）** | 告知用户 AI 参与其中，展示历史操作，提供反馈渠道 | 显示历史提示、提供👍👎反馈按钮 |
| **可控（Control）** | 用户能自定义、修改偏好、删除数据 | 修改 System Prompt、调整输出风格、删除历史 |
| **一致（Consistency）** | 跨设备一致的多模态体验，降低认知负担 | 统一的图标、简洁回复、展开了解更多 |

---

## 3. 对我们的实际价值

虽然这课不教工程模式，但几个原则对 DDA 设计有启发：

| 原则 | DDA 场景映射 |
|------|------------|
| **透明** | DDA 检测到死锁后，要向受影响的 Worker 解释"发生了什么、为什么选你" |
| **可控** | Victim selection 可以是"建议"而非"强制"，让 Worker 有最终决定权 |
| **拥抱不确定性** | DDA 的 victim 判断不需要完美，但要给出理由，让 Worker 的 LLM 自己决策 |
| **轻推 > 通知轰炸** | DDA 不要每轮都报告状态，只在检测到异常时介入 |

---

## 4. 工程模式去哪了

| 我们想学的 | 实际在哪 |
|-----------|---------|
| Tool Use | Lesson 4（但 Step 1/2 已覆盖，跳过） |
| Multi-Agent 编排 | Lesson 8（Session 3，核心） |
| Planning | Lesson 8 部分覆盖 + Anthropic 博客补充 |
| Orchestrator-Worker | Anthropic 博客 + Claude Patterns |
| Debate | Claude Patterns |
