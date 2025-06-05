"""
缓存服务模块。
提供缓存服务的接口和实现。
"""
from abc import ABC, abstractmethod
import pickle
from typing import Any, Dict, Optional, List, Pattern
import re
import time
from cachetools import TTLCache
from loguru import logger
import redis


class CacheService(ABC):
    """
    缓存服务接口。
    定义缓存操作的抽象方法。
    """
    
    @abstractmethod
    def get(self, key: str) -> Optional[Any]:
        """
        从缓存中获取值。
        
        Args:
            key: 缓存键
            
        Returns:
            缓存值，如果不存在则返回None
        """
        pass
    
    @abstractmethod
    def set(self, key: str, value: Any, ttl: int = 300) -> bool:
        """
        将值存入缓存。
        
        Args:
            key: 缓存键
            value: 要缓存的值
            ttl: 过期时间（秒）
            
        Returns:
            是否成功
        """
        pass
    
    @abstractmethod
    def delete(self, key: str) -> bool:
        """
        从缓存中删除键。
        
        Args:
            key: 缓存键
            
        Returns:
            是否成功
        """
        pass
    
    @abstractmethod
    def delete_pattern(self, pattern: str) -> int:
        """
        删除匹配模式的所有键。
        
        Args:
            pattern: 键模式
            
        Returns:
            删除的键数量
        """
        pass
    
    @abstractmethod
    def exists(self, key: str) -> bool:
        """
        检查键是否存在。
        
        Args:
            key: 缓存键
            
        Returns:
            是否存在
        """
        pass
    
    @abstractmethod
    def clear(self) -> bool:
        """
        清空缓存。
        
        Returns:
            是否成功
        """
        pass


class RedisCacheService(CacheService):
    """
    基于Redis的缓存服务实现。
    使用Redis作为缓存存储。
    """
    
    def __init__(
        self,
        redis_client: redis.Redis,
        key_prefix: str = "haishop:",
        local_cache_size: int = 1000,
        local_cache_ttl: int = 60
    ):
        """
        初始化Redis缓存服务。
        
        Args:
            redis_client: Redis客户端
            key_prefix: 键前缀
            local_cache_size: 本地缓存大小
            local_cache_ttl: 本地缓存TTL（秒）
        """
        self.redis_client = redis_client
        self.key_prefix = key_prefix
        self.local_cache = TTLCache(maxsize=local_cache_size, ttl=local_cache_ttl)
    
    def _get_full_key(self, key: str) -> str:
        """
        获取带前缀的完整键名。
        
        Args:
            key: 原始键
            
        Returns:
            带前缀的完整键
        """
        return f"{self.key_prefix}{key}"
    
    def get(self, key: str) -> Optional[Any]:
        """
        从缓存中获取值。
        先从本地缓存获取，如果不存在则从Redis获取。
        
        Args:
            key: 缓存键
            
        Returns:
            缓存值，如果不存在则返回None
        """
        # 先检查本地缓存
        if key in self.local_cache:
            logger.debug(f"本地缓存命中: {key}")
            return self.local_cache[key]
        
        # 再检查Redis缓存
        full_key = self._get_full_key(key)
        try:
            value = self.redis_client.get(full_key)
            if value:
                # 反序列化
                result = pickle.loads(value)
                # 更新本地缓存
                self.local_cache[key] = result
                logger.debug(f"Redis缓存命中: {key}")
                return result
        except (redis.RedisError, pickle.PickleError) as e:
            logger.error(f"Redis缓存读取错误: {e}")
        
        logger.debug(f"缓存未命中: {key}")
        return None
    
    def set(self, key: str, value: Any, ttl: int = 300) -> bool:
        """
        将值存入缓存。
        同时更新本地缓存和Redis缓存。
        
        Args:
            key: 缓存键
            value: 要缓存的值
            ttl: 过期时间（秒）
            
        Returns:
            是否成功
        """
        # 更新本地缓存
        self.local_cache[key] = value
        
        # 更新Redis缓存
        full_key = self._get_full_key(key)
        try:
            # 序列化
            serialized = pickle.dumps(value)
            result = self.redis_client.setex(full_key, ttl, serialized)
            logger.debug(f"缓存已设置: {key}, TTL: {ttl}秒")
            return result
        except (redis.RedisError, pickle.PickleError) as e:
            logger.error(f"Redis缓存写入错误: {e}")
            return False
    
    def delete(self, key: str) -> bool:
        """
        从缓存中删除键。
        同时从本地缓存和Redis缓存中删除。
        
        Args:
            key: 缓存键
            
        Returns:
            是否成功
        """
        # 从本地缓存删除
        if key in self.local_cache:
            del self.local_cache[key]
        
        # 从Redis缓存删除
        full_key = self._get_full_key(key)
        try:
            result = self.redis_client.delete(full_key)
            logger.debug(f"缓存已删除: {key}")
            return result > 0
        except redis.RedisError as e:
            logger.error(f"Redis缓存删除错误: {e}")
            return False
    
    def delete_pattern(self, pattern: str) -> int:
        """
        删除匹配模式的所有键。
        先从Redis获取匹配的键，然后逐个删除。
        
        Args:
            pattern: 键模式
            
        Returns:
            删除的键数量
        """
        full_pattern = self._get_full_key(pattern) + "*"
        count = 0
        
        try:
            # 获取匹配的键
            keys = self.redis_client.keys(full_pattern)
            if not keys:
                return 0
            
            # 批量删除
            count = self.redis_client.delete(*keys)
            
            # 从本地缓存删除匹配的键
            pattern_regex = pattern.replace("*", ".*")
            local_keys = [k for k in self.local_cache.keys() 
                        if re.match(pattern_regex, k)]
            
            for k in local_keys:
                del self.local_cache[k]
            
            logger.debug(f"已删除匹配模式 {pattern} 的 {count} 个键")
            return count
        except redis.RedisError as e:
            logger.error(f"Redis缓存模式删除错误: {e}")
            return 0
    
    def exists(self, key: str) -> bool:
        """
        检查键是否存在。
        先检查本地缓存，再检查Redis缓存。
        
        Args:
            key: 缓存键
            
        Returns:
            是否存在
        """
        # 先检查本地缓存
        if key in self.local_cache:
            return True
        
        # 再检查Redis缓存
        full_key = self._get_full_key(key)
        try:
            return bool(self.redis_client.exists(full_key))
        except redis.RedisError as e:
            logger.error(f"Redis缓存检查错误: {e}")
            return False
    
    def clear(self) -> bool:
        """
        清空缓存。
        清空本地缓存和Redis缓存中带前缀的所有键。
        
        Returns:
            是否成功
        """
        # 清空本地缓存
        self.local_cache.clear()
        
        # 清空Redis缓存中带前缀的所有键
        full_pattern = self._get_full_key("*")
        try:
            keys = self.redis_client.keys(full_pattern)
            if keys:
                self.redis_client.delete(*keys)
            logger.debug(f"缓存已清空, 删除了 {len(keys)} 个键")
            return True
        except redis.RedisError as e:
            logger.error(f"Redis缓存清空错误: {e}")
            return False


