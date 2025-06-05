"""
值对象模块。
包含ValueObject基类和常用值对象实现，如Money。
"""
from decimal import Decimal
from typing import Any, Dict, List, Optional


class ValueObject:
    """
    值对象基类。
    值对象是通过其属性值而非标识定义的不可变对象。
    相同属性值的值对象被视为相等。
    """
    
    def __eq__(self, other: Any) -> bool:
        """
        判断两个值对象是否相等，通过比较它们的属性值。
        
        Args:
            other: 另一个值对象
            
        Returns:
            如果两个值对象的属性值相等，则返回True；否则返回False
        """
        if not isinstance(other, self.__class__):
            return False
        return self.__dict__ == other.__dict__
    
    def __hash__(self) -> int:
        """
        计算值对象的哈希值，基于其属性值。
        
        Returns:
            值对象属性值的哈希值
        """
        # 将__dict__转换为可哈希类型(frozenset)
        items = frozenset((k, hash(v)) for k, v in self.__dict__.items())
        return hash(items)


class Money(ValueObject):
    """
    金额值对象，表示带有货币单位的金额。
    """
    
    def __init__(self, amount: Any, currency: str = "CNY"):
        """
        初始化金额值对象。
        
        Args:
            amount: 金额数值，将被转换为Decimal
            currency: 货币单位，默认为人民币(CNY)
        """
        self.amount = Decimal(amount)
        self.currency = currency
    
    def __add__(self, other: 'Money') -> 'Money':
        """
        金额加法运算。
        
        Args:
            other: 另一个金额值对象
            
        Returns:
            两个金额的和
            
        Raises:
            ValueError: 当两个金额的货币单位不同时抛出
        """
        if self.currency != other.currency:
            raise ValueError(f"不能相加不同货币单位的金额: {self.currency} != {other.currency}")
        return Money(self.amount + other.amount, self.currency)
    
    def __sub__(self, other: 'Money') -> 'Money':
        """
        金额减法运算。
        
        Args:
            other: 另一个金额值对象
            
        Returns:
            两个金额的差
            
        Raises:
            ValueError: 当两个金额的货币单位不同时抛出
        """
        if self.currency != other.currency:
            raise ValueError(f"不能相减不同货币单位的金额: {self.currency} != {other.currency}")
        return Money(self.amount - other.amount, self.currency)
    
    def __mul__(self, multiplier: Decimal) -> 'Money':
        """
        金额乘法运算。
        
        Args:
            multiplier: 乘数
            
        Returns:
            金额乘以乘数的结果
        """
        return Money(self.amount * Decimal(multiplier), self.currency)
    
    def __str__(self) -> str:
        """
        返回金额的字符串表示。
        
        Returns:
            金额的字符串表示，例如"CNY 100.00"
        """
        return f"{self.currency} {self.amount:.2f}"
    
    def to_dict(self) -> Dict[str, Any]:
        """
        将金额转换为字典表示。
        
        Returns:
            包含金额和货币单位的字典
        """
        return {
            "amount": str(self.amount),
            "currency": self.currency
        }
