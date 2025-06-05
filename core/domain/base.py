"""
核心领域模型基类模块。
包含Entity基类，用于所有具有唯一标识的领域对象。
"""
from typing import Any, TypeVar, Generic
import uuid

T = TypeVar('T')

class Entity:
    """
    实体基类。
    实体是具有唯一标识的领域对象，其相等性通过标识而非属性值判断。
    """
    def __init__(self, id: Any = None):
        """
        初始化实体。
        
        Args:
            id: 实体标识，如果未提供，将自动生成UUID
        """
        self.id = id if id is not None else uuid.uuid4()
    
    def __eq__(self, other: Any) -> bool:
        """
        判断两个实体是否相等，通过比较它们的标识。
        
        Args:
            other: 另一个实体
            
        Returns:
            如果两个实体标识相等，则返回True；否则返回False
        """
        if not isinstance(other, Entity):
            return False
        return self.id == other.id
    
    def __hash__(self) -> int:
        """
        计算实体的哈希值，基于其标识。
        
        Returns:
            实体标识的哈希值
        """
        return hash(self.id)
