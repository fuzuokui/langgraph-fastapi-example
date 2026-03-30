# ai结点部分
from functools import wraps
from config import *
from openai import OpenAI
from log import logger
import time

# 定义ai结点装饰器
def ai_node_monitor(func):
    @wraps(func)
    def wrapper(state: AIChatState, client: OpenAI) -> AIChatState:
        node_name = func.__name__
        logger.info(f'AI结点开始：{node_name}')

        # 记录开始时间
        start_time = time.time()

        try:
            # 更新结点历史
            state['node_history'].append(node_name)
            state['current_step'] = node_name

            # 执行AI结点函数
            result_state = func(state, client)

            # 计算执行时间并记录
            execution_time = time.time() - start_time

            logger.info(f'AI结点完成: {node_name}, 耗时：{execution_time:.2f}s')
            return result_state
        except Exception as e:
            execution_time = time.time() - start_time
            state['error'].append(f'AI结点{node_name}执行出错：{e}')
            logger.error(f'结点{node_name}执行出错：{e}')

            return state

    return wrapper


@ai_node_monitor
def analyze_user_input(state: AIChatState, client: OpenAI) -> AIChatState:
    """分析用户的输入，理解用户想要的输出"""
    logger.info('分析用户输入...')

    user_input = state.get('user_input')
    if not user_input:
        state['error'].append('输入为空')
        return state
    logger.info(f'用户输入：{user_input}')

    # 构建分析提示
    analyze_prompt = f"""
    请分析以下用户的输入，返回JSON格式的分析结果：
    用户输入：“{user_input}
    
    请分析：
    1. 主要意图（intent）：用户想要什么？
    2. 主题分类（topic）：属于什么主题？
    3. 情感倾向（sentiment）：positive/negative/neutral
    4. 紧急程度（urgency）：high/medium/low
    5. 工具(tools)：是否需要调用工具（需要已明确工具需要的参数才可调用）
    提示:目前你可以使用3个工具，以下是每种工具的应传入的参数格式（均为字典格式）：
        1、查询天气信息"get_weather": {{'city'：查询的城市或地区, 'data': 查询的日期}}, 例如："get_weather": {{'city'：'beijing', 'data': '2026-03-30'}}
        2、翻译文本"translate_to_chinese": {{'text'：要翻译的文本}}
        3、时间工具：获取当前时间"get_current_time": {{}}无需参数
    
    返回格式：
    {{
        "intent": "描述用户意图",
        "topic": "technology/English/Chinese/business/creative/emotion/history/general", 
        "sentiment": "positive/negative/neutral",
        "urgency": "high/medium/low",
        "tool_use": True/False,
        "tool_usage": [none/{{工具名: [需要传入的参数列表]}}/...](这是一个列表,里面存放工具及其参数的字典)
        ""
    }}
    """

    try:
        system_prompt = "你是一个非常专业的文本分析助手"
        # 加入上下文
        if state['conversation_history'] != []:
            system_prompt += f'以下是历史对话:{state["conversation_history"]}'

        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": analyze_prompt}
            ],
            temperature=0.2,
            response_format={"type": "json_object"}
        )
        """
        temperature
        作用：控制生成文本的随机性/创造性
        范围：0.0 到 2.0
        具体含义：
            低温度 (0.0-0.3)：更确定、一致的回答，适合事实性任务
            中温度 (0.4-0.7)：平衡创造性和一致性，适合一般对话
            高温度 (0.8-2.0)：更有创造性、随机性，适合创意写作
        """

        # 解析分析结果
        analysis_result = response.choices[0].message.content.replace('\n\n', '\n\t').replace('\n', '\n\t').replace('\t\t', '\t')

        import json
        analysis_data = json.loads(analysis_result)

        # 更新状态
        state['conversation_topic'] = analysis_data.get('topic', 'general')
        state['ai_usage'].append({
            "prompt_tokens": response.usage.prompt_tokens,
            "completion_tokens": response.usage.completion_tokens,
            "total_tokens": response.usage.total_tokens
        })

        state['tool_use'] = analysis_data.get('tool_use', False)
        state['tool_usage'] = analysis_data.get('tool_usage', 'none')

        logger.info(f'用户输入分析完成：{analysis_data}')
    except Exception as e:
        logger.error(f'用户输入分析失败：{e}')
        state['error'].append(f'分析失败,{e}')

    return state