class MemoryCacheService(CacheService):
    """
    基于内存的缓存服务实现。
    使用TTLCache实现的纯内存缓存，适用于开发环境和测试。
    """
    
    def __init__(self, maxsize: int = 1000, default_ttl: int = 300):
        """
        初始化内存缓存服务。
        
        Args:
            maxsize: 最大缓存项数
            default_ttl: 默认TTL（秒）
        """
        self.cache = TTLCache(maxsize=maxsize, ttl=default_ttl)
        self.default_ttl = default_ttl
    
    def get(self, key: str) -> Optional[Any]:
        """
        从缓存中获取值。
        
        Args:
            key: 缓存键
            
        Returns:
            缓存值，如果不存在则返回None
        """
        return self.cache.get(key)
    
    def set(self, key: str, value: Any, ttl: int = None) -> bool:
        """
        将值存入缓存。
        
        Args:
            key: 缓存键
            value: 要缓存的值
            ttl: 过期时间（秒）
            
        Returns:
            是否成功
        """
        if ttl is None:
            ttl = self.default_ttl
        
        # 如果TTL与默认值不同，需要更新TTL
        if ttl != self.default_ttl:
            # 保存当前时间
            now = time.time()
            # 计算过期时间
            expires = now + ttl
            # 存储值和过期时间
            self.cache[key] = value
            # 手动设置过期时间
            self.cache.timer.tickers[key] = expires
        else:
            # 使用默认TTL
            self.cache[key] = value
        
        return True
    
    def delete(self, key: str) -> bool:
        """
        从缓存中删除键。
        
        Args:
            key: 缓存键
            
        Returns:
            是否成功
        """
        try:
            if key in self.cache:
                del self.cache[key]
                return True
            return False
        except Exception:
            return False
    
    def delete_pattern(self, pattern: str) -> int:
        """
        删除匹配模式的所有键。
        
        Args:
            pattern: 键模式
            
        Returns:
            删除的键数量
        """
        pattern_regex = pattern.replace("*", ".*")
        r = re.compile(pattern_regex)
        keys_to_delete = [k for k in self.cache.keys() if r.match(k)]
        
        count = 0
        for key in keys_to_delete:
            if self.delete(key):
                count += 1
        
        return count
    
    def exists(self, key: str) -> bool:
        """
        检查键是否存在。
        
        Args:
            key: 缓存键
            
        Returns:
            是否存在
        """
        return key in self.cache
    
    def clear(self) -> bool:
        """
        清空缓存。
        
        Returns:
            是否成功
        """
        self.cache.clear()
        return True


class NoCacheService(CacheService):
    """
    空缓存服务实现。
    不进行实际缓存，适用于禁用缓存的场景。
    """
    
    def get(self, key: str) -> Optional[Any]:
        """
        从缓存中获取值，总是返回None。
        
        Args:
            key: 缓存键
            
        Returns:
            总是返回None
        """
        return None
    
    def set(self, key: str, value: Any, ttl: int = 300) -> bool:
        """
        将值存入缓存，但实际上不做任何操作。
        
        Args:
            key: 缓存键
            value: 要缓存的值
            ttl: 过期时间（秒）
            
        Returns:
            总是返回True
        """
        return True
    
    def delete(self, key: str) -> bool:
        """
        从缓存中删除键，但实际上不做任何操作。
        
        Args:
            key: 缓存键
            
        Returns:
            总是返回True
        """
        return True
    
    def delete_pattern(self, pattern: str) -> int:
        """
        删除匹配模式的所有键，但实际上不做任何操作。
        
        Args:
            pattern: 键模式
            
        Returns:
            总是返回0
        """
        return 0
    
    def exists(self, key: str) -> bool:
        """
        检查键是否存在，总是返回False。
        
        Args:
            key: 缓存键
            
        Returns:
            总是返回False
        """
        return False
    
    def clear(self) -> bool:
        """
        清空缓存，但实际上不做任何操作。
        
        Returns:
            总是返回True
        """
        return True 