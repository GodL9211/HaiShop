"""
商品领域模型中的事件。
定义商品相关的领域事件。
"""
from typing import Any

from core.domain.events import DomainEvent


class ProductCreatedEvent(DomainEvent):
    """商品创建事件"""
    
    def __init__(self, product_id: Any, name: str, price: Any, category_id: Any = None):
        """
        初始化商品创建事件。
        
        Args:
            product_id: 商品ID
            name: 商品名称
            price: 商品价格
            category_id: 商品分类ID
        """
        super().__init__()
        self.product_id = product_id
        self.name = name
        self.price = price
        self.category_id = category_id


class ProductUpdatedEvent(DomainEvent):
    """商品更新事件"""
    
    def __init__(self, product_id: Any, updated_fields: list):
        """
        初始化商品更新事件。
        
        Args:
            product_id: 商品ID
            updated_fields: 更新的字段列表
        """
        super().__init__()
        self.product_id = product_id
        self.updated_fields = updated_fields


class ProductStateChangedEvent(DomainEvent):
    """商品状态变更事件"""
    
    def __init__(self, product_id: Any, old_state: str, new_state: str):
        """
        初始化商品状态变更事件。
        
        Args:
            product_id: 商品ID
            old_state: 旧状态
            new_state: 新状态
        """
        super().__init__()
        self.product_id = product_id
        self.old_state = old_state
        self.new_state = new_state


class ProductRatingAddedEvent(DomainEvent):
    """商品评分添加事件"""
    
    def __init__(self, product_id: Any, rating_value: float, new_average: float, new_count: int):
        """
        初始化商品评分添加事件。
        
        Args:
            product_id: 商品ID
            rating_value: 新增评分值
            new_average: 新的平均评分
            new_count: 新的评分数量
        """
        super().__init__()
        self.product_id = product_id
        self.rating_value = rating_value
        self.new_average = new_average
        self.new_count = new_count


class CategoryCreatedEvent(DomainEvent):
    """分类创建事件"""
    
    def __init__(self, category_id: Any, name: str, parent_id: Any = None):
        """
        初始化分类创建事件。
        
        Args:
            category_id: 分类ID
            name: 分类名称
            parent_id: 父分类ID
        """
        super().__init__()
        self.category_id = category_id
        self.name = name
        self.parent_id = parent_id


class CategoryUpdatedEvent(DomainEvent):
    """分类更新事件"""
    
    def __init__(self, category_id: Any, updated_fields: list):
        """
        初始化分类更新事件。
        
        Args:
            category_id: 分类ID
            updated_fields: 更新的字段列表
        """
        super().__init__()
        self.category_id = category_id
        self.updated_fields = updated_fields


class CategoryDeletedEvent(DomainEvent):
    """分类删除事件"""
    
    def __init__(self, category_id: Any):
        """
        初始化分类删除事件。
        
        Args:
            category_id: 分类ID
        """
        super().__init__()
        self.category_id = category_id
