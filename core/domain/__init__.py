"""
领域模型包。
提供实体、值对象、聚合根和领域事件等领域驱动设计(DDD)的核心概念。
"""

# 基础类
from core.domain.base import Entity
from core.domain.value_objects import ValueObject, Money
from core.domain.aggregates import AggregateRoot

# 领域事件
from core.domain.events import (
    DomainEvent,
    DomainEvents,
    ProductPriceChangedEvent,
    ProductStockChangedEvent,
    OrderCreatedEvent,
)

# 领域异常
from core.domain.exceptions import (
    DomainException,
    InvalidEntityStateException,
    EntityNotFoundException,
    BusinessRuleViolationException,
    ConcurrencyException,
    InsufficientStockException,
    ValidationException,
    AuthorizationException,
    LockAcquisitionException,
)

# 仓储接口
from core.domain.repositories import (
    Repository,
    ReadOnlyRepository,
    SearchableRepository,
)

__all__ = [
    # 基础类
    'Entity',
    'ValueObject',
    'Money',
    'AggregateRoot',
    
    # 领域事件
    'DomainEvent',
    'DomainEvents',
    'ProductPriceChangedEvent',
    'ProductStockChangedEvent',
    'OrderCreatedEvent',
    
    # 领域异常
    'DomainException',
    'InvalidEntityStateException',
    'EntityNotFoundException',
    'BusinessRuleViolationException',
    'ConcurrencyException',
    'InsufficientStockException',
    'ValidationException',
    'AuthorizationException',
    'LockAcquisitionException',
    
    # 仓储接口
    'Repository',
    'ReadOnlyRepository',
    'SearchableRepository',
]
