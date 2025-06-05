"""
领域异常模块。
包含领域模型中使用的各种异常类。
"""
from typing import Any, Optional


class DomainException(Exception):
    """
    领域异常基类。
    所有领域模型中的异常都应继承自此类。
    """
    
    def __init__(self, message: str):
        """
        初始化领域异常。
        
        Args:
            message: 异常消息
        """
        self.message = message
        super().__init__(self.message)


class InvalidEntityStateException(DomainException):
    """
    实体状态无效异常。
    当实体处于无效状态时抛出。
    """
    
    def __init__(self, entity_name: str, reason: str):
        """
        初始化实体状态无效异常。
        
        Args:
            entity_name: 实体名称
            reason: 无效原因
        """
        message = f"{entity_name}处于无效状态: {reason}"
        super().__init__(message)
        self.entity_name = entity_name
        self.reason = reason


class EntityNotFoundException(DomainException):
    """
    实体未找到异常。
    当请求的实体不存在时抛出。
    """
    
    def __init__(self, entity_name: str, entity_id: Any):
        """
        初始化实体未找到异常。
        
        Args:
            entity_name: 实体名称
            entity_id: 实体ID
        """
        message = f"无法找到{entity_name}: ID={entity_id}"
        super().__init__(message)
        self.entity_name = entity_name
        self.entity_id = entity_id


class BusinessRuleViolationException(DomainException):
    """
    业务规则违反异常。
    当违反业务规则时抛出。
    """
    
    def __init__(self, rule_name: str, message: str):
        """
        初始化业务规则违反异常。
        
        Args:
            rule_name: 规则名称
            message: 异常消息
        """
        full_message = f"违反业务规则 '{rule_name}': {message}"
        super().__init__(full_message)
        self.rule_name = rule_name


class ConcurrencyException(DomainException):
    """
    并发异常。
    当发生并发冲突时抛出，例如在乐观锁情况下。
    """
    
    def __init__(self, entity_name: str, entity_id: Any):
        """
        初始化并发异常。
        
        Args:
            entity_name: 实体名称
            entity_id: 实体ID
        """
        message = f"{entity_name}(ID={entity_id})已被另一个事务修改"
        super().__init__(message)
        self.entity_name = entity_name
        self.entity_id = entity_id


class InsufficientStockException(DomainException):
    """
    库存不足异常。
    当商品库存不足以满足请求时抛出。
    """
    
    def __init__(self, product_id: Any, requested: int, available: int):
        """
        初始化库存不足异常。
        
        Args:
            product_id: 商品ID
            requested: 请求数量
            available: 可用数量
        """
        message = f"商品(ID={product_id})库存不足，请求:{requested}，可用:{available}"
        super().__init__(message)
        self.product_id = product_id
        self.requested = requested
        self.available = available


class ValidationException(DomainException):
    """
    数据验证异常。
    当数据验证失败时抛出。
    """
    
    def __init__(self, field_name: Optional[str] = None, message: str = "数据验证失败"):
        """
        初始化数据验证异常。
        
        Args:
            field_name: 字段名称
            message: 异常消息
        """
        if field_name:
            full_message = f"字段'{field_name}'验证失败: {message}"
        else:
            full_message = message
        super().__init__(full_message)
        self.field_name = field_name


class AuthorizationException(DomainException):
    """
    授权异常。
    当用户没有执行操作的权限时抛出。
    """
    
    def __init__(self, user_id: Any, operation: str, resource: Optional[str] = None):
        """
        初始化授权异常。
        
        Args:
            user_id: 用户ID
            operation: 操作名称
            resource: 资源名称
        """
        if resource:
            message = f"用户(ID={user_id})没有权限执行'{operation}'操作，资源: {resource}"
        else:
            message = f"用户(ID={user_id})没有权限执行'{operation}'操作"
        super().__init__(message)
        self.user_id = user_id
        self.operation = operation
        self.resource = resource


class LockAcquisitionException(DomainException):
    """
    锁获取异常。
    当无法获取资源锁时抛出。
    """
    
    def __init__(self, resource_name: str, message: Optional[str] = None):
        """
        初始化锁获取异常。
        
        Args:
            resource_name: 资源名称
            message: 额外消息
        """
        if message:
            full_message = f"无法获取资源'{resource_name}'的锁: {message}"
        else:
            full_message = f"无法获取资源'{resource_name}'的锁"
        super().__init__(full_message)
        self.resource_name = resource_name
