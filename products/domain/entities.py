"""
商品领域模型中的实体。
包含商品相关的实体定义。
"""
from datetime import datetime
from typing import Any, List, Optional
from decimal import Decimal
import uuid

from core.domain import Entity, Money, DomainException


class ProductState:
    """商品状态枚举"""
    DRAFT = "draft"        # 草稿状态，未发布
    ACTIVE = "active"      # 激活状态，可销售
    INACTIVE = "inactive"  # 未激活状态，暂不可销售
    DELETED = "deleted"    # 已删除状态，不可见


class ProductStateException(DomainException):
    """商品状态异常"""
    def __init__(self, current_state: str, target_state: str):
        message = f"商品状态不能从 {current_state} 变更为 {target_state}"
        super().__init__(message)
        self.current_state = current_state
        self.target_state = target_state


class Product(Entity):
    """
    商品实体。
    代表系统中的商品。
    """
    
    def __init__(
        self,
        id: Any = None,
        name: str = "",
        description: str = "",
        price: Money = None,
        keywords: str = "",
        category_id: Any = None,
    ):
        """
        初始化商品实体。
        
        Args:
            id: 商品ID，如果未提供则自动生成
            name: 商品名称
            description: 商品描述
            price: 商品价格
            keywords: 商品关键词，用于搜索
            category_id: 商品分类ID
        """
        super().__init__(id)
        self.name = name
        self.description = description
        self.price = price or Money(0)
        self.keywords = keywords
        self.category_id = category_id
        self.state = ProductState.DRAFT
        self.created_at = datetime.now()
        self.updated_at = datetime.now()
        self.version = 0  # 添加版本号，用于乐观锁
    
    def activate(self) -> None:
        """
        激活商品，使其可被搜索和购买。
        从草稿或未激活状态变更为激活状态。
        
        Raises:
            ProductStateException: 如果当前状态不允许激活
        """
        if self.state == ProductState.DELETED:
            raise ProductStateException(self.state, ProductState.ACTIVE)
        
        self.state = ProductState.ACTIVE
        self.updated_at = datetime.now()
        self.increment_version()
    
    def deactivate(self) -> None:
        """
        停用商品，使其不可被搜索和购买。
        从激活状态变更为未激活状态。
        
        Raises:
            ProductStateException: 如果当前状态不允许停用
        """
        if self.state not in [ProductState.ACTIVE, ProductState.DRAFT]:
            raise ProductStateException(self.state, ProductState.INACTIVE)
        
        self.state = ProductState.INACTIVE
        self.updated_at = datetime.now()
        self.increment_version()
    
    def delete(self) -> None:
        """
        删除商品，使其不可见。
        
        Raises:
            ProductStateException: 如果当前状态已经是删除状态
        """
        if self.state == ProductState.DELETED:
            raise ProductStateException(self.state, ProductState.DELETED)
        
        self.state = ProductState.DELETED
        self.updated_at = datetime.now()
        self.increment_version()
    
    def update_price(self, new_price: Money) -> None:
        """
        更新商品价格。
        
        Args:
            new_price: 新价格
        """
        self.price = new_price
        self.updated_at = datetime.now()
        self.increment_version()
    
    def update_basic_info(
        self,
        name: Optional[str] = None,
        description: Optional[str] = None,
        keywords: Optional[str] = None,
        category_id: Optional[Any] = None
    ) -> None:
        """
        更新商品基本信息。
        
        Args:
            name: 商品名称
            description: 商品描述
            keywords: 商品关键词
            category_id: 商品分类ID
        """
        if name is not None:
            self.name = name
        if description is not None:
            self.description = description
        if keywords is not None:
            self.keywords = keywords
        if category_id is not None:
            self.category_id = category_id
        
        self.updated_at = datetime.now()
        self.increment_version()
    
    def is_available(self) -> bool:
        """
        检查商品是否可用于销售。
        
        Returns:
            如果商品处于激活状态，则返回True；否则返回False
        """
        return self.state == ProductState.ACTIVE
        
    def increment_version(self) -> None:
        """
        增加版本号，用于乐观锁。
        """
        self.version += 1
