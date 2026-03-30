import logging
import os

# 获取当前文件的目录
current_dir = os.path.dirname(os.path.abspath(__file__))

# 配置日志
def setup_logging():
    logging.basicConfig(
        level=logging.INFO,  # 设置报告的最低等级
        format="%(asctime)s %(levelname)s %(message)s",  # 设置输出日期，等级和消息
        datefmt="%Y-%m-%d %H:%M:%S",    # 设置输出的时间格式
        handlers=[
            logging.FileHandler(os.path.join(current_dir, "app.log"), mode='w' ,encoding='utf-8'),  # 创建文件处理器，将日志写入文件
            # logging.StreamHandler()  # 创建控制台处理器，将日志输出到控制台
        ]
    )

    return logging.getLogger(__name__)  # 返回一个日志对象

logger = setup_logging()