"""
商品基础设施层工厂。
负责创建和管理基础设施层对象，包括仓储和服务实例。
"""
from core.infrastructure.cache import CacheService
from core.infrastructure.transaction import TransactionManager

from products.domain import ProductRepository, CategoryRepository, SearchService, InventoryLockService
from products.infrastructure.repositories.django_product_repository import DjangoProductRepository
from products.infrastructure.repositories.django_category_repository import DjangoCategoryRepository
from products.infrastructure.services.django_search_service import DjangoSearchService
from products.infrastructure.services.inventory_lock_service import MySQLInventoryLockService
from products.infrastructure.services.cache_manager import ProductCacheManager


class ProductInfrastructureFactory:
    """
    商品基础设施层工厂类。
    负责创建商品领域的基础设施层对象，如仓储和服务实例。
    """
    
    def __init__(self, cache_service: CacheService, transaction_manager: TransactionManager):
        """
        初始化商品基础设施层工厂。
        
        Args:
            cache_service: 缓存服务
            transaction_manager: 事务管理器
        """
        self.cache_service = cache_service
        self.transaction_manager = transaction_manager
        
        # 存储已创建的实例
        self._product_repository = None
        self._category_repository = None
        self._search_service = None
        self._inventory_lock_service = None
        self._cache_manager = None
    
    def create_product_repository(self) -> ProductRepository:
        """
        创建商品仓储。
        
        Returns:
            商品仓储实例
        """
        if not self._product_repository:
            self._product_repository = DjangoProductRepository()
        
        return self._product_repository
    
    def create_category_repository(self) -> CategoryRepository:
        """
        创建分类仓储。
        
        Returns:
            分类仓储实例
        """
        if not self._category_repository:
            self._category_repository = DjangoCategoryRepository()
        
        return self._category_repository
    
    def create_search_service(self) -> SearchService:
        """
        创建搜索服务。
        
        Returns:
            搜索服务实例
        """
        if not self._search_service:
            product_repository = self.create_product_repository()
            self._search_service = DjangoSearchService(
                product_repository=product_repository,
                cache_service=self.cache_service
            )
        
        return self._search_service
    
    def create_inventory_lock_service(self) -> InventoryLockService:
        """
        创建库存锁定服务。
        
        Returns:
            库存锁定服务实例
        """
        if not self._inventory_lock_service:
            self._inventory_lock_service = MySQLInventoryLockService(
                cache_service=self.cache_service
            )
        
        return self._inventory_lock_service
    
    def create_cache_manager(self) -> ProductCacheManager:
        """
        创建缓存管理服务。
        
        Returns:
            缓存管理服务实例
        """
        if not self._cache_manager:
            product_repository = self.create_product_repository()
            self._cache_manager = ProductCacheManager(
                cache_service=self.cache_service,
                product_repository=product_repository
            )
        
        return self._cache_manager
    
    def initialize_services(self, preheat_cache: bool = True):
        """
        初始化所有服务。
        
        Args:
            preheat_cache: 是否预热缓存
        """
        # 创建所有服务
        self.create_product_repository()
        self.create_category_repository()
        self.create_search_service()
        self.create_inventory_lock_service()
        
        # 创建并初始化缓存管理器
        cache_manager = self.create_cache_manager()
        if preheat_cache:
            cache_manager.preheat_cache(async_preheat=True) 