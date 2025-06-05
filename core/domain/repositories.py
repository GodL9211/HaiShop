"""
仓储接口模块。
定义仓储接口，用于持久化和检索领域对象。
"""
from abc import ABC, abstractmethod
from typing import Any, Dict, Generic, List, Optional, Tuple, TypeVar

T = TypeVar('T')


class Repository(Generic[T], ABC):
    """
    仓储接口。
    定义了所有仓储必须实现的基本操作。
    """
    
    @abstractmethod
    def get_by_id(self, id: Any) -> Optional[T]:
        """
        根据ID获取实体。
        
        Args:
            id: 实体ID
            
        Returns:
            找到的实体，如果不存在则返回None
        """
        pass
    
    @abstractmethod
    def save(self, entity: T) -> T:
        """
        保存实体。
        如果实体已存在则更新，否则创建。
        
        Args:
            entity: 要保存的实体
            
        Returns:
            保存后的实体
        """
        pass
    
    @abstractmethod
    def delete(self, entity: T) -> None:
        """
        删除实体。
        
        Args:
            entity: 要删除的实体
        """
        pass


class ReadOnlyRepository(Generic[T], ABC):
    """
    只读仓储接口。
    定义了只读仓储必须实现的基本操作。
    适用于CQRS架构中的查询端。
    """
    
    @abstractmethod
    def get_by_id(self, id: Any) -> Optional[T]:
        """
        根据ID获取实体。
        
        Args:
            id: 实体ID
            
        Returns:
            找到的实体，如果不存在则返回None
        """
        pass
    
    @abstractmethod
    def list(self, skip: int = 0, limit: int = 100) -> List[T]:
        """
        获取实体列表。
        
        Args:
            skip: 跳过的记录数
            limit: 返回的最大记录数
            
        Returns:
            实体列表
        """
        pass


class SearchableRepository(ReadOnlyRepository[T], ABC):
    """
    可搜索仓储接口。
    扩展只读仓储，添加搜索功能。
    """
    
    @abstractmethod
    def search(
        self, 
        keyword: str, 
        filters: Optional[Dict[str, Any]] = None,
        page: int = 1,
        page_size: int = 20
    ) -> Tuple[List[T], int]:
        """
        搜索实体。
        
        Args:
            keyword: 搜索关键词
            filters: 过滤条件
            page: 页码，从1开始
            page_size: 每页大小
            
        Returns:
            匹配的实体列表和总数的元组
        """
        pass
