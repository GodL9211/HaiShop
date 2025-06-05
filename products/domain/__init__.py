"""
商品领域模型包。
提供商品相关的实体、值对象、聚合根、服务等。
"""

# 实体
from products.domain.entities import Product, ProductState, ProductStateException

# 值对象
from products.domain.value_objects import ProductCategory, ProductSpecification, Rating, SearchQuery, SearchResult, SearchFacet

# 聚合根
from products.domain.aggregates import ProductAggregate

# 仓储接口
from products.domain.repositories import ProductRepository, CategoryRepository, SearchService, InventoryLockService

# 领域事件
from products.domain.events import (
    ProductCreatedEvent,
    ProductUpdatedEvent,
    ProductStateChangedEvent,
    ProductRatingAddedEvent,
    CategoryCreatedEvent,
    CategoryUpdatedEvent,
    CategoryDeletedEvent,
)

# 领域服务
from products.domain.services import ProductService

__all__ = [
    # 实体
    'Product',
    'ProductState',
    'ProductStateException',
    
    # 值对象
    'ProductCategory',
    'ProductSpecification',
    'Rating',
    'SearchQuery',
    'SearchResult',
    'SearchFacet',
    
    # 聚合根
    'ProductAggregate',
    
    # 仓储接口
    'ProductRepository',
    'CategoryRepository',
    'SearchService',
    'InventoryLockService',
    
    # 领域事件
    'ProductCreatedEvent',
    'ProductUpdatedEvent',
    'ProductStateChangedEvent',
    'ProductRatingAddedEvent',
    'CategoryCreatedEvent',
    'CategoryUpdatedEvent',
    'CategoryDeletedEvent',
    
    # 领域服务
    'ProductService',
]
