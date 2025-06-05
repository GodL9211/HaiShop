"""
商品应用服务层的数据传输对象(DTOs)。
定义应用服务与外部通信使用的数据结构。
"""
from typing import Any, Dict, List, Optional
from decimal import Decimal
import uuid
from datetime import datetime


class ProductCreateDTO:
    """商品创建DTO"""
    
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
        初始化商品创建DTO。
        
        Args:
            name: 商品名称
            description: 商品描述
            price: 商品价格
            keywords: 商品关键词，用于搜索
            category_id: 商品分类ID
            specification: 商品规格，如颜色、尺寸等
            initial_stock: 初始库存
        """
        self.name = name
        self.description = description
        self.price = price
        self.keywords = keywords
        self.category_id = category_id
        self.specification = specification or {}
        self.initial_stock = initial_stock


class ProductUpdateDTO:
    """商品更新DTO"""
    
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
        初始化商品更新DTO。
        
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


class ProductStockUpdateDTO:
    """商品库存更新DTO"""
    
    def __init__(self, id: str, stock: int):
        """
        初始化商品库存更新DTO。
        
        Args:
            id: 商品ID
            stock: 新的库存数量
        """
        self.id = id
        self.stock = stock


class ProductRatingDTO:
    """商品评分DTO"""
    
    def __init__(self, id: str, rating_value: float):
        """
        初始化商品评分DTO。
        
        Args:
            id: 商品ID
            rating_value: 评分值(1-5)
        """
        self.id = id
        self.rating_value = rating_value


class ProductDTO:
    """商品数据传输对象，用于返回商品信息"""
    
    def __init__(
        self,
        id: str,
        name: str,
        description: str,
        price: Dict[str, Any],
        keywords: str,
        category_id: Optional[str],
        category_name: Optional[str],
        state: str,
        rating_value: float,
        rating_count: int,
        specification: Dict[str, Any],
        stock_available: int,
        stock_reserved: int,
        created_at: datetime,
        updated_at: datetime
    ):
        """
        初始化商品DTO。
        
        Args:
            id: 商品ID
            name: 商品名称
            description: 商品描述
            price: 商品价格字典，包含amount和currency
            keywords: 商品关键词
            category_id: 分类ID
            category_name: 分类名称
            state: 商品状态
            rating_value: 评分值
            rating_count: 评分数量
            specification: 商品规格
            stock_available: 可用库存
            stock_reserved: 预留库存
            created_at: 创建时间
            updated_at: 更新时间
        """
        self.id = id
        self.name = name
        self.description = description
        self.price = price
        self.keywords = keywords
        self.category_id = category_id
        self.category_name = category_name
        self.state = state
        self.rating_value = rating_value
        self.rating_count = rating_count
        self.specification = specification
        self.stock_available = stock_available
        self.stock_reserved = stock_reserved
        self.total_stock = stock_available + stock_reserved
        self.created_at = created_at
        self.updated_at = updated_at
        self.is_available = (state == "active" and stock_available > 0)
    
    @classmethod
    def from_aggregate(
        cls, 
        product_aggregate, 
        category_name: Optional[str] = None
    ) -> 'ProductDTO':
        """
        从商品聚合根创建DTO。
        
        Args:
            product_aggregate: 商品聚合根
            category_name: 分类名称
            
        Returns:
            商品DTO
        """
        product = product_aggregate.product
        
        # 安全地处理ID
        try:
            id_str = str(product.id) if product.id else None
        except:
            id_str = None
            
        # 安全地处理分类ID
        try:
            category_id_str = str(product.category_id) if product.category_id else None
        except:
            category_id_str = None
        
        return cls(
            id=id_str,
            name=product.name,
            description=product.description,
            price={
                "amount": product.price.amount,
                "currency": product.price.currency
            },
            keywords=product.keywords,
            category_id=category_id_str,
            category_name=category_name,
            state=product.state,
            rating_value=float(product_aggregate.rating.value),
            rating_count=product_aggregate.rating.count,
            specification=product_aggregate.specification.to_dict(),
            stock_available=product_aggregate.stock_available,
            stock_reserved=product_aggregate.stock_reserved,
            created_at=product.created_at,
            updated_at=product.updated_at
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """
        将DTO转换为字典。
        
        Returns:
            字典表示
        """
        # 处理价格
        price_dict = {}
        if isinstance(self.price, dict):
            price_dict = {
                "amount": str(self.price.get("amount")) if self.price.get("amount") is not None else None,
                "currency": self.price.get("currency")
            }
        else:
            price_dict = {
                "amount": None,
                "currency": None
            }
        
        # 处理日期时间
        created_at_str = None
        if self.created_at:
            try:
                created_at_str = self.created_at.isoformat()
            except:
                pass
                
        updated_at_str = None
        if self.updated_at:
            try:
                updated_at_str = self.updated_at.isoformat()
            except:
                pass
        
        # 构建响应字典
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "price": price_dict,
            "keywords": self.keywords,
            "category": {
                "id": self.category_id,
                "name": self.category_name
            } if self.category_id else None,
            "state": self.state,
            "rating": {
                "value": float(self.rating_value) if self.rating_value is not None else 0.0,
                "count": self.rating_count if self.rating_count is not None else 0
            },
            "specification": self.specification or {},
            "stock": {
                "available": self.stock_available if self.stock_available is not None else 0,
                "reserved": self.stock_reserved if self.stock_reserved is not None else 0,
                "total": (self.stock_available or 0) + (self.stock_reserved or 0)
            },
            "created_at": created_at_str,
            "updated_at": updated_at_str,
            "is_available": self.is_available
        }


class FacetValueDTO:
    """分面值DTO，表示分面中的一个选项"""
    
    def __init__(self, value: Any, count: int, selected: bool = False):
        """
        初始化分面值DTO。
        
        Args:
            value: 分面值
            count: 该值的商品数量
            selected: 该值是否被选中
        """
        self.value = value
        self.count = count
        self.selected = selected
    
    def to_dict(self) -> Dict[str, Any]:
        """
        将DTO转换为字典。
        
        Returns:
            字典表示
        """
        return {
            "value": self.value,
            "count": self.count,
            "selected": self.selected
        }


class FacetDTO:
    """分面DTO，表示一个分面及其可选值"""
    
    def __init__(
        self,
        name: str,
        display_name: str,
        values: List[FacetValueDTO],
        facet_type: str = "terms"
    ):
        """
        初始化分面DTO。
        
        Args:
            name: 分面名称（字段名）
            display_name: 分面显示名称
            values: 分面值列表
            facet_type: 分面类型，如terms（离散值）、range（范围）等
        """
        self.name = name
        self.display_name = display_name
        self.values = values
        self.facet_type = facet_type
    
    def to_dict(self) -> Dict[str, Any]:
        """
        将DTO转换为字典。
        
        Returns:
            字典表示
        """
        return {
            "name": self.name,
            "display_name": self.display_name,
            "type": self.facet_type,
            "values": [value.to_dict() for value in self.values]
        }


class ProductListDTO:
    """商品列表DTO"""
    
    def __init__(
        self,
        items: List[ProductDTO],
        total: int,
        page: int,
        page_size: int,
        facets: Optional[List[FacetDTO]] = None
    ):
        """
        初始化商品列表DTO。
        
        Args:
            items: 商品DTO列表
            total: 总数
            page: 当前页码
            page_size: 每页大小
            facets: 分面列表
        """
        self.items = items
        self.total = total
        self.page = page
        self.page_size = page_size
        self.total_pages = (total + page_size - 1) // page_size if page_size > 0 else 0
        self.has_next = page < self.total_pages
        self.has_previous = page > 1
        self.facets = facets or []
    
    def to_dict(self) -> Dict[str, Any]:
        """
        将DTO转换为字典。
        
        Returns:
            字典表示
        """
        return {
            "items": [item.to_dict() for item in self.items],
            "total": self.total,
            "page": self.page,
            "page_size": self.page_size,
            "total_pages": self.total_pages,
            "has_next": self.has_next,
            "has_previous": self.has_previous,
            "facets": [facet.to_dict() for facet in self.facets] if self.facets else []
        }


class CategoryDTO:
    """分类数据传输对象"""
    
    def __init__(
        self,
        id: str,
        name: str,
        description: str,
        parent_id: Optional[str] = None,
        parent_name: Optional[str] = None,
        children: Optional[List['CategoryDTO']] = None,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
        product_count: int = 0
    ):
        """
        初始化分类DTO。
        
        Args:
            id: 分类ID
            name: 分类名称
            description: 分类描述
            parent_id: 父分类ID
            parent_name: 父分类名称
            children: 子分类列表
            created_at: 创建时间
            updated_at: 更新时间
            product_count: 关联的商品数量
        """
        self.id = id
        self.name = name
        self.description = description
        self.parent_id = parent_id
        self.parent_name = parent_name
        self.children = children or []
        self.created_at = created_at
        self.updated_at = updated_at
        self.product_count = product_count
    
    @classmethod
    def from_value_object(
        cls, 
        category, 
        parent_name: Optional[str] = None,
        children: Optional[List['CategoryDTO']] = None,
        product_count: int = None
    ) -> 'CategoryDTO':
        """
        从分类值对象创建DTO。
        
        Args:
            category: 分类值对象
            parent_name: 父分类名称
            children: 子分类列表
            product_count: 关联的商品数量，如果为None则使用分类对象自带的product_count
            
        Returns:
            分类DTO
        """
        # 安全地处理ID
        try:
            id_str = str(category.id) if category.id else None
        except:
            id_str = None
            
        # 安全地处理父分类ID
        try:
            parent_id_str = str(category.parent_id) if category.parent_id else None
        except:
            parent_id_str = None
        
        # 获取创建时间和更新时间（如果有）
        created_at = getattr(category, 'created_at', None)
        updated_at = getattr(category, 'updated_at', None)
        
        # 如果没有提供product_count，则使用分类对象自带的product_count
        if product_count is None:
            product_count = getattr(category, 'product_count', 0)
            
        return cls(
            id=id_str,
            name=category.name,
            description=category.description,
            parent_id=parent_id_str,
            parent_name=parent_name,
            children=children,
            created_at=created_at,
            updated_at=updated_at,
            product_count=product_count
        )
    
    def to_dict(self, include_children: bool = True) -> Dict[str, Any]:
        """
        将DTO转换为字典。
        
        Args:
            include_children: 是否包含子分类
            
        Returns:
            字典表示
        """
        result = {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "parent": {
                "id": self.parent_id,
                "name": self.parent_name
            } if self.parent_id else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "product_count": self.product_count,
            "children_count": len(self.children)
        }
        
        # 构建分类路径（面包屑）
        if self.parent_id and self.parent_name:
            result["path"] = [{
                "id": self.parent_id,
                "name": self.parent_name
            }, {
                "id": self.id,
                "name": self.name
            }]
        else:
            result["path"] = [{
                "id": self.id,
                "name": self.name
            }]
        
        if include_children and self.children:
            result["children"] = [child.to_dict(include_children=False) for child in self.children]
        
        return result
