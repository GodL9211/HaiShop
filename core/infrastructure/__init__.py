"""
基础设施层包。
提供事务管理、缓存服务等基础设施组件。
"""

# 事务管理
from core.infrastructure.transaction import (
    TransactionManager,
    DjangoTransactionManager,
    NoOpTransactionManager
)

# 缓存服务
from core.infrastructure.cache import (
    CacheService,
    RedisCacheService,
    MemoryCacheService,
    NoCacheService
)

__all__ = [
    # 事务管理
    'TransactionManager',
    'DjangoTransactionManager',
    'NoOpTransactionManager',
    
    # 缓存服务
    'CacheService',
    'RedisCacheService',
    'MemoryCacheService',
    'NoCacheService',
] 