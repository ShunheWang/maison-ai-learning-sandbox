# 代码 ↔ 笔记映射

每个 .py 文件对应一个学习单元，按编号顺序递增。文件独立运行，不互相依赖。

## Step 1：单 Agent + Tool Calling

| 文件 | 学习单元 | 核心概念 | 对应笔记 |
|------|---------|---------|---------|
| `step1-agent-toolcalling/01_hello_claude.py` | Claude API 基础 | SDK 初始化、messages.create()、三种角色、Token | `db-agent-plan.md` § 2026-06-01 |
| `step1-agent-toolcalling/02_define_tool.py` | Tool 定义 | JSON Schema、stop_reason、tool_use block | `db-agent-plan.md` § 2026-06-02 上午 |
| `step1-agent-toolcalling/03_agent_loop.py` | Agent 循环 | while 循环、tool_result 回传、消息数组积累 | `db-agent-plan.md` § 2026-06-02 下午 |
| `step1-agent-toolcalling/04_connect_rookiedb.py` | 接 rookieDB | socket 通信、闭包工厂、recv_until_prompt | `db-agent-plan.md` § 2026-06-02 晚 |
| `step1-agent-toolcalling/05_system_prompt.py` | System Prompt | 角色设定、护栏、反幻觉、对比实验 | `db-agent-plan.md` § 2026-06-03 |
| `step1-agent-toolcalling/06_error_handling.py` | 错误处理 | 指数退避重试、参数校验、断线重连、is_error | `db-agent-plan.md` § 2026-06-03 |

## Step 2：MCP

| 文件 | 学习单元 | 核心概念 | 对应笔记 |
|------|---------|---------|---------|
| `step2-mcp/07_first_mcp_server.py` | 第一个 MCP Server | FastMCP、@mcp.tool()、Inspector 测试 | `02-First-MCP-Server-笔记.md` |

## 专题学习

| 目录 | 内容 | 对应代码 |
|------|------|---------|
| `docs-resources/tool/note/` | Tool Use 完整笔记（11 章）+ demo | `02`, `03` |
| `docs-resources/mcp/note/` | MCP 学习笔记 | `07` |
| `docs-resources/mcp/` | MCP 官方教程（mcp-for-beginners 等） | — |
| `blueprint/rookiedb-review.md` | rookieDB 代码评估 | `04`, `06` |

## 学习资源位置

| 文件夹 | 用途 |
|--------|------|
| `step1-agent-toolcalling/` | Step 1 所有 demo 代码 |
| `step2-mcp/` | Step 2 代码（即将开始） |
| `blueprint/` | 项目蓝图：方案、日志、代码评估、本映射表 |
| `docs-resources/` | 外部学习资料（教程、参考实现） |
| `docs/` | 自动生成的 spec/plan（Superpowers 输出） |