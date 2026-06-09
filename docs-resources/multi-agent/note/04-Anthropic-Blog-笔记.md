# Session 4 笔记：Anthropic 多 Agent 研究系统实战

> 来源：[Anthropic: Building a Multi-Agent Research System](https://www.anthropic.com/engineering/multi-agent-research-system)
> 学习时间：2026-06-08

---

## 为什么读这篇

Lesson 8 讲了"什么时候用多 Agent"和"设计思想"，这篇讲的是**怎么落地写代码**。Anthropic 用原生 SDK 实现了 Orchestrator-Worker，跟我们的技术栈一致，比 Microsoft 教程的 Azure 示例更贴近我们的项目。

---

## 一、架构总览：Orchestrator-Worker 模式

```
用户提问
  │
  ▼
LeadResearcher Agent（主 Agent，Claude Opus 4）
  │  分析问题 → 制定策略 → 拆成子任务
  │  将策略存入 Memory（防止上下文窗口截断）
  │
  ├──→ Subagent 1（Claude Sonnet 4）: 研究方向 A
  ├──→ Subagent 2（Claude Sonnet 4）: 研究方向 B
  └──→ Subagent 3（Claude Sonnet 4）: 研究方向 C
        │  各自独立搜索、评估结果、返回发现
        ▼
      LeadResearcher 汇总 → 判断是否还需要更多研究
        │  如果需要 → 再派另一批 subagent
        ▼
      CitationAgent 处理引用 → 最终输出
```

**关键设计**：
- Lead agent 用强模型（Opus），subagent 用弱模型（Sonnet）——省钱，因为 subagent 的任务更机械
- Subagent 并行跑，不串行——复杂查询时间最多减少 90%
- Subagent 不直接返回大段文本给 lead，而是**写文件**，lead 只拿到轻量引用——避免信息膨胀

---

## 二、Subagent 设计原则

### 2.1 委派要具体（Delegation Specificity）

每个 subagent 必须明确：
- **目标**：要回答什么问题
- **输出格式**：返回什么格式的结果
- **工具指导**：用哪些工具、怎么用
- **边界**：管什么、不管什么

**反面例子**：指令模糊 → Subagent A 和 Subagent B 搜了同一个方向，浪费 token。

### 2.2 工作量分级（Effort Scaling）

在 prompt 里直接告诉 subagent 要花多少力气：

| 任务类型 | Subagent 数量 | 每个 tool_use 次数 | 例子 |
|---------|-------------|------------------|------|
| 简单事实查询 | 1 | 3-10 | "苹果市值多少" |
| 直接对比 | 2-4 | 10-15 | "对比 iPhone 15 和 16" |
| 复杂研究 | 10+ | 各自不同 | "分析全球芯片供应链" |

**启示**：不是越多的 subagent 越好，量跟任务复杂度匹配。

### 2.3 自我改进（Self-Improvement via Model）

一个很妙的设计：**用 Agent 来改进 Agent**。

他们做了一个 tool-testing agent——给一个有缺陷的 MCP 工具，让它试着用，然后把工具的 description 重写成更准确的版本。结果：**任务完成时间减少了 40%**。

**实际应用场景**：我们的 `execute_sql` 工具的 description 写得不好 → Agent 调用时传错参数 → tool-testing agent 自动发现并改进 description。

### 2.4 搜索策略启发式

Prompt 里写策略而不是死规则：
- 先用短、广的关键词探索
- 根据结果逐步收窄
- 不要一上来就用太具体的查询

**核心**：subagent 不是在执行脚本，而是在做探索性研究。Prompt 教它"怎么思考"，不是"按步骤 1-2-3 做"。

### 2.5 Extended Thinking

- Lead agent：调用前 thinking——分析问题、评估工具、决定 subagent 数量
- Subagent：调用后 thinking——拿到工具结果后评估质量、调整下一步查询

**但注意**：deepseek-v4-pro 的 thinking 是自动的，我们不用显式控制，但思路一样。

---

## 三、工具设计原则

这篇对工具设计讲得很狠：

| 原则 | 含义 |
|------|------|
| **Agent-工具接口跟人机接口一样重要** | 工具描述写不好 = Agent 不会用 = 系统废了 |
| **用错工具是灾难性的** | Agent 用 web search 找 Slack 里的信息 → 永远找不到，浪费全部 token |
| **每个工具要有独特目的和清晰描述** | 两个工具功能重叠 → Agent 选错 → 走偏 |
| **MCP 放大了这个问题** | MCP Server 来自不同作者，工具描述质量参差不齐 |
| **优先用专用工具而不是通用工具** | 专用工具更准，Agent 更不容易走偏 |

**对我们项目的启示**：
- `execute_sql`、`list_tables`、`describe_table` 的 description 要写好
- 后续加新工具（如 `show_locks`、`kill_transaction`）要明确跟已有工具的区别
- DDA 的 tool 要精心设计，不给 Agent 用错的机会

---

## 四、性能结果

### 4.1 核心数据

| 指标 | 数据 |
|------|------|
| 多 Agent vs 单 Agent（Opus 4） | 多 Agent **提升 90.2%** |
| 性能差异的 80% 归因 | **Token 用量**——用更多 token 就更好 |
| 模型升级 vs 翻倍 token 预算 | 升级到 Sonnet 4 的提升 > Sonnet 3.7 翻倍 token |
| 多 Agent 的 token 消耗 | 比普通 chat 多约 **15 倍** token |

### 4.2 什么时候多 Agent 值得做

**值得**：
- 广度优先任务（多个独立方向并行探索）
- 需要大量并行化
- 信息量超过单上下文窗口
- 需要对接大量复杂工具

**不值得**：
- 所有 subagent 需要共享同一上下文
- 子任务之间有大量依赖
- **大多数编程任务**（可并行的子任务比研究少）
- **Agent 还不擅长实时协调和委派**

最后一条很重要：**Agent 不擅长实时协调其他 Agent**——这解释了为什么我们现在不做 Agent 间直接通信（方案 B）。

---

## 五、评估方法

### 5.1 从小开始

用约 20 个有代表性的查询开始测试。效果差距大时（如 prompt 改一行，成功率从 30% 跳到 80%），小样本就够了。

### 5.2 LLM-as-Judge

用 LLM 给每次输出打分，评分标准：
- 事实准确性（结论 vs 来源）
- 引用准确性（来源 vs 结论）
- 完整性（所有要求的方面都覆盖了）
- 来源质量（一手 > 二手）
- 工具效率（用了合适的工具，次数合理）

输出 0.0-1.0 分数 + pass/fail。

### 5.3 人类评估

LLM 评估漏掉的东西：
- 不寻常查询上的幻觉
- 系统故障
- 来源选择偏见（比如早期版本偏好 SEO 优化过的内容农场而不是学术 PDF）

### 5.4 End-State 评估

不是逐轮评估，而是看最终状态。Agent 做完后检查"正确的结果出现了吗"。对复杂工作流，按检查点拆开评估。

**对我们项目的启示**：评估 DDA 不是看它每步做了什么，而是看"死锁解了吗？回滚的对吗？系统恢复了吗？"

---

## 六、生产环境挑战

| 挑战 | 解决方案 |
|------|---------|
| **错误累积**：有状态 Agent 跑了很久，中间出错，重跑代价大 | 从出错位置恢复，不重跑全流程 |
| **调试困难**：非确定性行为，每次跑结果不同 | 全链路追踪：记录每一步的输入/输出 |
| **部署不中断**：Agent 一直在跑，代码更新不能打断它 | Rainbow 部署：新旧版本共存，逐步切流量 |
| **同步瓶颈**：Lead agent 等所有 subagent 完成才能继续 | 异步执行是下一个目标，但增加协调复杂度 |

---

## 七、核心收获

1. **Prompt 编码启发式，不是死规则**——教 Agent 怎么思考，不是教它按步骤执行

2. **原型到生产的差距巨大**——"最后一公里是最长的一公里"。Agent 的错误会累积，小问题会滚雪球

3. **多 Agent 本质上是在扩展 token 预算**——不是"多 Agent 更聪明"，而是"多 Agent 能用更多 token 来思考和搜索"

4. **Subagent 输出到文件系统**——不把大段文本塞回 lead agent 的 messages，避免"传话筒效应"（信息在每次传递中丢失）

5. **长对话管理**：Agent 定期总结已完成的工作，把关键信息存到外部 Memory，用干净上下文启动新 subagent

6. **团队协作**：研究、产品、工程团队必须紧密合作，深入理解 Agent 的能力边界

---

## 八、跟 DDA 项目的关系

### 直接可用的设计

| Anthropic 的设计 | DDA 中怎么用 |
|-----------------|------------|
| Lead agent (Opus) + Subagent (Sonnet) | Orchestrator 用强模型，Worker 用弱模型 |
| Subagent 写文件而不是返回大段文本 | DDA 检测结果写到外部存储，Worker 只收到"你的事务被回滚" |
| Prompt 教策略，不教步骤 | DDA 的 prompt 教"怎么判断 victim"，不教"第一步查锁、第二步..." |
| 工具 description 极其重要 | `show_locks`、`kill_transaction` 的描述要仔细打磨 |
| End-State 评估 | 评估 DDA："死锁解了吗？"不看中间步骤 |
| 工作量分级 | 简单并发 = 2-3 Worker，复杂场景 = 更多 |

### 踩坑预警

| 风险 | 我们的对策 |
|------|----------|
| Agent 不擅长实时协调 Agent | 方案 A 先做（DDA 直接操作 DB），不做 Agent 间协商 |
| 错误累积 | DDA 每次检测从干净状态开始，不依赖上次结果 |
| Token 爆炸 | Subagent 只回传结果摘要，不传完整 messages |
