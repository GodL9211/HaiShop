"""
聚合根模块。
包含AggregateRoot基类，用于定义领域聚合的边界和不变性规则。
"""
from typing import Any, List, Optional, Type
from core.domain.base import Entity
from core.domain.events import DomainEvent


class AggregateRoot(Entity):
    """
    聚合根基类。
    聚合根是一个特殊的实体，它定义了一个聚合的边界，
    并负责维护聚合内部对象的不变性规则。
    它是外部访问聚合内部对象的唯一入口点。
    """
    
    def __init__(self, id: Any = None):
        """
        初始化聚合根。
        
        Args:
            id: 聚合根标识，如果未提供，将自动生成UUID
        """
        super().__init__(id)
        self._domain_events: List[DomainEvent] = []
        self._version: int = 0
    
    @property
    def version(self) -> int:
        """
        获取聚合根的版本号，用于乐观锁。
        
        Returns:
            聚合根的版本号
        """
        return self._version
    
    def increment_version(self) -> None:
        """
        增加聚合根的版本号，通常在修改聚合状态后调用。
        """
        self._version += 1
    
    def add_domain_event(self, event: DomainEvent) -> None:
        """
        添加领域事件到事件列表中，等待发布。
        
        Args:
            event: 要添加的领域事件
        """
        self._domain_events.append(event)
    
    def clear_domain_events(self) -> List[DomainEvent]:
        """
        清除并返回所有未发布的领域事件。
        
        Returns:
            未发布的领域事件列表
        """
        events = self._domain_events.copy()
        self._domain_events.clear()
        return events
    
    def check_invariants(self) -> bool:
        """
        检查聚合的不变性规则。
        子类应该重写此方法以实现特定的业务规则验证。
        
        Returns:
            如果所有不变性规则都满足，则返回True；否则返回False
        """
        return True
