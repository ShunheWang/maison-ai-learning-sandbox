"""
12_orchestrator_worker.py — Orchestrator-Worker 编排模式

学习点：
  - Orchestrator-Worker 模式：一个 Leader 拆任务，多个 Worker 各司其职
  - Prompt Chaining：Orchestrator → Worker A → Worker B 串行流水线
  - 每个 Agent 独立的 client + messages 历史
  - 跟 03_agent_loop.py 对比：单 Agent 循环 vs 多 Agent 编排
  - 不连 rookieDB，纯编排练习

运行方式：
  python3 step3-multi-agent/12_orchestrator_worker.py

Agent 角色：
  Orchestrator — "大脑"，分析请求、拆成子任务、分派给对应 Worker
  Worker A     — "SQL 生成器"，理解子任务 → 生成合法 SQL
  Worker B     — "SQL 审查员"，检查语法/逻辑/安全性 → 通过或修改
"""

import os
import pathlib

# 加载 .env
env_path = pathlib.Path(__file__).parent.parent / ".env"
if env_path.exists():
    with open(env_path) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, _, value = line.partition("=")
                os.environ[key.strip()] = value.strip()

from anthropic import Anthropic

# ============================================================
# 配置
# ============================================================
MODEL = "deepseek-v4-pro"
MAX_TOKENS = 1000

client = Anthropic(
    api_key=os.environ["ANTHROPIC_API_KEY"],
    base_url=os.environ.get("ANTHROPIC_BASE_URL", "https://api.deepseek.com/anthropic"),
)

# ============================================================
# 表结构（Worker 需要知道才能生成正确 SQL）
# ============================================================
DB_SCHEMA = """
数据库表结构（rookieDB）:

Students(sid INT, name VARCHAR, major VARCHAR, gpa REAL)
  - sid: 学号（主键）
  - name: 学生姓名
  - major: 专业（如 CS, Math, Physics）
  - gpa: 绩点

Courses(cid INT, name VARCHAR, department VARCHAR)
  - cid: 课程号（主键）
  - name: 课程名
  - department: 开课院系

Enrollment(sid INT, cid INT, grade VARCHAR, semester VARCHAR)
  - sid: 学号（外键 → Students.sid）
  - cid: 课程号（外键 → Courses.cid）
  - grade: 成绩（A, A-, B+, ...）
  - semester: 学期（如 Fall2024, Spring2025）
"""

# ============================================================
# Prompt 模板
# ============================================================

ORCHESTRATOR_PROMPT = """你是一个任务编排器（Orchestrator）。你会收到用户的自然语言请求，你需要把它拆解成独立的子任务。

数据库结构：
""" + DB_SCHEMA + """

你的职责：
1. 分析用户请求，理解需要什么数据
2. 把请求拆成 1-3 个独立的子任务
3. 输出格式：
   - 如果请求简单，一个子任务就够了，输出：
     TASK: <子任务描述>
   - 如果有多个子任务，输出：
     TASK_1: <子任务1描述>
     TASK_2: <子任务2描述>
     ...
4. 不要生成 SQL，只描述每个子任务需要什么数据

注意：
- 子任务要具体、独立、可执行
- 如果用户请求非常简单（如"列出所有学生"），只输出一个 TASK
- 不要输出多余的内容，严格按照 TASK: 格式"""

SQL_GENERATOR_PROMPT = """你是一个 SQL 生成器。你会收到一个子任务描述，你需要生成一条合法的 SQL 语句。

数据库结构：
""" + DB_SCHEMA + """

你的职责：
1. 理解子任务描述
2. 生成对应的 SELECT 语句
3. 输出格式：
   SQL: <SQL语句>
4. 不要输出多余的内容，不要解释

注意：
- rookieDB 不支持 ORDER BY column DESC，用 ORDER BY -column 代替
- rookieDB 不支持 LIMIT，用其它方式代替
- 只输出一条 SQL，不要多条
- 确保字段名、表名跟上述结构一致"""

SQL_REVIEWER_PROMPT = """你是一个 SQL 审查员。你会收到一条 SQL 语句和它对应的子任务描述，你需要审查这条 SQL。

你的职责：
1. 检查语法是否正确（字段名、表名是否存在）
2. 检查逻辑是否正确（查询条件跟任务描述是否匹配）
3. 检查是否有 rookieDB 不支持的语法（如 ORDER BY ... DESC 要改为 ORDER BY -...）
4. 输出审查结果：
   - 如果通过：PASS
   - 如果需要修改：MODIFY: <修改后的SQL>
5. 只输出 PASS 或 MODIFY:，不要多余内容"""

# ============================================================
# Agent 函数
# ============================================================

