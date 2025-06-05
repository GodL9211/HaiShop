"""
领域事件模块。
包含DomainEvent基类和DomainEvents管理器，用于领域事件的发布和订阅。
"""
from datetime import datetime
from typing import Any, Callable, Dict, List, Type
import uuid


class DomainEvent:
    """
    领域事件基类。
    领域事件表示领域模型中发生的重要事件，通常用于跨聚合的业务流程。
    """
    
    def __init__(self):
        """
        初始化领域事件。
        自动设置事件ID和发生时间。
        """
        self.id = uuid.uuid4()
        self.occurred_on = datetime.now()


# 事件处理器类型
EventHandler = Callable[[DomainEvent], None]


class DomainEvents:
    """
    领域事件管理器。
    负责事件的发布和订阅。
    """
    
    # 事件处理器字典，键为事件类型，值为处理器列表
    _handlers: Dict[Type[DomainEvent], List[EventHandler]] = {}
    
    @classmethod
    def register(cls, event_type: Type[DomainEvent], handler: EventHandler) -> None:
        """
        注册事件处理器。
        
        Args:
            event_type: 事件类型
            handler: 事件处理器函数
        """
        if event_type not in cls._handlers:
            cls._handlers[event_type] = []
        cls._handlers[event_type].append(handler)
    
    @classmethod
    def unregister(cls, event_type: Type[DomainEvent], handler: EventHandler) -> None:
        """
        取消注册事件处理器。
        
        Args:
            event_type: 事件类型
            handler: 事件处理器函数
        """
        if event_type in cls._handlers:
            cls._handlers[event_type].remove(handler)
            if not cls._handlers[event_type]:
                del cls._handlers[event_type]
    
    @classmethod
    def publish(cls, event: DomainEvent) -> None:
        """
        发布事件。
        调用所有注册到该事件类型的处理器。
        
        Args:
            event: 要发布的事件
        """
        event_type = type(event)
        if event_type in cls._handlers:
            for handler in cls._handlers[event_type]:
                handler(event)
    
    @classmethod
    def clear_handlers(cls) -> None:
        """
        清除所有事件处理器。
        通常用于测试环境的重置。
        """
        cls._handlers.clear()


# 常用领域事件定义

class ProductPriceChangedEvent(DomainEvent):
    """商品价格变更事件"""
    
    def __init__(self, product_id: Any, old_price: Any, new_price: Any):
        """
        初始化商品价格变更事件。
        
        Args:
            product_id: 商品ID
            old_price: 旧价格
            new_price: 新价格
        """
        super().__init__()
        self.product_id = product_id
        self.old_price = old_price
        self.new_price = new_price


class ProductStockChangedEvent(DomainEvent):
    """商品库存变更事件"""
    
    def __init__(self, product_id: Any, old_stock: int, new_stock: int):
        """
        初始化商品库存变更事件。
        
        Args:
            product_id: 商品ID
            old_stock: 旧库存
            new_stock: 新库存
        """
        super().__init__()
        self.product_id = product_id
        self.old_stock = old_stock
        self.new_stock = new_stock


class OrderCreatedEvent(DomainEvent):
    """订单创建事件"""
    
    def __init__(self, order_id: Any, user_id: Any, total_amount: Any):
        """
        初始化订单创建事件。
        
        Args:
            order_id: 订单ID
            user_id: 用户ID
            total_amount: 订单总金额
        """
        super().__init__()
        self.order_id = order_id
        self.user_id = user_id
        self.total_amount = total_amount


class ProductReservedStockChangedEvent(DomainEvent):
    """商品预留库存变更事件"""
    
    def __init__(
        self,
        product_id: Any,
        old_reserved_stock: int,
        new_reserved_stock: int
    ):
        """
        初始化商品预留库存变更事件。
        
        Args:
            product_id: 商品ID
            old_reserved_stock: 旧预留库存
            new_reserved_stock: 新预留库存
        """
        super().__init__()
        self.product_id = product_id
        self.old_reserved_stock = old_reserved_stock
        self.new_reserved_stock = new_reserved_stock
