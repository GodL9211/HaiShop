"""
测试环境配置文件。
包含测试环境特定的Django配置。
"""
import os
from pathlib import Path
from .base import *
from .env import *

# 测试环境禁用调试模式
DEBUG = False

# 使用内存数据库加速测试
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': ':memory:',
    }
}

# 禁用缓存加速测试
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.dummy.DummyCache',
    }
}

# 禁用密码哈希加速测试
PASSWORD_HASHERS = [
    'django.contrib.auth.hashers.MD5PasswordHasher',
]

# 简化日志配置
LOGGING = {
    'version': 1,
    'disable_existing_loggers': True,
    'handlers': {
        'console': {
            'level': 'ERROR',
            'class': 'logging.StreamHandler',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['console'],
            'level': 'ERROR',
            'propagate': False,
        },
        'products': {
            'handlers': ['console'],
            'level': 'ERROR',
            'propagate': False,
        },
    },
}

# 测试环境特定的DRF配置
REST_FRAMEWORK['DEFAULT_RENDERER_CLASSES'] = [
    'rest_framework.renderers.JSONRenderer',
]
REST_FRAMEWORK['TEST_REQUEST_DEFAULT_FORMAT'] = 'json'

# 商品模块测试环境配置
PRODUCT_SETTINGS = {
    'IMAGE_PATH': 'media/test/products/',
    'CACHE_TIMEOUT': 0,  # 禁用缓存
    'RELATED_PRODUCTS_LIMIT': 5,
    'ENABLE_DRAFT_PRODUCTS': True,  # 测试环境可以查看草稿商品
} 