from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from dotenv import load_dotenv
import os
import sys

# 获取当前目录
current_dir = os.path.dirname(os.path.abspath(__file__))
# 获取上一级目录
parent_dir = os.path.dirname(current_dir)
# 将目录加到python路径
sys.path.append(parent_dir)

from  _main import create_deepseek_client, build_ai_chat_workflow
from config import AIChatState
from log import logger

state: AIChatState = {
    "current_step": "",
    "error": [],
    "node_history": [],

    "user_input": None,
    "ai_response": None,
    "conversation_topic": None,
    "ai_model": "deepseek-chat",
    "ai_usage": [],

    "conversation_history": [],
    "memory_tokens": 0,
    "max_memory_tokens": 102400,

    "tool_use": False,
    "tool_usage": [],
    "tool_results": [],

    'summary': None
}

# 加载.env到当前进行的环境变量里
load_dotenv()

# 创建deepseek客户端
deepseek = create_deepseek_client()

# 构建工作流
graph = build_ai_chat_workflow(deepseek)

# 创建应用
app = FastAPI()

# 请求模型
class ChatRequest(BaseModel):
    user_input: str

# 回应模型
class ChatResponse(BaseModel):
    ai_reply: str


# 发送请求
@app.post('/AIchat/', response_model=ChatResponse)  # 当有人向 http://你的服务器/chat 发送 POST 请求时，执行下面的函数
async def run_workflow(request: ChatRequest):
    try:
        logger.info(f'收到请求')
        state['user_input'] = request.user_input
        result = graph.invoke(state)

        return ChatResponse(
            ai_reply=result['ai_response']
        )
    except Exception as e:
        logger.error(f"处理请求时出错: {e}")
        raise HTTPException(status_code=500, detail="内部服务器错误")



