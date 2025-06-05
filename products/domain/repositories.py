"""
商品领域模型中的仓储接口。
定义用于持久化和检索商品实体的仓储接口。
"""
from abc import abstractmethod
from typing import Any, Dict, List, Optional, Tuple

from core.domain.repositories import Repository, SearchableRepository
from products.domain.aggregates import ProductAggregate
from products.domain.entities import Product
from products.domain.value_objects import ProductCategory


class ProductRepository(SearchableRepository[ProductAggregate]):
    """
    商品仓储接口。
    定义用于持久化和检索商品聚合根的方法。
    """
    
    @abstractmethod
    def get_by_id(self, id: Any) -> Optional[ProductAggregate]:
        """
        根据ID获取商品聚合根。
        
        Args:
            id: 商品ID
            
        Returns:
            找到的商品聚合根，如果不存在则返回None
        """
        pass
    
    @abstractmethod
    def save(self, product_aggregate: ProductAggregate) -> ProductAggregate:
        """
        保存商品聚合根。
        
        Args:
            product_aggregate: 要保存的商品聚合根
            
        Returns:
            保存后的商品聚合根
        """
        pass
    
    @abstractmethod
    def delete(self, product_aggregate: ProductAggregate) -> None:
        """
        删除商品聚合根。
        
        Args:
            product_aggregate: 要删除的商品聚合根
        """
        pass
    
    @abstractmethod
    def list(self, skip: int = 0, limit: int = 100) -> List[ProductAggregate]:
        """
        获取商品列表。
        
        Args:
            skip: 跳过的记录数
            limit: 返回的最大记录数
            
        Returns:
            商品聚合根列表
        """
        pass
    
    @abstractmethod
    def search(
        self, 
        keyword: str, 
        filters: Optional[Dict[str, Any]] = None,
        page: int = 1,
        page_size: int = 20,
        include_facets: bool = False,
        facet_fields: Optional[List[str]] = None
    ) -> Tuple[List[ProductAggregate], int, Optional[Dict[str, Any]]]:
        """
        搜索商品。
        
        Args:
            keyword: 搜索关键词
            filters: 过滤条件
            page: 页码
            page_size: 每页大小
            include_facets: 是否包含分面结果
            facet_fields: 需要聚合的分面字段列表
            
        Returns:
            商品聚合根列表、总数和分面结果的元组
        """
        pass
    
    @abstractmethod
    def find_by_category(
        self,
        category_id: Any,
        page: int = 1,
        page_size: int = 20
    ) -> Tuple[List[ProductAggregate], int]:
        """
        按分类查找商品。
        
        Args:
            category_id: 分类ID
            page: 页码
            page_size: 每页大小
            
        Returns:
            商品聚合根列表和总数的元组
        """
        pass
    
    @abstractmethod
    def find_by_keyword(
        self,
        keyword: str,
        page: int = 1,
        page_size: int = 20
    ) -> Tuple[List[ProductAggregate], int]:
        """
        按关键词查找商品。
        
        Args:
            keyword: 关键词
            page: 页码
            page_size: 每页大小
            
        Returns:
            商品聚合根列表和总数的元组
        """
        pass


class CategoryRepository(Repository[ProductCategory]):
    """
    分类仓储接口。
    定义用于持久化和检索商品分类的方法。
    """
    
    @abstractmethod
    def get_by_id(self, id: Any) -> Optional[ProductCategory]:
        """
        根据ID获取分类。
        
        Args:
            id: 分类ID
            
        Returns:
            找到的分类，如果不存在则返回None
        """
        pass
    
    @abstractmethod
    def save(self, category: ProductCategory) -> ProductCategory:
        """
        保存分类。
        
        Args:
            category: 要保存的分类
            
        Returns:
            保存后的分类
        """
        pass
    
    @abstractmethod
    def delete(self, category: ProductCategory) -> None:
        """
        删除分类。
        
        Args:
            category: 要删除的分类
        """
        pass
    
    @abstractmethod
    def get_all(self) -> List[ProductCategory]:
        """
        获取所有分类。
        
        Returns:
            所有分类的列表
        """
        pass
    
    @abstractmethod
    def get_children(self, parent_id: Any) -> List[ProductCategory]:
        """
        获取子分类。
        
        Args:
            parent_id: 父分类ID
            
        Returns:
            子分类列表
        """
        pass
    
    @abstractmethod
    def count_products_in_category(self, category_id: Any) -> int:
        """
        获取分类下的商品数量。
        
        Args:
            category_id: 分类ID
            
        Returns:
            分类下的商品数量
        """
        pass


class SearchService:
    """
    搜索服务接口。
    定义用于搜索商品的方法。
    """
    
    @abstractmethod
    def search(
        self, 
        keyword: str, 
        filters: Optional[Dict[str, Any]] = None,
        page: int = 1, 
        page_size: int = 20,
        include_facets: bool = False,
        facet_fields: Optional[List[str]] = None
    ) -> Tuple[List[Product], int, Dict[str, Any]]:
        """
        搜索商品。
        
        Args:
            keyword: 搜索关键词
            filters: 过滤条件
            page: 页码
            page_size: 每页大小
            include_facets: 是否包含分面结果
            facet_fields: 需要聚合的分面字段列表
            
        Returns:
            商品列表、总数和分面结果的元组
        """
        pass


class InventoryLockService:
    """
    库存锁定服务接口。
    定义用于锁定和解锁商品库存的方法。
    """
    
    @abstractmethod
    def lock_inventory(self, product_id: Any, quantity: int, lock_key: str) -> bool:
        """
        锁定商品库存。
        
        Args:
            product_id: 商品ID
            quantity: 锁定数量
            lock_key: 锁定键
            
        Returns:
            是否锁定成功
        """
        pass
    
    @abstractmethod
    def unlock_inventory(self, product_id: Any, quantity: int, lock_key: str) -> bool:
        """
        解锁商品库存。
        
        Args:
            product_id: 商品ID
            quantity: 解锁数量
            lock_key: 锁定键
            
        Returns:
            是否解锁成功
        """
        pass
    
    @abstractmethod
    def confirm_lock(self, product_id: Any, lock_key: str) -> bool:
        """
        确认库存锁定。
        将临时锁定转为永久锁定。
        
        Args:
            product_id: 商品ID
            lock_key: 锁定键
            
        Returns:
            是否确认成功
        """
        pass
