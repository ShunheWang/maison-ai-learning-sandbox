# Lesson 1 笔记：AI Agent 是什么 & 什么时候用

> 来源：[Microsoft ai-agents-for-beginners Lesson 1](https://github.com/microsoft/ai-agents-for-beginners/blob/main/01-intro-to-ai-agents/README.md)
> 学习时间：2026-06-04 晚

---

## 1. AI Agent 的定义

**AI Agent = 让 LLM 能真正"做事"的系统，不只是生成文本。**

拆解开：
- **Environment**（环境）— Agent 工作的空间（比如 booking 平台）
- **Sensors**（感知器）— 读取环境状态（查航班价格、酒店空房）
- **Actuators**（执行器）— 采取行动（订房、发确认、取消预订）

> 对比我们已有的理解：我们的 Agent 里，Environment = rookieDB，Sensors = execute_sql 查询，Actuators = INSERT/UPDATE/DELETE。

LLM 在这个系统里的角色：它不是"脑子"，而是**推理引擎**——把模糊请求转成可执行的行动计划。

---

## 2. 7 种 Agent 类型

| 类型 | 特点 | 例子 |
|------|------|------|
| Simple Reflex | 纯规则，无记忆无计划 | 看到投诉邮件 → 转客服 |
| Model-Based Reflex | 维护内部世界模型 | 跟踪历史价格 → 标记异常 |
| Goal-Based | 有目标，自己规划步骤 | 从当前位置规划完整旅行 |
| Utility-Based | 不仅找到解，还找最优解 | 权衡成本 vs 舒适度 |
| Learning | 从反馈中学习改进 | 根据用户评价调整推荐 |
| Hierarchical | 高层拆任务 → 分给子Agent | 取消旅行 = 取消航班+酒店+租车 |
| **Multi-Agent (MAS)** | 多个独立 Agent 协作/竞争 | 不同 Agent 分管酒店、航班、娱乐 |

**重点**：Hierarchical 和 Multi-Agent 的区别 —— Hierarchical 是一个老板指挥多个下属，MAS 是多个平级 Agent 各自独立决策。

---

## 3. 什么时候用 Agent

**应该用的场景**：
- 开放式问题（步骤无法预先编程）
- 多步流程（需要跨多轮使用工具）
- 需要随时间改进（从用户反馈中学习）

**不应该用的场景**：
- 单步查询（直接 API 调用更简单）
- 确定性逻辑（传统代码更可靠）
- 实时性要求极高（Agent 推理有延迟）

---

## 4. 课程技术栈（跟我们无关的部分跳过）

课程用 Azure AI Agent Service + Microsoft Agent Framework。我们只学概念和设计模式，代码实现用 Anthropic SDK。

---

## 5. 跟我们项目的关系

我们已经实践了 Lesson 1 的核心概念：
- Agent 循环 ✅（Step 1 的 03_agent_loop.py）
- Tool Calling ✅（Step 1-2）
- System Prompt 设计 ✅（05_system_prompt.py）
- MCP 协议 ✅（Step 2）

Lesson 1 新增的认知：7 种 Agent 类型的分类框架，特别是 **Hierarchical vs Multi-Agent** 的区别 —— 这直接影响 Step 3 的设计选择：死锁检测场景是 Hierarchical（一个检测器 Agent 管理多个 Worker）还是 MAS（多个 Agent 各自独立操作，检测是外部系统）？
