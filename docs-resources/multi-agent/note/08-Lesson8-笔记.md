# Lesson 8 笔记：Multi-Agent Design Pattern

> 来源：[Microsoft ai-agents-for-beginners Lesson 8](https://github.com/microsoft/ai-agents-for-beginners/blob/main/08-multi-agent/README.md)
> 学习时间：2026-06-08

---

## 先修正预期

学习计划预期这课讲 5 种编排模式（Sequential、Parallel、Orchestrator-Worker、Debate、Hierarchical），实际讲的是 3 种不同维度的模式（Group Chat、Hand-off、Collaborative Filtering）。**编排模式在 Claude Patterns（Session 5）和 Anthropic 博客里补上。**

这课的价值在**设计思想**：什么时候拆 Agent、怎么通信、怎么协调——比具体的编排模式更底层，是所有多 Agent 系统都绕不开的问题。

---

## 核心问题

这节课回答四个问题：

1. **什么场景**需要多 Agent？
2. 多 Agent 比单 Agent **好在哪**？
3. 实现多 Agent 系统的**构建模块**是什么？
4. 怎么**观测**多个 Agent 之间的交互？

---

## 1. 什么时候用 Multi-Agent

三种场景触发多 Agent 的决策：

### 1.1 大负载（Large Workloads）

**含义**：任务量大到单 Agent 串行处理太慢，需要拆开并行。

拆成多个 Agent，每个处理一部分数据，并行执行，更快完成。

**例子**：大数据处理任务——TB 级别的日志分析，单 Agent 跑一天，10 个 Agent 各处理 1/10，一小时跑完。

### 1.2 复杂任务（Complex Tasks）

**含义**：任务本身跨多个领域，不可能由一个 Agent 同时精通所有方面。

跟"大负载"不同——大负载是量的问题，复杂任务是质的问题。任务本身就需要多种能力，拆开让不同 Agent 各管一个子领域。

**例子**：自动驾驶——
- 导航 Agent：路线规划
- 感知 Agent：障碍物检测
- 通信 Agent：车联网交互

这不是一个 Agent 忙不过来的问题，是一个 Agent 不可能同时精通这三个领域。

### 1.3 多元专业知识（Diverse Expertise）

**含义**：不同 Agent 有不同专长，组合起来比全能 Agent 更准。

**例子**：医疗——
- 诊断 Agent：分析症状
- 治疗方案 Agent：推荐疗法
- 监测 Agent：跟踪康复情况

三个 Agent 各有专精领域，协作效果 > 一个"全科医生" Agent。

**跟复杂任务的区别**：复杂任务是"必须拆"（一个 Agent 做不了），多元专业知识是"拆了更好"（一个 Agent 能做，但不够好）。

### 判断标准

| 问自己 | 是 → 用多 Agent | 否 → 单 Agent |
|--------|----------------|--------------|
| 任务量太大单 Agent 处理不过来？ | 多 Agent | 单 Agent |
| 任务跨多个领域，一个 Agent 精通不了？ | 多 Agent | 单 Agent |
| 拆开能显著提升质量/速度？ | 多 Agent | 单 Agent |

---

## 2. 为什么不用单 Agent 搞定

### 2.1 专业化（Specialization）

每个 Agent 只专注于一件事，不会"什么都会但什么都做不好"。

单 Agent 的问题：面对复杂任务时可能搞混——该用工具 A 却调了工具 B，或者对不擅长的领域瞎猜。多 Agent 各管一个领域，在自己的范围内精准执行。

### 2.2 可扩展（Scalability）

加新功能 = 加新 Agent，不用动已有系统。

单 Agent：加能力 = 改 prompt + 加 tool + 可能破坏原有行为。  
多 Agent：加一个新 Agent，注册到系统里，其他 Agent 不受影响。

### 2.3 容错（Fault Tolerance）

一个 Agent 挂了，其他继续跑。

单 Agent 挂了 → 整个系统停摆。多 Agent 系统里 Agent A 失败，Agent B/C/D 继续干活。关键任务还可以分配多个备份 Agent。

### 2.4 课程类比：家庭旅馆 vs 连锁旅行社

| 维度 | 家庭旅馆（单 Agent） | 连锁旅行社（多 Agent） |
|------|----------------------|---------------------------|
| 谁处理订票 | 一个人全包 | 机票、酒店、租车各司其职 |
| 扩展 | 加一个人要培训全部技能 | 新员工只学一个领域 |
| 出差错 | 老板请假 = 停业 | 一个专员请假 = 其他人顶 |

### 2.5 具体例子：订旅行

**单 Agent 方案**：
- 一个 Agent 同时处理机票搜索、酒店预订、租车
- 需要持有一大堆 tool（search_flights、book_hotel、rent_car...）
- System prompt 越来越长，容易搞混
- 维护：加一个"旅行保险"功能 = 再加一个 tool + 改 prompt

**多 Agent 方案**：
- 机票 Agent：只管搜索和预订机票
- 酒店 Agent：只管酒店
- 租车 Agent：只管租车
- 每个 Agent 只有 2-3 个 tool，prompt 短而精确
- 加"旅行保险" = 新建一个 Agent，不改现有的

---

## 3. 多 Agent 系统的构建模块（6 大要素）

用订旅行的例子串联所有模块。

### 3.1 Agent 通信（Communication）

**要决定的事**：哪些 Agent 之间要通信？怎么通信？

**例子**：机票 Agent 查到用户 1 月 1 日到纽约，酒店 Agent 必须知道这个日期才能订同期酒店。机票 Agent → 酒店 Agent 传"1 月 1 日到达纽约"。

**核心问题**：
- 用什么协议/方式？（直接函数调用？消息队列？共享内存？）
- 同步还是异步？
- 中心化路由还是点对点？

### 3.2 协调机制（Coordination）

**要决定的事**：Agent 之间怎么协调，确保不冲突、满足用户约束？

**例子**：用户要"离机场近的酒店"且"机场才有租车"。酒店 Agent 订了机场附近的 Hilton，租车 Agent 必须知道 Hilton 在哪才能安排取车点。两个 Agent 要协调——酒店 Agent 把位置传给租车 Agent，租车 Agent 确认机场有库存。

**核心问题**：
- 谁主导协调？有一个中心调度者还是 Agent 自己协商？
- 冲突怎么处理？（两个 Agent 给出矛盾的建议）
- 约束条件怎么传递？

### 3.3 Agent 内部架构（Architecture）

**要决定的事**：每个 Agent 怎么做决策？怎么从交互中学习改进？

**例子**：机票 Agent 根据用户过去的偏好（靠窗、上午起飞）来推荐航班。这要求 Agent 内部有：
- 推理能力：LLM + prompt
- 记忆能力：用户偏好存储
- 工具能力：搜索航班 API
- 学习能力：从用户的👍👎反馈中调整

**核心问题**：
- Agent 用什么模型？（LLM？规则引擎？ML 模型？）
- Agent 有没有记忆？记忆存在哪？
- Agent 怎么从反馈中学习？

### 3.4 可观测性（Visibility）

**要决定的事**：怎么看见 Agent 之间在干什么？

这个足够重要，单独在第 5 节展开。

### 3.5 多 Agent 模式（Patterns）

**要决定的事**：选哪种架构模式？中心化、去中心化、还是混合？

第 4 节展开三种具体模式。

### 3.6 人机协作（Human in the loop）

**要决定的事**：什么时候 Agent 应该停下来，让人介入？

**例子**：
- 用户要指定某个不在推荐列表里的酒店 → Agent 停下来问人
- 预订前确认→"找到 $200 的机票和 $150 的酒店，要预订吗？"
- Agent 遇到自己处理不了的异常 → 上报给人

**核心问题**：
- 哪些操作必须人工确认？（支付？删除？）
- Agent 怎么判断"我搞不定了，需要人介入"？
- 人介入后，Agent 怎么恢复继续？

---

## 4. 三种多 Agent 模式

### 4.1 Group Chat（群聊模式）

**是什么**：多个 Agent 在同一个"群"里，所有消息对所有人可见（或按规则选择性可见）。每个 Agent 可以主动发言、回复他人、或者被 @ 触发。

**典型场景**：
- 团队协作（飞书/钉钉里多个 Agent 协作）
- 客服（客户消息进群 → 客服 Agent A 先响应 → 需要时 @ Agent B 协助）
- 社交（多个 AI 角色在群聊里互动）

**架构选择**：
- **中心化**：所有消息通过中心服务器路由，服务器决定谁收到什么
- **去中心化**：Agent 两两直连，没有中心节点

**图解**：
```
中心化：                   去中心化：
   中心服务器              Agent A ←→ Agent B
   /  |  \                  ↕        ↕
  A   B   C              Agent C ←→ Agent D
```

**优点**：灵活，Agent 可以自由加入/离开，适合松耦合场景  
**缺点**：消息量大时每个 Agent 都收到所有消息，信息过载

### 4.2 Hand-off（转接模式）

**是什么**：任务从 A Agent 转给 B Agent，像客服转接——"这是技术问题，我帮你转技术部"。

A Agent 处理自己能处理的部分 → 判断需要转接 → 把上下文传给 B Agent → B Agent 继续处理。

**典型场景**：
- 客服系统：通用客服 → 技术专员 → 退款专员
- 任务管理：任务分配 → 执行 → 审核
- 工作流自动化：审批 → 处理 → 归档

**图解**：
```
用户 → Agent A（通用） → "这是技术问题，转技术部"
                           ↓
                      Agent B（技术） → "需要退款，转退款组"
                                           ↓
                                      Agent C（退款） → 解决
```

**关键设计**：
- 转接规则：什么条件触发转接？转给谁？
- 上下文传递：A 和用户的对话历史、已确认的信息 → 一并传给 B，不让用户重新说一遍

**优点**：职责清晰，每个 Agent 只处理自己领域的事  
**缺点**：转接链条太长时延迟增加，中间转接丢失上下文

### 4.3 Collaborative Filtering（协同过滤模式）

**是什么**：多个 Agent 各从不同角度独立分析同一个问题，然后协作给出综合结论。不是串行（A 做完给 B），而是并行（A、B、C 同时分析，然后汇总）。

**典型场景**：推荐系统、风险评估、多维度分析

**例子（股票推荐）**：
```
用户："推荐一只股票"
  │
  ├── Agent 1（行业专家）：分析行业前景 → "新能源板块看好"
  ├── Agent 2（技术分析）：看 K 线图 → "股价突破阻力位，趋势向上"  
  └── Agent 3（基本面）：读财报 → "市盈率合理，现金流健康"
        │
        └── 汇总 → "推荐 XYZ 股票：行业向好 + 技术面强势 + 基本面扎实"
```

**为什么需要多个 Agent**：每个 Agent 的分析方法完全不同，一个 Agent 不可能同时精通行业分析、K 线技术和财报解读。

**优点**：结果比单 Agent 更全面可靠，多角度交叉验证  
**缺点**：如果三个 Agent 意见矛盾，需要额外的"仲裁"逻辑

---

## 5. 可观测性（Visibility）

多 Agent 系统的调试比单 Agent 难很多——你看不到谁跟谁说了什么、谁卡住了、谁做错了决策。所以可观测性是**构建模块之一，不是可选项**。

三个层面：

### 5.1 日志和监控（Logging and Monitoring）

每个 Agent 的每次行动都记日志：
- 哪个 Agent 做了什么
- 什么时候做的
- 结果是什么

**作用**：调试时回溯"谁在什么时候做了什么导致出问题"。

### 5.2 可视化工具（Visualization Tools）

用图展示 Agent 之间的信息流向，一眼看出：
- 瓶颈：哪个 Agent 处理最慢
- 死循环：Agent A → B → C → A
- 孤立：哪个 Agent 从来没人调

### 5.3 性能指标（Performance Metrics）

- 任务完成时间
- 单位时间完成任务数
- Agent 输出的准确率

**旅行例子**：仪表盘上显示——用户旅行日期、机票 Agent 推荐的航班、酒店 Agent 推荐的酒店、租车 Agent 推荐的车型、各 Agent 之间的交互状态。

---

## 6. 实战场景：退款流程

课程用退款流程展示了怎么把"拆 Agent"落地——真实业务里 Agent 比想象的多。

### 6.1 退款专属 Agent

| Agent | 职责 |
|-------|------|
| **Customer Agent** | 代表客户，发起退款申请 |
| **Seller Agent** | 代表卖家，审核退款条件 |
| **Payment Agent** | 处理退款打款 |
| **Resolution Agent** | 处理纠纷——客户和卖家意见不一致时介入 |
| **Compliance Agent** | 确保退款流程合规（法律、税务、平台规则） |

### 6.2 通用 Agent（可跨业务复用）

| Agent | 职责 | 哪些场景也能用 |
|-------|------|-------------|
| **Shipping Agent** | 退货物流——生成退货单、跟踪包裹 | 购买发货、换货 |
| **Notification Agent** | 退款各阶段通知用户 | 订单通知、促销推送 |
| **Escalation Agent** | 问题升级到人工/更高权限 | 任何异常场景 |
| **Analytics Agent** | 分析退款数据 | 销售分析、用户行为 |
| **Audit Agent** | 审计退款流程是否正确执行 | 财务审计、安全审计 |
| **Security Agent** | 防欺诈退款 | 支付安全、账号保护 |
| **Quality Agent** | 退款服务质量监控 | 客服质量、物流质量 |
| **Knowledge Agent** | 维护退款相关的知识库（政策、FAQ） | 产品知识库、帮助中心 |
| **Feedback Agent** | 收集用户退款后的反馈 | 购买反馈、服务评价 |
| **Reporting Agent** | 生成退款报告 | 财务报表、运营报表 |

### 6.3 设计方法

**第一步**：拆业务专属 Agent——只跟退款流程相关的（Customer、Seller、Payment、Resolution、Compliance）

**第二步**：识别复用机会——哪些 Agent 的能力不只是退款能用？（Shipping 可以用于发货、Feedback 可以用于任何用户交互）

**第三步**：跟 6 大构建模块对接：
- 这些 Agent 之间怎么通信？（Customer → Seller: "用户申请退款"）
- 怎么协调？（Payment 要等 Seller 确认退款条件满足再打款）
- 每个 Agent 内部什么架构？（Compliance Agent 需要查法规知识库）
- 人什么时候介入？（纠纷升级需要人工审核）

---

## 7. 跟 DDA 项目的关系

### 7.1 什么时候用 Multi-Agent 的判断

| 标准 | DDA 场景 | 结论 |
|------|---------|------|
| 大负载 | 多个 Worker 同时操作数据库 | ✅ 需要 |
| 复杂任务 | Worker 各管自己的事务，DDA 管锁监控 | ✅ 需要 |
| 多元专业知识 | DDA 懂锁 + Worker 懂 SQL | ✅ 需要 |

DDA 场景满足三个条件，天然是多 Agent 问题。

### 7.2 6 大构建模块在 DDA 中的映射

| 构建模块 | DDA 的具体问题 |
|---------|--------------|
| **通信** | DDA 检测到死锁后，怎么通知受影响的 Worker？直接回滚还是发消息？ |
| **协调** | DDA 选 victim 回滚后，其他事务继续还是也要检查？victim 自动重试还是等指令？ |
| **内部架构** | DDA 内部：图算法（确定性）+ LLM（选 victim）。Worker 内部：LLM + execute_sql tool |
| **可观测性** | DDA 日志记录：锁等待图快照 → 检测到的环 → 选中的 victim → 回滚结果 |
| **模式选择** | 初期：中心化（DDA 是中心节点）。未来：去中心化协商 |
| **人机协作** | DDA 选 victim 后要不要人工确认？自动回滚的风险和人工介入的延迟怎么权衡？ |

### 7.3 三种模式在 DDA 中的可能使用

| 模式 | DDA 映射 | 优先级 |
|------|---------|--------|
| **Group Chat** | Worker 之间在"群"里协商锁资源（"我要拿 Students 表的锁，谁在用？"） | 未来探索 |
| **Hand-off** | 检测 → 分析 → 执行 三个 Agent 串行：Detector 检测死锁 → Analyzer 分析严重度选 victim → Executor 执行回滚 | Phase 3 可做 |
| **Collaborative Filtering** | 多个 DDA 从不同角度（锁数量、事务时长、业务重要性）分析选哪个 victim，汇总裁决 | 未来探索 |

### 7.4 退款场景的设计方法

"专属 + 通用"的拆法对 DDA 设计有直接启发：

**专属 Agent**（死锁检测系统特有）：
- Detector Agent — 轮询 LockManager，发现死锁
- Analyzer Agent — 分析死锁，选 victim
- Executor Agent — 执行回滚

**通用 Agent**（多 Agent 数据库系统都能用）：
- Worker Agent — 执行数据库任务（事务管理通用）
- MCP Server — 数据库连接和工具暴露（任何数据库 Agent 都能用）
- Logger Agent — 记录操作日志（审计通用）
- Notification Agent — 异常时通知（监控通用）

---

## 8. 编排模式去哪了

学习计划预期的 5 种编排模式（Sequential、Parallel、Orchestrator-Worker、Debate、Hierarchical），本课没有覆盖。

补充来源：
- **Anthropic 博客**（Session 4）：Orchestrator-Worker 实战，含代码
- **Claude Patterns**（Session 5）：7 种模式对照，含 Subagent Orchestration、Parallelization、Evaluator-Optimizer、Prompt Chaining、Routing、Master-Clone、Programmatic Orchestration
