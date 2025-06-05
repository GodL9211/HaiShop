"""
Django settings for haishop project.

此文件作为配置入口点，根据环境变量加载相应的配置模块。
"""

import os
import sys
from pathlib import Path

# 构建基本路径
BASE_DIR = Path(__file__).resolve().parent.parent

# 确保日志目录存在
os.makedirs(os.path.join(BASE_DIR, 'logs'), exist_ok=True)

# 确定当前环境
DJANGO_ENV = os.environ.get('DJANGO_ENV', 'development')

# 根据环境加载相应的配置
if DJANGO_ENV == 'production':
    from .config.production import *
elif DJANGO_ENV == 'testing':
    from .config.testing import *
else:  # 默认使用开发环境配置
    from .config.development import *

# 打印当前使用的环境配置
print(f"使用{DJANGO_ENV}环境配置")
print(f"{DATABASES}")
