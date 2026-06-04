# Step 2 MCP 复习题

基于 07~11 的代码，检验是否真正理解 MCP 的设计思想。

---

## 1. MCP 三层分离

看 `09_agent_with_mcp.py`，画出"法官—传令兵—执行者"三层分别对应代码里的哪些部分？如果把 Agent 里的 `tools` 参数从 `anthropic_tools` 改成手写 JSON Schema，跟 MCP 还有什么关系？

---

## 2. Agent 循环中 messages 的膨胀轨迹

`09` 跑了 3 轮 tool_use 后，`messages` 数组里有多少条消息？每条的角色和内容类型是什么？如果 `execute_sql` 一次返回 5000 行数据，messages 会有什么问题？

---

## 3. ThinkingBlock 为什么需要过滤

`deepseek-v4-pro` 的 ThinkingBlock 是什么？不过滤的话代码哪里会崩？为什么是**存 assistant 消息时过滤**而不是**接收 response 时就丢掉**？

---

## 4. 懒初始化 vs 启动连接

`10_rookiedb_mcp_server.py` 为什么用 `get_db()` 懒初始化，而不是在模块加载时直接 `db.connect()`？跟 `mcp run` 的内部机制有什么关系？

---

## 5. MCP Tool vs MCP Resource 的设计意图

`10` 里同时用了 `@mcp.tool()` 和 `@mcp.resource()`。为什么 schema 用 Resource 而不是再写一个 Tool？从"读写分离"和"协议语义"两个角度解释。

---

## 6. 断线重连：谁的责任？

`RookieDBConnection` 里有 `_reconnect()` 逻辑。如果把这个重连逻辑放在 `11_agent_mcp_rookiedb.py` 的 Agent 端会有什么问题？跟 MCP 的分层设计有什么关系？

---

## 7. 对比 06 和 11

`06_error_handling.py`（Agent 直连 rookieDB）和 `11_agent_mcp_rookiedb.py`（Agent 通过 MCP 连 rookieDB），如果 rookieDB 挂了重启，两边的处理有什么区别？哪个更容易加监控/限流/审计？为什么？
