"""
商品领域模型中的聚合根。
包含商品聚合根的定义，管理商品实体和相关值对象。
"""
from typing import Any, Dict, Optional

from core.domain import AggregateRoot, Money
from core.domain.events import ProductPriceChangedEvent, ProductStockChangedEvent, ProductReservedStockChangedEvent
from products.domain.entities import Product
from products.domain.value_objects import Rating, ProductSpecification


class ProductAggregate(AggregateRoot):
    """
    商品聚合根。
    封装商品实体及其相关属性，确保商品数据的一致性。
    """
    
    def __init__(
        self,
        product: Product,
        rating: Rating = None,
        specification: ProductSpecification = None,
        stock_available: int = 0,
        stock_reserved: int = 0
    ):
        """
        初始化商品聚合根。
        
        Args:
            product: 商品实体
            rating: 商品评分
            specification: 商品规格
            stock_available: 可用库存
            stock_reserved: 预留库存
        """
        super().__init__(product.id)
        self._product = product
        self._rating = rating or Rating.zero()
        self._specification = specification or ProductSpecification({})
        self._stock_available = stock_available
        self._stock_reserved = stock_reserved
    
    @property
    def product(self) -> Product:
        """获取商品实体"""
        return self._product
    
    @property
    def rating(self) -> Rating:
        """获取商品评分"""
        return self._rating
    
    @property
    def specification(self) -> ProductSpecification:
        """获取商品规格"""
        return self._specification
    
    @property
    def stock_available(self) -> int:
        """获取可用库存"""
        return self._stock_available
    
    @property
    def stock_reserved(self) -> int:
        """获取预留库存"""
        return self._stock_reserved
    
    @property
    def total_stock(self) -> int:
        """获取总库存"""
        return self._stock_available + self._stock_reserved
    
    def update_price(self, new_price: Money) -> None:
        """
        更新商品价格。
        
        Args:
            new_price: 新价格
        """
        old_price = self._product.price
        self._product.update_price(new_price)
        
        # 添加价格变更事件
        self.add_domain_event(
            ProductPriceChangedEvent(
                product_id=self.id,
                old_price=old_price,
                new_price=new_price
            )
        )
        
        # 增加版本号
        self.increment_version()
    
    def update_stock(self, new_stock: int) -> None:
        """
        更新商品库存。
        
        Args:
            new_stock: 新的可用库存
        """
        old_stock = self._stock_available
        self._stock_available = new_stock
        
        # 添加库存变更事件
        self.add_domain_event(
            ProductStockChangedEvent(
                product_id=self.id,
                old_stock=old_stock,
                new_stock=new_stock
            )
        )
        
        # 增加版本号
        self.increment_version()
    
    def reserve_stock(self, quantity: int) -> bool:
        """
        预留库存。
        
        Args:
            quantity: 预留数量
            
        Returns:
            预留成功返回True，库存不足返回False
        """
        if self._stock_available < quantity:
            return False
        
        self._stock_available -= quantity
        self._stock_reserved += quantity
        
        # 增加版本号
        self.increment_version()
        
        return True
    
    def release_reserved_stock(self, quantity: int) -> None:
        """
        释放预留库存。
        
        Args:
            quantity: 释放数量
        """
        if self._stock_reserved < quantity:
            raise ValueError(f"预留库存不足，当前:{self._stock_reserved}，请求:{quantity}")
        
        self._stock_reserved -= quantity
        self._stock_available += quantity
        
        # 增加版本号
        self.increment_version()
    
    def confirm_reserved_stock(self, quantity: int) -> None:
        """
        确认预留库存使用，从预留库存中扣减。
        
        Args:
            quantity: 确认使用的数量
        """
        if self._stock_reserved < quantity:
            raise ValueError(f"预留库存不足，当前:{self._stock_reserved}，请求:{quantity}")
        
        self._stock_reserved -= quantity
        
        # 增加版本号
        self.increment_version()
    
    def add_rating(self, rating_value: float) -> None:
        """
        添加商品评分。
        
        Args:
            rating_value: 评分值
        """
        self._rating = self._rating.add_rating(rating_value)
        
        # 增加版本号
        self.increment_version()
    
    def update_specification(self, specification: ProductSpecification) -> None:
        """
        更新商品规格。
        
        Args:
            specification: 新的商品规格
        """
        self._specification = specification
        
        # 增加版本号
        self.increment_version()
    
    def is_available_for_purchase(self, quantity: int = 1) -> bool:
        """
        检查商品是否可购买。
        
        Args:
            quantity: 购买数量
            
        Returns:
            如果商品可购买则返回True，否则返回False
        """
        return (
            self._product.is_available() and
            self._stock_available >= quantity
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """
        将商品聚合转换为字典表示。
        
        Returns:
            商品聚合的字典表示
        """
        return {
            "id": str(self.id),
            "name": self._product.name,
            "description": self._product.description,
            "price": self._product.price.to_dict(),
            "keywords": self._product.keywords,
            "category_id": str(self._product.category_id) if self._product.category_id else None,
            "state": self._product.state,
            "rating": self._rating.to_dict(),
            "specification": self._specification.to_dict(),
            "stock_available": self._stock_available,
            "stock_reserved": self._stock_reserved,
            "total_stock": self.total_stock,
            "created_at": self._product.created_at.isoformat(),
            "updated_at": self._product.updated_at.isoformat(),
            "version": self.version
        }
    
    def update_reserved_stock(self, new_reserved_stock: int) -> None:
        """
        更新商品预留库存。
        
        Args:
            new_reserved_stock: 新的预留库存
        """
        old_reserved_stock = self._stock_reserved
        self._stock_reserved = new_reserved_stock
        
        # 添加预留库存变更事件
        self.add_domain_event(
            ProductReservedStockChangedEvent(
                product_id=self.id,
                old_reserved_stock=old_reserved_stock,
                new_reserved_stock=new_reserved_stock
            )
        )
        
        # 增加版本号
        self.increment_version()
