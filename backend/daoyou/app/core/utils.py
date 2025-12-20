"""
工具函数模块

提供各种工具函数，包括历史文件处理等。
"""

import os
import logging

logger = logging.getLogger(__name__)

def get_abs_history_path(history_path: str) -> str:
    """获取历史文件的绝对路径
    
    Args:
        history_path: 相对路径，如 'cache/13800138000/bazi/history/{cache_key}'
        
    Returns:
        绝对路径，如 '/path/to/app/cache/13800138000/bazi/history/{cache_key}'
    """
    try:
        # 以 app 目录为基准
        app_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        abs_path = os.path.join(app_dir, history_path)
        return abs_path
    except Exception as e:
        logger.error(f"获取历史文件绝对路径失败: {str(e)}", exc_info=True)
        raise 