@ai_node_monitor
def generate_ai_response(state: AIChatState, client: OpenAI) -> AIChatState:
    logger.info(f'生成ai回复...')

    user_input = state.get('user_input')
    conversation_topic = state.get('conversation_topic', 'general')

    if not user_input:
        state["error"].append("无法生成回复：用户输入为空")
        return state


    topic_prompts = {
        'technology': '你是一名技术工程师，精通各领域的技术问题',
        "English": "你是一名英语老师，精通英语语法、词汇、应用及中英文的翻译",
        "Chinese": "你是一名语文老师，精通古诗词，擅长写作。",
        "business": "你是一个商业顾问，提供专业的商业建议和分析。",
        "creative": "你是一个创意助手，擅长头脑风暴和创造性思考。",
        "emotion": "你是一个情感专家，擅长帮助人们解决生活情感中的问题",
        "history": "你是一个历史学家，精通中国历史和世界历史",
        "general": "你是一个有帮助的AI助手，提供准确、有用的信息。"
    }

    tool_prompts = {
        'get_weather': "查询天气的结果",
        "translate_to_chinese": "翻译的结果",
        "get_current_time": "查询的当前时间",
    }

    system_prompt = topic_prompts.get(conversation_topic, topic_prompts['general'])

    if state['tool_use']:
        tool_results = []
        for i in state['tool_results']:
            tool_results.append({tool_prompts[list(i.keys())[0]]: list(i.values())[0]})
        system_prompt += f',下面是你调用工具的调用结果:{tool_results}'

    # 加入上下文
    if state['conversation_history'] != []:
        system_prompt += f',以下是历史对话:{state["conversation_history"]}(注意,输出结果少用或不用*号,并且不要说根据对话记录)'

    # 加入可用工具
    system_prompt += f',以下是可用工具:{tool_prompts}(注意,输出结果少用或不用*号,并且不要说根据工具调用结果)'
    logger.info(f'topic:{conversation_topic}, 系统提示：{system_prompt}')
    try:
        response = client.chat.completions.create(
            model='deepseek-chat',
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_input}
            ],
            temperature=0.7,
            max_tokens=1024,
            stream=True,
        )

        # 收集完整回复
        ai_response = ""

        # 流式回复
        print('🤖AI:', end='')
        for chunk in response:
            # 检查chunk是否有choices
            if chunk.choices and len(chunk.choices) > 0:
                delta = chunk.choices[0].delta

                # 检查delta是否有content
                if hasattr(delta, 'content') and delta.content:
                    content = delta.content.replace('\n\n', '\n')
                    print(content, end="", flush=True)

                    ai_response += content
            else:
                # 有些chunk可能没有内容，是正常的
                continue
            # time.sleep(0.2)  # 模拟打字效果
        print()  # 最后加个换行

        # 记录历史对话
        logger.info('记录对话:{},{}'.format({"role": "user", "content": user_input}, {"role": "assistant", "content": ai_response}))
        state['conversation_history'].append({"role": "user", "content": user_input})
        state['conversation_history'].append({"role": "assistant", "content": ai_response})

        # 计算token
        prompt_tokens = count_tokens(state, user_input) + count_tokens(state, system_prompt) + 2
        completion_tokens = count_tokens(state, ai_response) + 2
        total_tokens = completion_tokens + prompt_tokens

        # 更新状态
        state['ai_response'] = ai_response
        state['ai_model'] = 'deepseek-chat'
        state['ai_usage'].append({
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": total_tokens,
        })

        logger.info(f'AI回复：{ai_response}')

        logger.info(f"AI回复成功，长度{len(ai_response)}字符")

    except Exception as e:
        logger.error(f"AI回复失败：{e}")
        state["error"].append(f"AI回复失败：{e}")

    return state