def run_orchestrator(user_request: str) -> str:
    """Orchestrator：分析请求 → 拆成子任务"""
    print(f"\n{'─'*60}")
    print(f"🧠 Orchestrator: 分析请求...")
    print(f"{'─'*60}")

    response = client.messages.create(
        model=MODEL,
        max_tokens=MAX_TOKENS,
        system=ORCHESTRATOR_PROMPT,
        messages=[{"role": "user", "content": user_request}],
    )

    result = "".join(
        block.text for block in response.content if block.type == "text"
    )
    print(f"   输入: {user_request}")
    print(f"   输出:\n{result}")
    return result


def run_worker_a(subtask: str) -> str:
    """Worker A: 子任务描述 → SQL"""
    print(f"\n{'─'*60}")
    print(f"🔧 Worker A (SQL 生成器): 生成 SQL...")
    print(f"{'─'*60}")

    response = client.messages.create(
        model=MODEL,
        max_tokens=MAX_TOKENS,
        system=SQL_GENERATOR_PROMPT,
        messages=[{"role": "user", "content": subtask}],
    )

    result = "".join(
        block.text for block in response.content if block.type == "text"
    )
    print(f"   输入: {subtask}")
    print(f"   输出: {result}")
    return result


def run_worker_b(task: str, sql: str) -> str:
    """Worker B: 审查 SQL"""
    print(f"\n{'─'*60}")
    print(f"🔍 Worker B (SQL 审查员): 审查 SQL...")
    print(f"{'─'*60}")

    review_input = f"任务描述: {task}\nSQL: {sql}"

    response = client.messages.create(
        model=MODEL,
        max_tokens=MAX_TOKENS,
        system=SQL_REVIEWER_PROMPT,
        messages=[{"role": "user", "content": review_input}],
    )

    result = "".join(
        block.text for block in response.content if block.type == "text"
    )
    print(f"   输入: {review_input}")
    print(f"   输出: {result}")
    return result


def parse_tasks(orchestrator_output: str) -> list[str]:
    """从 Orchestrator 输出中提取子任务"""
    tasks = []
    for line in orchestrator_output.strip().split("\n"):
        line = line.strip()
        if line.startswith("TASK:") or line.startswith("TASK_"):
            # 移除 TASK_1:, TASK_2: 或 TASK: 前缀
            task = line.split(":", 1)[1].strip() if ":" in line else line
            tasks.append(task)
    return tasks


# ============================================================
# 主流程
# ============================================================

def main():
    print("=" * 60)
    print("🎯 Orchestrator-Worker 编排演示")
    print("=" * 60)
    print()
    print("流程: 用户请求 → Orchestrator 拆任务 → Worker A 生成SQL → Worker B 审查SQL")
    print()

    # 测试用例
    test_cases = [
        {
            "name": "简单请求",
            "request": "列出所有学生的姓名和专业",
        },
        {
            "name": "复杂请求",
            "request": "查出所有 CS 专业且 GPA 高于 3.5 的学生，按成绩从高到低排序",
        },
        {
            "name": "需要拆分的请求",
            "request": "统计每个专业的学生人数，同时找出 GPA 最高的 3 个学生",
        },
    ]

    for i, case in enumerate(test_cases):
        print(f"\n{'='*60}")
        print(f"📋 测试 {i+1}: {case['name']}")
        print(f"{'='*60}")

        # 1. Orchestrator 拆任务
        orchestrator_result = run_orchestrator(case["request"])
        tasks = parse_tasks(orchestrator_result)

        if not tasks:
            print("⚠️  Orchestrator 没有生成有效子任务，跳过")
            continue

        print(f"\n   📦 拆成 {len(tasks)} 个子任务")

        # 2. 对每个子任务: Worker A 生成 SQL → Worker B 审查
        for j, task in enumerate(tasks):
            print(f"\n   --- 子任务 {j+1}: {task} ---")

            # Worker A: 生成 SQL
            sql_result = run_worker_a(task)

            # 从输出中提取 SQL
            sql_line = ""
            for line in sql_result.strip().split("\n"):
                if line.strip().startswith("SQL:"):
                    sql_line = line.split(":", 1)[1].strip() if ":" in line else line.strip()
                    break

            if not sql_line:
                print("   ⚠️  Worker A 没有生成有效 SQL，跳过")
                continue

            # Worker B: 审查 SQL
            review_result = run_worker_b(task, sql_line)

            # 判断审查结果
            if "PASS" in review_result:
                print(f"\n   ✅ 审查通过: {sql_line}")
            elif "MODIFY" in review_result:
                modified = review_result.split(":", 1)[1].strip() if ":" in review_result else review_result
                print(f"\n   🔄 需要修改 → {modified}")
            else:
                print(f"\n   ❓ 审查结果不明: {review_result}")

    print(f"\n{'='*60}")
    print("✅ 所有测试完成")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
