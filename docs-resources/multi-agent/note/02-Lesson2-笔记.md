# Lesson 2 笔记：AI Agent 框架概览

> 来源：[Microsoft ai-agents-for-beginners Lesson 2](https://github.com/microsoft/ai-agents-for-beginners/blob/main/02-explore-agentic-frameworks/README.md)
> 学习时间：2026-06-08

---

## 1. AI Agent Framework 是什么

**给开发者用的软件平台，简化 Agent 的创建、部署和管理。** 提供预构建组件、抽象层、工具，让开发者专注于业务逻辑而不是底层实现。

三个核心能力：
- **Agent 协作与协调**：多个 Agent 一起干活，通信、协调
- **任务自动化与管理**：多步骤工作流、任务委派、动态任务管理
- **上下文理解与适应**：根据环境变化实时调整决策

---

## 2. 框架能帮你做什么

### 2.1 模块化组件
- AI 连接器、Memory 模块、函数调用、Prompt 模板等预构建组件
- 不需要从零写，组装即可

### 2.2 协作工具
- 多 Agent 角色定义、任务分配、通信协调
- 代码示例：DataRetrieval Agent + DataAnalysis Agent 串行协作

### 2.3 实时学习
- 反馈循环，从交互中学习并动态调整行为

---

## 3. 微软的两个产品

| | Microsoft Agent Framework | Azure AI Agent Service |
|------|------|------|
| 定位 | SDK，帮你写 Agent 代码 | 平台服务，帮你部署和扩展 Agent |
| 核心 | AzureAIProjectAgentProvider | Azure Foundry 集成 |
| 模型 | Azure OpenAI | 多种模型（GPT-4, Llama 3, Mistral...） |
| 场景 | 快速原型、开发迭代 | 企业级部署、安全、扩展 |

**简单说**：MAF 是开发工具，Agent Service 是部署平台。先 MAF 开发，再 Agent Service 上线。

---

## 4. 为什么我们不用这些框架

Lesson 2 介绍的两个框架都是 **Azure 生态**的产品，跟我们的技术栈无关。

回头看我们选 Anthropic 原生 SDK 的理由：
- **学原理，不学框架** — 框架抽象了太多细节，你不知道底下发生了什么
- **框架有锁定效应** — MAF 绑 Azure，LangChain 有自己的生态
- **SDK 够用** — `client.messages.create()` + 手动循环，20 行代码就是 Agent
- **换底层更自由** — 原生 SDK 不限定 LLM provider，换个 base_url 就行

**结论**：这课的价值是建立全局视野，确认"我知道为什么不用它们了"——原计划就是这么定的，确实如此。

---

## 5. 跟我们项目的关系

基本没关系。微软生态我们不用，框架概念我们已经用自己的方式实现了：

| 框架做的事 | 我们怎么做的 |
|-----------|------------|
| Agent 创建 & 管理 | `client.messages.create()` + 手动循环 |
| Tool 定义 | Anthropic Tool JSON Schema / MCP `@mcp.tool()` |
| 多 Agent 协调 | 还没做（Step 3 的内容） |
| Memory / 上下文 | messages 数组积累（原始但透明） |
| 企业安全 / 部署 | 学习项目，不需要 |
