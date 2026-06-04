# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 项目概述

AI 学习沙盒 — 一步步构建一个能自然语言操作数据库的 Agent 系统。最终目标是做**死锁检测 Agent 系统**（多 Agent 并发操作 rookieDB + 自动检测死锁）。

学习的范围、深度和进度已详细记录在 `blueprint/` 目录下。核心文件：
- `blueprint/db-agent-plan.md` — 项目方案 + 学习进度 + 学习日志（合并后的唯一真相源）
- `blueprint/code-map.md` — 代码文件与学习单元的映射表
- `blueprint/ai-tech-landscape.md` — AI 技术全景图
- `blueprint/rookiedb-review.md` — rookieDB 代码评估报告

写新代码前先读 `db-agent-plan.md` 了解上下文。

## 技术栈与限制

- **LLM 调用**：Anthropic SDK，通过 DeepSeek 兼容层（`ANTHROPIC_BASE_URL=https://api.deepseek.com/anthropic`）
- **模型**：`deepseek-v4-pro`（写死在每个 .py 文件里）
- **数据库**：rookieDB（Java），通过 TCP socket（localhost:18600）通信
- **语言**：Python 3，原生 Anthropic SDK，不用 LangChain
- **无测试框架**：每个文件是独立的演示脚本，看懂概念即可

## 环境变量

```bash
ANTHROPIC_API_KEY=sk-...     # DeepSeek 的 key
ANTHROPIC_BASE_URL=https://api.deepseek.com/anthropic
```

两个来源：终端靠 `~/.zshrc`，IDE 直接运行时靠项目根目录的 `.env` 文件（每个脚本开头有手动加载逻辑）。

## 运行

```bash
# 直接跑（不依赖 rookieDB）
python3 step1-agent-toolcalling/01_hello_claude.py
python3 step1-agent-toolcalling/02_define_tool.py
python3 step1-agent-toolcalling/03_agent_loop.py

# 后续接 rookieDB 时需要先启动 Server
cd /Users/shunhewang/melbourne/cs186/berkeley-sp26-rookiedb
java -cp target/classes edu.berkeley.cs186.database.cli.Server &
```

## 文件架构（按学习顺序）

```
step1-agent-toolcalling/
  01_hello_claude.py     — Anthropic SDK 初始化 + messages.create() 基础调用
  02_define_tool.py      — Tool JSON Schema 定义，stop_reason: end_turn vs tool_use
  03_agent_loop.py       — Agent 循环（Think→Act→Observe→Repeat），mock 数据库
  04_connect_rookiedb.py — 接上真 rookieDB，socket 通信 + 端到端 Agent
  05_system_prompt.py    — System Prompt 设计：角色设定、护栏、工具选择
  06_error_handling.py   — 错误处理、重试、超时限流、优雅降级

step2-mcp/               — Step 2: MCP（待开始）
step3-multi-agent/       — Step 3: Multi-Agent（后续）
step4-rag/               — Step 4: RAG（后续）
```

## 核心架构

```
Agent (Python) ──TCP socket :18600──→ rookieDB Server (Java)
  │                                     ├─ LockManager（已实现）
  ├─ Anthropic SDK                      ├─ Transaction（已实现）
  ├─ Tool: execute_sql(sql)             └─ 死锁检测（待做）
  └─ Tool Calling Loop
```

Agent 循环模式：
1. 用户提问 → `client.messages.create(model, system, messages, tools)`
2. Claude 返回 `stop_reason="tool_use"` → 执行工具 → 把 `tool_result` 塞回 `messages` → 循环
3. Claude 返回 `stop_reason="end_turn"` → 输出最终回复，结束

## 关键约定

### 通用规则

- 每个 .py 文件是独立的"学习单元"，有自己的注释、学习点和打印输出
- **铁律：Demo 代码永远新建文件，绝不覆盖已有文件。** 每次新增的学习单元按编号递增命名（`07_xxx.py`、`08_xxx.py`），跨 Step 不重置编号，保持历史代码可追溯、可对比
- **每个 Step 独立文件夹**：进入新 Step 时建新目录（如 `step2-mcp/`），编号继续递增不归零
- **每次学习后同步更新进度**：写完新的 demo 或学完一个单元后，更新 `blueprint/db-agent-plan.md`（方案 + 进度 + 学习日志）和 `blueprint/code-map.md`（代码映射），保持最新
- **优先看文档**：用户问"下一步做什么"或"进度到哪了"时，优先引导看 `mcp-learning-outline.md`（学习大纲）或 `db-agent-plan.md`（项目方案），而不是凭记忆直接回答
- `.env` 已被 `.gitignore` 忽略（含 API key）
- `.claude/settings.local.json` 里有本项目专用的 Bash 权限配置

### 流程一：学习新知识（读文档/教程/论文）

适用范围：读 MCP 教程、看技术文档、学新概念。**不涉及 rookieDB 代码。**

```
读原文 → 生成笔记 → 用户消化 → 用户提问/确认 → 对话补充 → review 笔记 → 进入下一阶段
```

- 生成笔记后，必须等用户读完并确认（或提出问题），不要让用户马上进入下一阶段
- **笔记写完了不等于用户学完了**
- 笔记 review 规则：对照原文和对话内容完整 review，看有没有遗漏、不准确、需要补的地方
- 如果用户说的是"复习"性质的（如"昨天学了什么"），需要重新梳理

### 流程二：开发 rookieDB 相关代码

适用范围：所有涉及 rookieDB 的编码工作（新建 demo、封装工具、改 Agent 逻辑等）。**这是铁律，不可跳过。**

```
brainstorming → spec（设计文档）→ plan（实施计划）→ implement → verify
```

每个阶段产出：
| 阶段 | 产出 | 存放位置 |
|------|------|---------|
| brainstorming | 澄清需求、对比方案、确认设计 | 对话中 |
| spec | 设计文档（目标、范围、架构、关键决策） | `docs/superpowers/specs/YYYY-MM-DD-<name>.md` |
| plan | 实施计划（Task 拆解、每步代码、测试验证） | `docs/superpowers/plans/YYYY-MM-DD-<name>.md` |
| implement | 代码 + commit | `step*/` 目录 |
| verify | 端到端跑通验证 | 对话中 |

- spec 和 plan 必须提交 git
- implement 推荐使用 subagent-driven-development
- **学习和开发是两套流程，不能混用。** 学 MCP 用流程一，写 rookieDB 代码用流程二