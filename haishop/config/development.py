"""
开发环境配置文件。
包含开发环境特定的Django配置。
"""
import os
from pathlib import Path
from .base import *
from .env import *

# 开发环境默认开启调试模式
DEBUG = True

# 安全配置 - 开发环境禁用HTTPS相关设置
SECURE_SSL_REDIRECT = False
SECURE_PROXY_SSL_HEADER = None
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False
SECURE_HSTS_SECONDS = 0
SECURE_HSTS_INCLUDE_SUBDOMAINS = False
SECURE_HSTS_PRELOAD = False

# 数据库配置
DATABASES = {
    'default': {
        'ENGINE': DB_ENGINE,
        'NAME': DB_NAME,
        'USER': DB_USER,
        'PASSWORD': DB_PASSWORD,
        'HOST': DB_HOST,
        'PORT': DB_PORT,
        'OPTIONS': {
            'charset': 'utf8mb4',
            'use_unicode': True,
        },
    }
}

# Redis缓存配置
CACHES = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': REDIS_URL,
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
            'PARSER_CLASS': 'redis.connection._HiredisParser',
            'CONNECTION_POOL_KWARGS': {'max_connections': REDIS_MAX_CONNECTIONS},
            'PASSWORD': REDIS_PASSWORD,
        },
        'KEY_PREFIX': REDIS_KEY_PREFIX,
    }
}

# 日志配置 - 开发环境更详细的日志
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
        'simple': {
            'format': '{levelname} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'level': 'DEBUG',
            'class': 'logging.StreamHandler',
            'formatter': 'verbose'
        },
        'file': {
            'level': 'INFO',
            'class': 'logging.FileHandler',
            'filename': os.path.join(BASE_DIR, 'logs/django.log'),
            'formatter': 'verbose',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['console', 'file'],
            'level': 'INFO',
            'propagate': True,
        },
        'products': {
            'handlers': ['console', 'file'],
            'level': 'DEBUG',  # 开发环境使用DEBUG级别
            'propagate': False,
        },
    },
}

# 确保日志目录存在
os.makedirs(os.path.join(BASE_DIR, 'logs'), exist_ok=True)

# 开发环境特定的DRF配置
REST_FRAMEWORK['DEFAULT_RENDERER_CLASSES'] = [
    'rest_framework.renderers.JSONRenderer',
    'rest_framework.renderers.BrowsableAPIRenderer',  # 保留浏览器API渲染器
]

# 商品模块开发环境配置
PRODUCT_SETTINGS = {
    'IMAGE_PATH': PRODUCT_IMAGE_PATH,
    'CACHE_TIMEOUT': PRODUCT_CACHE_TIMEOUT,
    'RELATED_PRODUCTS_LIMIT': RELATED_PRODUCTS_LIMIT,
    'ENABLE_DRAFT_PRODUCTS': True,  # 开发环境可以查看草稿商品
} 