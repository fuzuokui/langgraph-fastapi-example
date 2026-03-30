# 基础结点部分
from config import *
from log import logger

# 开始结点
def start_node(state: AIChatState) ->  AIChatState:
    logger.info('启动ai聊天工作流')
    state['current_step'] = 'start'
    state['node_history'].append('start')
    return state

# 结束结点
def end_node(state: AIChatState) ->  AIChatState:
    logger.info("结束ai聊天工作流")
    state['current_step'] = 'end'

    total_tokens = 0
    for i in state['ai_usage']:
        total_tokens += i['total_tokens']

    # 汇总结果
    summary = {
        'ai_model': state.get('ai_model', 'unknown'),
        'total_tokens': total_tokens
    }

    state['summary'] = summary
    state['memory_tokens'] += summary['total_tokens']

    logger.info(f'工作流完成，{summary}')

    return state

