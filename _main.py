# 主函数部分
from langgraph.graph import StateGraph, END
from dotenv import load_dotenv
from base_node import *
from ai_node import *
from tools import *
from log import logger

# 搭建图
def build_ai_chat_workflow(client: OpenAI):
    logger.info('搭建AI工作流')

    builder = StateGraph(AIChatState)

    # 添加结点
    builder.add_node('start', lambda state:start_node(state))
    builder.add_node('analyze_input', lambda state:analyze_user_input(state, client))
    builder.add_node('call_tool', lambda state:call_tool(state))
    builder.add_node('generate_response', lambda state:generate_ai_response(state, client))
    builder.add_node('end', lambda state:end_node(state))

    # 设置工作流
    builder.set_entry_point('start')
    builder.add_edge('start', 'analyze_input')
    builder.add_conditional_edges(  # 分支结点
        'analyze_input',
        need_tool,
        {
            'need': 'call_tool',
            'no_need': 'generate_response'
        }
    )
    builder.add_edge('call_tool', 'generate_response')
    builder.add_edge('generate_response', 'end')
    builder.add_edge('end', END)

    logger.info('ai工作流构建完成')

    return builder.compile()


# 创建交互式界面
def create_interactive_interface():

    # 创建deepseek客户端
    deepseek = create_deepseek_client()

    # 构建工作流
    graph = build_ai_chat_workflow(deepseek)

    mermaid_code = graph.get_graph().draw_mermaid()
    with open('workflow/workflow.mermaid', 'w', encoding='utf-8')as f:
        f.write(mermaid_code)
    # print('mermaid代码已保存到workflow.mermaid')

    # try:
    #     print("\n3. 尝试生成图片...")
    #     # 这需要安装 graphviz: pip install graphviz
    #     png_data = graph.get_graph().draw_mermaid_png()
    #     with open("graph.png", "wb") as f:
    #         f.write(png_data)
    #     print("图片已保存到 graph.png")
    # except Exception as e:
    #     print(f"无法生成图片: {e}")
    #     print("请安装 graphviz: pip install graphviz")

    # 定义初始数据状态
    current_state: AIChatState = {
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

    # 创建历史对话管理器
    memory = MemoryConfig(current_state, deepseek)

    conversation_round = 0
    print("-" * 52)
    print("输入 'quit' 退出, 'show' 显示历史对话, 'clear' 清除历史对话")
    print("-" * 52)
    print('🤖嗨~~ 我是deepseek')
    while True:
        try:
            # 获取用户输入
            user_input = input(f'\n[{conversation_round}]You:').strip()

            if user_input == 'quit':
                logger.info('用户输入：quit 退出')
                print('👋再见 bye~')
                break
            elif user_input == 'show':
                logger.info('用户输入：show 显示历史对话')
                print('以下是历史对话：\n{')
                for i in current_state['conversation_history']:
                    print(f" {i['role']}: {i['content']}")
                print('}', end='')
                continue
            elif user_input == 'clear':
                logger.info('用户输入：clear 清除历史对话')
                current_state['conversation_history'] = []
                print('已清除历史对话')
                continue
            elif not user_input:
                logger.info('用户输入为空')
                print("⚠️ 输入不能为空")
                continue

            # 更新状态
            current_state['user_input'] = user_input

            print("⏳ 思考中...")

            # 执行工作流
            start_time = time.time()
            result_state = graph.invoke(current_state)
            end_time = time.time()


            if result_state.get('error'):
                print('错误：', result_state['error'])
            else:
                # 计算token数是否有超出
                memory.calculate_total_tokens(result_state)

                # 显示元信息
                print('-'*20)
                print('总token使用{}'.format(result_state['summary']['total_tokens']))
                print(f'思考用时{end_time - start_time:.2f}s')

            # 更新状态
            current_state = result_state
            conversation_round += 1

        except KeyboardInterrupt:
            logger.info('用户中断')
            print('用户中断  👋再见 bye~')
            break
        except Exception as e:
            logger.error(f"❌ 发生错误: {e}")
            print(f"❌ 发生错误: {e}")


# 主函数
def main():
    print("=" * 50)
    try:
        create_interactive_interface()

    except Exception as e:
        print(f"❌ 初始化失败: {e}")
        print("\n请确保：")
        print("1. 已设置 DEEPSEEK_API_KEY 环境变量")
        print("2. 已安装 openai 库: pip install openai")
        print("3. 网络连接正常")



if __name__ == "__main__":
    # 加载.env到当前进行的环境变量里
    load_dotenv()

    main()












