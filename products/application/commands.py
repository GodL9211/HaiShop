"""
商品应用服务层的命令对象。
定义用于修改系统状态的命令。
"""
from typing import Any, Dict, Optional
from decimal import Decimal


class CreateProductCommand:
    """创建商品命令"""
    
    def __init__(
        self,
        name: str,
        description: str,
        price: Decimal,
        keywords: str = "",
        category_id: Optional[str] = None,
        specification: Optional[Dict[str, Any]] = None,
        initial_stock: int = 0
    ):
        """
        初始化创建商品命令。
        
        Args:
            name: 商品名称
            description: 商品描述
            price: 商品价格
            keywords: 商品关键词
            category_id: 商品分类ID
            specification: 商品规格
            initial_stock: 初始库存
        """
        self.name = name
        self.description = description
        self.price = price
        self.keywords = keywords
        self.category_id = category_id
        self.specification = specification
        self.initial_stock = initial_stock


class UpdateProductCommand:
    """更新商品命令"""
    
    def __init__(
        self,
        id: str,
        name: Optional[str] = None,
        description: Optional[str] = None,
        price: Optional[Decimal] = None,
        keywords: Optional[str] = None,
        category_id: Optional[str] = None,
        specification: Optional[Dict[str, Any]] = None
    ):
        """
        初始化更新商品命令。
        
        Args:
            id: 商品ID
            name: 商品名称
            description: 商品描述
            price: 商品价格
            keywords: 商品关键词
            category_id: 商品分类ID
            specification: 商品规格
        """
        self.id = id
        self.name = name
        self.description = description
        self.price = price
        self.keywords = keywords
        self.category_id = category_id
        self.specification = specification


class ChangeProductStateCommand:
    """变更商品状态命令"""
    
    def __init__(self, id: str, activate: bool):
        """
        初始化变更商品状态命令。
        
        Args:
            id: 商品ID
            activate: 是否激活
        """
        self.id = id
        self.activate = activate


class UpdateProductStockCommand:
    """更新商品库存命令"""
    
    def __init__(self, id: str, stock: int, reserved_stock: int = 0):
        """
        初始化更新商品库存命令。
        
        Args:
            id: 商品ID
            stock: 新的可用库存
            reserved_stock: 新的预留库存
        """
        self.id = id
        self.stock = stock
        self.reserved_stock = reserved_stock


class AddProductRatingCommand:
    """添加商品评分命令"""
    
    def __init__(self, id: str, rating_value: float):
        """
        初始化添加商品评分命令。
        
        Args:
            id: 商品ID
            rating_value: 评分值
        """
        self.id = id
        self.rating_value = rating_value


class CreateCategoryCommand:
    """创建分类命令"""
    
    def __init__(
        self,
        name: str,
        description: str = "",
        parent_id: Optional[str] = None
    ):
        """
        初始化创建分类命令。
        
        Args:
            name: 分类名称
            description: 分类描述
            parent_id: 父分类ID
        """
        self.name = name
        self.description = description
        self.parent_id = parent_id


class UpdateCategoryCommand:
    """更新分类命令"""
    
    def __init__(
        self,
        id: str,
        name: Optional[str] = None,
        description: Optional[str] = None,
        parent_id: Optional[str] = None
    ):
        """
        初始化更新分类命令。
        
        Args:
            id: 分类ID
            name: 分类名称
            description: 分类描述
            parent_id: 父分类ID
        """
        self.id = id
        self.name = name
        self.description = description
        self.parent_id = parent_id


class DeleteCategoryCommand:
    """删除分类命令"""
    
    def __init__(self, id: str):
        """
        初始化删除分类命令。
        
        Args:
            id: 分类ID
        """
        self.id = id
