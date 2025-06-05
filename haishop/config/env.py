"""
环境变量处理模块。
负责加载和处理环境变量。
"""
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Union, cast

from dotenv import load_dotenv


# 项目根目录
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# 从当前文件同级目录加载.env文件
def load_env_file():
    """从当前文件同级目录加载.env文件"""
    # .env文件位置
    env_path = os.path.join(os.path.dirname(__file__), '.env')
    
    if os.path.exists(env_path):
        try:
            # 尝试加载.env文件
            print(f"尝试加载环境变量文件: {env_path}")
            load_dotenv(dotenv_path=env_path, encoding='utf-8')
            print(f"成功加载环境变量文件: {env_path}")
            return True
        except Exception as e:
            print(f"加载环境变量文件失败: {e}，将使用默认值")
            return False
    else:
        print(f"环境变量文件不存在: {env_path}，将使用默认值")
        return False

# 尝试加载环境变量
load_env_file()

# 获取环境变量，支持类型转换和默认值
def get_env(name: str, default: Any = None, cast_type: Optional[type] = None) -> Any:
    """
    获取环境变量值，支持类型转换和默认值
    
    Args:
        name: 环境变量名称
        default: 默认值，如果环境变量不存在则返回此值
        cast_type: 类型转换函数，如int, float, bool等
        
    Returns:
        环境变量的值，经过类型转换（如果指定了cast_type）
    """
    value = os.environ.get(name, default)
    
    if value is None:
        return None
    
    if cast_type is not None:
        if cast_type is bool and isinstance(value, str):
            return value.lower() in ('true', 'yes', '1', 'y')
        if cast_type is list and isinstance(value, str):
            return [item.strip() for item in value.split(',') if item.strip()]
        try:
            return cast_type(value)
        except (ValueError, TypeError):
            import warnings
            warnings.warn(f"无法将环境变量{name}的值'{value}'转换为{cast_type.__name__}类型，使用默认值")
            return default
    
    return value


# 导出常用环境变量
DEBUG = get_env('DEBUG', default=True, cast_type=bool)
SECRET_KEY = get_env('SECRET_KEY', default='django-insecure-v%%g938(07j#*8y^l&gaw^d%_a$e#lqb$m0$1q^==2zy1(c2!8')
ALLOWED_HOSTS = get_env('ALLOWED_HOSTS', default='localhost,127.0.0.1', cast_type=list)

# 数据库配置
DB_ENGINE = get_env('DB_ENGINE', default='django.db.backends.mysql')
DB_NAME = get_env('DB_NAME', default='haishop')
DB_USER = get_env('DB_USER', default='root')
DB_PASSWORD = get_env('DB_PASSWORD', default='123456')
DB_HOST = get_env('DB_HOST', default='127.0.0.1')
DB_PORT = get_env('DB_PORT', default='3306')

# Redis配置
REDIS_URL = get_env('REDIS_URL', default='redis://localhost:6379/1')
REDIS_PASSWORD = get_env('REDIS_PASSWORD', default='')
REDIS_MAX_CONNECTIONS = get_env('REDIS_MAX_CONNECTIONS', default=100, cast_type=int)
REDIS_KEY_PREFIX = get_env('REDIS_KEY_PREFIX', default='haishop')

# 国际化配置
LANGUAGE_CODE = get_env('LANGUAGE_CODE', default='zh-hans')
TIME_ZONE = get_env('TIME_ZONE', default='Asia/Shanghai')

# 商品模块配置
PRODUCT_IMAGE_PATH = get_env('PRODUCT_IMAGE_PATH', default='media/products/')
PRODUCT_CACHE_TIMEOUT = get_env('PRODUCT_CACHE_TIMEOUT', default=3600, cast_type=int)
RELATED_PRODUCTS_LIMIT = get_env('RELATED_PRODUCTS_LIMIT', default=5, cast_type=int)