from openai import OpenAI
import os
from typing import TypedDict, List, Dict, Any, Optional
import requests
import tiktoken
from log import logger


# 配置deepseek
class DeepSeekConfig():
    def __init__(self, api_key: str, url: str):
        self.api_key = api_key
        self.base_url = url

        if not self.api_key:
            raise ValueError("OPENAI_API_KEY environment variable not set")

    # 创建deepseek客户端
    def get_client(self):
        return OpenAI(
            api_key=self.api_key,
            base_url=self.base_url
        )


# 创建deepseek客户端
def create_deepseek_client(api_key: str = os.getenv("OPENAI_API_KEY"), url: str = "https://api.deepseek.com"):
    try:
        config = DeepSeekConfig(api_key, url)
        client = config.get_client()
        print('deepseek客户端创建成功')
        return client

    except requests.exceptions.ConnectionError:
        print("❌ 无法连接到deepseek服务器")

    except Exception as e:
        print('deepseek客户端创建失败:', e)
        if "rate limit" in str(e).lower():
            print("⚠️ 达到速率限制，请稍后重试")
        elif "invalid api key" in str(e).lower():
            print("❌ API密钥无效")
        elif "context length" in str(e).lower():
            print("📝 对话过长，请缩短输入")
        else:
            print(f"❌ 未知错误: {e}")
        return None


# 定义数据状态
class AIChatState(TypedDict):
    # 基础状态
    current_step: str
    error: List[str]
    node_history: List[str]

    # AI对话相关状态
    user_input: Optional[str]   # 用户输入
    ai_response: Optional[str]  # AI回复
    conversation_topic: Optional[str]   # 对话主题
    ai_model: str   # 使用的AI模型
    ai_usage: List[Dict[str, int]]  # token使用情况

    # 记忆相关状态
    conversation_history: List[Dict[str, Any]]  # 记录历史对话
    memory_tokens: int  # 当前所用的总token数
    max_memory_tokens: int  # 历史对话的最大token数限制

    # 工具相关状态
    tool_use: bool  # 是否需要使用工具
    tool_usage: Optional[List[Dict[str, Any]]]    # 工具调用列表
    tool_results: List[Dict[str, Any]]    # 工具调用结果

    # 汇总结果
    summary: Optional[Dict[str, Any]]


# 历史对话管理器

# 计算文本token数
def count_tokens(state: AIChatState, text: str):
    try:
        encoding = tiktoken.encoding_for_model(state['ai_model'])
        return len(encoding.encode(text))
    except:
        return len(text) // 4
class MemoryConfig():
    def __init__(self, state: AIChatState, client: OpenAI):
        self.max_memory_tokens = state['max_memory_tokens']
        self.memory_tokens = state['memory_tokens']
        self.client = client

    # # 添加到历史对话
    # def add_message(self, state: AIChatState, role: str, content: str):
    #     message = {
    #         "role": role,
    #         "content": content
    #     }
    #
    #     state['conversation_history'].append(message)

    def calculate_total_tokens(self, state: AIChatState):
        total_tokens = state['memory_tokens']

        logger.info(f'当前总token数{total_tokens}')
        if total_tokens > self.max_memory_tokens:
            print('(token数超出，压缩历史对话)')
            logger.info('token数超出，压缩历史对话')
            # 删除最旧的消息
            message = state['conversation_history'].pop(0)
            total_tokens -= count_tokens(state, message['content'])
            total_tokens -= 1

            logger.info(f'当前总token数{total_tokens}')

        state['memory_tokens'] = total_tokens

    # 获取所有历史对话
    def get_memory(self, state: AIChatState):
        return state['conversation_history']

    # 清空所有历史对话
    def clear_memory(self, state: AIChatState):
        state['conversation_history'] = []




# config = create_deepseek_client()
# response = config.chat.completions.create(
#     model="deepseek-chat",
#     messages=[
#         {"role": "system", "content": "你是一个AI智能助手"},
#         {"role": "user", "content": "请问一台计算机主要由哪几部分构成？"}
#     ],
#     temperature=0.1
#
# )
# print(response.choices[0].message.content)
# usage = response.usage
# print(f"Token使用: 输入={usage.prompt_tokens}, 输出={usage.completion_tokens}, 总计={usage.total_tokens}")
