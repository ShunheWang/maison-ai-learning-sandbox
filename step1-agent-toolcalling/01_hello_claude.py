"""
单元 1.1：Hello World — 跟 Claude 说上话

学习点：
  1. anthropic.Anthropic() 怎么初始化
  2. messages.create() 的参数：model, max_tokens, system, messages
  3. response.content 的结构
"""

import anthropic
import os

# 初始化客户端
# ANTHROPIC_API_KEY 和 ANTHROPIC_BASE_URL 从环境变量读
client = anthropic.Anthropic(
    base_url=os.environ.get("ANTHROPIC_BASE_URL", "https://api.anthropic.com"),
)

# 发第一条消息
response = client.messages.create(
    model="deepseek/deepseek-v4-pro",
    max_tokens=100,
    system="你是一个友好的助手。",
    messages=[
        {"role": "user", "content": "用一句话介绍你自己"}
    ]
)

# 打印回复
print("=" * 50)
print("回复内容：")
for block in response.content:
    if block.type == "thinking":
        print(f"  [思考] {block.thinking[:200]}...")
    elif block.type == "text":
        print(f"  {block.text}")
print("=" * 50)
print(f"模型: {response.model}")
print(f"stop_reason: {response.stop_reason}")
print(f"输入 tokens: {response.usage.input_tokens}")
print(f"输出 tokens: {response.usage.output_tokens}")
