# 工具函数
from config import *
from functools import wraps
import requests
import hashlib
import hmac
import json
from log import logger
import datetime
import time
from typing import Dict, Any


# 工具函数装饰器
def tool_monitor(func):
    @wraps(func)
    def wrapper(state: AIChatState, args) -> Dict:
        logger.info(f'tool_monitor调用工具{func.__name__}')
        try:
            logger.info(f'tool_monitor传入参数{args}')
            # 调用工具函数
            result = func(state, args)


            state['current_step'] = func.__name__
            return result

        except Exception as e:
            logger.error(f'工具{func.__name__}调用失败：{e}')
            state['error'].append(f'工具{func.__name__}调用失败：{e}')
            logger.error(f'工具{func.__name__}调用失败')

    return  wrapper


@tool_monitor
# 天气查询--------------------------------------------------------------------
def get_weather(state: AIChatState, params: Dict) -> Dict:
    logger.info('get_weather params: '+str(params));
    url = f"http://api.weatherapi.com/v1/current.json"

    # 请求参数
    params = {
        'key': os.getenv('WEATHER_API_KEY'),
        'q': params['city']
    }

    response = requests.get(url, params=params).json()
    return {
        '城市': response['location']['name'],
        '国家': response['location']['country'],
        '天气': response['current']['condition']['text'],
        '温度': str(response['current']['temp_c']) + '(摄氏度)',
        '风向': response['current']['wind_dir'],
        '风速': str(response['current']['wind_kph']) + '(公里/小时)',
        '最后更新于': response['current']['last_updated']
        }

# -------------------------------------------------------------------------------------------------

# 翻译工具--------------------------------------------------------------------------------------------
# 腾讯翻译API配置信息
class Translate_config():
    def __init__(self):
        self.SECRET_ID = os.getenv('SECRET_ID')
        self.SECRET_KEY = os.getenv('SECRET_KEY')
        self.REGION = 'ap-guangzhou'
        self.ENDPOINT = 'tmt.tencentcloudapi.com'
        self.SERVICE = 'tmt'
        self.VERSION = '2018-03-21'
        self.ACTION = 'TextTranslate'


def sign_request(secret_id, secret_key, method, endpoint, uri, params, co):
    timestamp = int(time.time())
    date = time.strftime('%Y-%m-%d', time.gmtime(timestamp))
    # 1. Build Canonical Request String
    http_request_method = method
    canonical_uri = uri
    canonical_querystring = ''
    canonical_headers = f'content-type:application/json\nhost:{endpoint}\n'
    signed_headers = 'content-type;host'
    payload_hash = hashlib.sha256(json.dumps(params).encode('utf-8')).hexdigest()
    canonical_request = (http_request_method + '\n' +
                         canonical_uri + '\n' +
                         canonical_querystring + '\n' +
                         canonical_headers + '\n' +
                         signed_headers + '\n' +
                         payload_hash)

    # 2. Build String to Sign
    algorithm = 'TC3-HMAC-SHA256'
    credential_scope = f"{date}/{co.SERVICE}/tc3_request"
    string_to_sign = (algorithm + '\n' +
                      str(timestamp) + '\n' +
                      credential_scope + '\n' +
                      hashlib.sha256(canonical_request.encode('utf-8')).hexdigest())

    # 3. Sign String
    def sign(key, msg):
        return hmac.new(key, msg.encode('utf-8'), hashlib.sha256).digest()

    secret_date = sign(('TC3' + secret_key).encode('utf-8'), date)
    secret_service = sign(secret_date, co.SERVICE)
    secret_signing = sign(secret_service, 'tc3_request')
    signature = hmac.new(secret_signing, string_to_sign.encode('utf-8'), hashlib.sha256).hexdigest()


    # 4. Build Authorization Header
    authorization = (f"{algorithm} "
                     f"Credential={secret_id}/{credential_scope}, "
                     f"SignedHeaders={signed_headers}, "
                     f"Signature={signature}")

    return authorization, timestamp

@tool_monitor
def translate_to_chinese(state: AIChatState, text: Dict) -> str:
    co = Translate_config()
    try:
        params = {
            "SourceText": text['text'],
            "Source": "en",
            "Target": "zh",
            "ProjectId": 0
        }

        method = 'POST'
        uri = '/'
        authorization, timestamp = sign_request(co.SECRET_ID, co.SECRET_KEY, method, co.ENDPOINT, uri, params, co)

        headers = {
            'Content-Type': 'application/json',
            'Host': co.ENDPOINT,
            'X-TC-Action': co.ACTION,
            'X-TC-Timestamp': str(timestamp),
            'X-TC-Version': co.VERSION,
            'X-TC-Region': co.REGION,
            'Authorization': authorization
        }

        response = requests.post(f'https://{co.ENDPOINT}{uri}', headers=headers, data=json.dumps(params))
        result = response.json()

        if 'Response' in result and 'TargetText' in result['Response']:
            return result['Response']['TargetText']
        else:
            logger.info(f"翻译API响应错误: {result}")
            return text['text']  # 如果翻译失败，返回原文
    except Exception as e:
        logger.error(f"翻译API请求错误: {e}")

# -------------------------------------------------------------------------------------------------

# 时间工具-------------------------------------------------------------------------------------------
@tool_monitor
def get_current_time(state: AIChatState, arg) -> Dict[str, Any]:
    """获取当前时间和日期"""
    now = datetime.datetime.now()
    return {
        "current_time": now.strftime("%H:%M:%S"),
        "current_date": now.strftime("%Y-%m-%d"),
        "weekday": ["周一", "周二", "周三", "周四", "周五", "周六", "周日"][now.weekday()],
        "timestamp": time.time()
    }
# -------------------------------------------------------------------------------------------------



# 判断是否需要调用工具结点
def need_tool(state: AIChatState) -> str:
    logger.info(f'工具结点，判断是否需要调用工具')
    if state['tool_use']:
        logger.info(f'工具结点，需要调用工具')
        return 'need'
    logger.info(f'工具结点，不需要调用工具')
    return 'no_need'


# 调用工具结点
def call_tool(state: AIChatState) -> AIChatState:
    # 工具函数列表
    tools_list = {
        'get_weather': get_weather,
        'translate_to_chinese': translate_to_chinese,
        'get_current_time': get_current_time,
    }

    logger.info(f'call_tool调用工具{state["tool_usage"]}')

    # 清空之前工具的调用结果
    state['tool_results'] = []
    try:
        # 调用工具
        for tool_para in state['tool_usage']:
            name = list(tool_para.keys())[0]  # 获得工具名
            param = tool_para[name]  # 获得参数字典

            # 调用对应工具并传入参数
            result = tools_list[name](state, param)

            logger.info(f'工具{name}调用完成')

            # 更新状态，保存调用结果
            state['current_step'] = 'call_tool'
            state['node_history'].append('call_tool')
            state['tool_results'].append({name: result})

    except Exception as e:
        logger.error(f'调用工具失败：{e}')
        state['error'].append(f'调用工具失败：{e}')

    return state




