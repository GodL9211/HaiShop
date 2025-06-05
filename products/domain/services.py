"""
商品领域模型中的服务。
定义跨实体的商品业务逻辑服务。
"""
from typing import Any, Dict, List, Optional, Tuple

from core.domain import Money
from core.domain.events import DomainEvents
from products.domain.aggregates import ProductAggregate
from products.domain.entities import Product
from products.domain.repositories import ProductRepository, CategoryRepository
from products.domain.value_objects import ProductCategory, ProductSpecification
from products.domain.events import (
    ProductCreatedEvent,
    ProductUpdatedEvent,
    ProductStateChangedEvent,
    ProductRatingAddedEvent,
)


class ProductService:
    """
    商品领域服务。
    实现跨实体的商品业务逻辑。
    """
    
    def __init__(
        self,
        product_repository: ProductRepository,
        category_repository: CategoryRepository
    ):
        """
        初始化商品领域服务。
        
        Args:
            product_repository: 商品仓储
            category_repository: 分类仓储
        """
        self.product_repository = product_repository
        self.category_repository = category_repository
    
    def create_product(
        self,
        name: str,
        description: str,
        price: Money,
        keywords: str = "",
        category_id: Optional[Any] = None,
        specification: Optional[Dict[str, Any]] = None,
        initial_stock: int = 0
    ) -> ProductAggregate:
        """
        创建商品。
        
        Args:
            name: 商品名称
            description: 商品描述
            price: 商品价格
            keywords: 商品关键词
            category_id: 商品分类ID
            specification: 商品规格
            initial_stock: 初始库存
            
        Returns:
            创建的商品聚合根
        """
        # 验证分类是否存在
        if category_id:
            category = self.category_repository.get_by_id(category_id)
            if not category:
                raise ValueError(f"分类不存在: ID={category_id}")
        
        # 创建商品实体
        product = Product(
            name=name,
            description=description,
            price=price,
            keywords=keywords,
            category_id=category_id
        )
        
        # 创建商品规格
        product_spec = ProductSpecification(specification or {})
        
        # 创建商品聚合根
        product_aggregate = ProductAggregate(
            product=product,
            specification=product_spec,
            stock_available=initial_stock
        )
        
        # 添加商品创建事件
        product_aggregate.add_domain_event(
            ProductCreatedEvent(
                product_id=product.id,
                name=name,
                price=price,
                category_id=category_id
            )
        )
        
        # 保存商品聚合根
        return self.product_repository.save(product_aggregate)
    
    def update_product(
        self,
        product_id: Any,
        name: Optional[str] = None,
        description: Optional[str] = None,
        price: Optional[Money] = None,
        keywords: Optional[str] = None,
        category_id: Optional[Any] = None,
        specification: Optional[Dict[str, Any]] = None
    ) -> ProductAggregate:
        """
        更新商品信息。
        
        Args:
            product_id: 商品ID
            name: 商品名称
            description: 商品描述
            price: 商品价格
            keywords: 商品关键词
            category_id: 商品分类ID
            specification: 商品规格
            
        Returns:
            更新后的商品聚合根
            
        Raises:
            ValueError: 如果商品不存在
        """
        # 获取商品聚合根
        product_aggregate = self.product_repository.get_by_id(product_id)
        if not product_aggregate:
            raise ValueError(f"商品不存在: ID={product_id}")
        
        # 验证分类是否存在
        if category_id:
            category = self.category_repository.get_by_id(category_id)
            if not category:
                raise ValueError(f"分类不存在: ID={category_id}")
        
        # 记录更新的字段
        updated_fields = []
        
        # 更新基本信息
        if any([name, description, keywords, category_id]):
            product_aggregate.product.update_basic_info(
                name=name,
                description=description,
                keywords=keywords,
                category_id=category_id
            )
            updated_fields.extend([f for f in ['name', 'description', 'keywords', 'category_id'] 
                                 if locals()[f] is not None])
        
        # 更新价格
        if price:
            product_aggregate.update_price(price)
            updated_fields.append('price')
        
        # 更新规格
        if specification:
            product_aggregate.update_specification(ProductSpecification(specification))
            updated_fields.append('specification')
        
        # 添加商品更新事件
        if updated_fields:
            product_aggregate.add_domain_event(
                ProductUpdatedEvent(
                    product_id=product_id,
                    updated_fields=updated_fields
                )
            )
        
        # 保存商品聚合根
        return self.product_repository.save(product_aggregate)
    
    def change_product_state(
        self,
        product_id: Any,
        activate: bool
    ) -> ProductAggregate:
        """
        变更商品状态。
        
        Args:
            product_id: 商品ID
            activate: 是否激活
            
        Returns:
            更新后的商品聚合根
            
        Raises:
            ValueError: 如果商品不存在
        """
        # 获取商品聚合根
        product_aggregate = self.product_repository.get_by_id(product_id)
        if not product_aggregate:
            raise ValueError(f"商品不存在: ID={product_id}")
        
        # 记录旧状态
        old_state = product_aggregate.product.state
        
        # 变更状态
        if activate:
            product_aggregate.product.activate()
        else:
            product_aggregate.product.deactivate()
        
        # 添加状态变更事件
        product_aggregate.add_domain_event(
            ProductStateChangedEvent(
                product_id=product_id,
                old_state=old_state,
                new_state=product_aggregate.product.state
            )
        )
        
        # 保存商品聚合根
        return self.product_repository.save(product_aggregate)
    
    def update_stock(
        self,
        product_id: Any,
        new_stock: int,
        reserved_stock: int = None
    ) -> ProductAggregate:
        """
        更新商品库存。
        
        Args:
            product_id: 商品ID
            new_stock: 新的可用库存数量
            reserved_stock: 新的预留库存数量，如果为None则保持不变
            
        Returns:
            更新后的商品聚合根
            
        Raises:
            ValueError: 如果商品不存在或库存为负数
        """
        if new_stock < 0:
            raise ValueError("可用库存不能为负数")
        
        if reserved_stock is not None and reserved_stock < 0:
            raise ValueError("预留库存不能为负数")
        
        # 获取商品聚合根 - 确保product_id是字符串
        product_id_str = str(product_id)
        product_aggregate = self.product_repository.get_by_id(product_id_str)
        if not product_aggregate:
            raise ValueError(f"商品不存在: ID={product_id_str}")
        
        # 更新可用库存
        product_aggregate.update_stock(new_stock)
        
        # 如果提供了预留库存，也更新它
        if reserved_stock is not None:
            product_aggregate.update_reserved_stock(reserved_stock)
        
        # 保存商品聚合根
        return self.product_repository.save(product_aggregate)
    
    def add_rating(
        self,
        product_id: Any,
        rating_value: float
    ) -> ProductAggregate:
        """
        添加商品评分。
        
        Args:
            product_id: 商品ID
            rating_value: 评分值
            
        Returns:
            更新后的商品聚合根
            
        Raises:
            ValueError: 如果商品不存在或评分值无效
        """
        # 验证评分值
        if not (1 <= rating_value <= 5):
            raise ValueError("评分值必须在1到5之间")
        
        # 获取商品聚合根
        product_aggregate = self.product_repository.get_by_id(product_id)
        if not product_aggregate:
            raise ValueError(f"商品不存在: ID={product_id}")
        
        # 添加评分
        old_rating = product_aggregate.rating
        product_aggregate.add_rating(rating_value)
        
        # 添加评分事件
        product_aggregate.add_domain_event(
            ProductRatingAddedEvent(
                product_id=product_id,
                rating_value=rating_value,
                new_average=float(product_aggregate.rating.value),
                new_count=product_aggregate.rating.count
            )
        )
        
        # 保存商品聚合根
        return self.product_repository.save(product_aggregate)
    
    def get_related_products(
        self,
        product_id: Any,
        limit: int = 5
    ) -> List[ProductAggregate]:
        """
        获取相关商品。
        基于相同分类或关键词匹配。
        
        Args:
            product_id: 商品ID
            limit: 返回的最大数量
            
        Returns:
            相关商品列表
            
        Raises:
            ValueError: 如果商品不存在
        """
        # 获取商品聚合根
        product_aggregate = self.product_repository.get_by_id(product_id)
        if not product_aggregate:
            raise ValueError(f"商品不存在: ID={product_id}")
        
        # 获取商品关键词和分类
        keywords = product_aggregate.product.keywords
        category_id = product_aggregate.product.category_id
        
        # 先尝试根据分类查找
        if category_id:
            # 确保category_id是字符串类型
            category_id_str = str(category_id)
            related_products, _ = self.product_repository.find_by_category(
                category_id=category_id_str,
                page=1,
                page_size=limit + 1  # 多查询一个，以便过滤掉当前商品
            )
            # 过滤掉当前商品
            related_products = [p for p in related_products if str(p.id) != str(product_id)][:limit]
            
            # 如果已经找到足够的相关商品，则返回
            if len(related_products) >= limit:
                return related_products
        else:
            related_products = []
        
        # 如果分类相关商品不足，则继续根据关键词查找
        if keywords and len(related_products) < limit:
            keyword_products, _ = self.product_repository.find_by_keyword(
                keyword=keywords,
                page=1,
                page_size=limit + 1
            )
            # 过滤掉当前商品和已有的相关商品
            keyword_products = [
                p for p in keyword_products 
                if str(p.id) != str(product_id) and p not in related_products
            ]
            
            # 添加关键词相关商品
            remaining_slots = limit - len(related_products)
            related_products.extend(keyword_products[:remaining_slots])
        
        return related_products
