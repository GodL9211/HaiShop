"""
商品领域模型中的值对象。
包含商品相关的值对象定义。
"""
from typing import Any, Dict, List, Optional
from decimal import Decimal

from core.domain import ValueObject


class ProductCategory(ValueObject):
    """
    商品分类值对象。
    表示商品所属的分类。
    """
    
    def __init__(
        self,
        id: Any,
        name: str,
        description: str = "",
        parent_id: Optional[Any] = None
    ):
        """
        初始化商品分类值对象。
        
        Args:
            id: 分类ID
            name: 分类名称
            description: 分类描述
            parent_id: 父分类ID，如果没有则为None
        """
        self.id = id
        self.name = name
        self.description = description
        self.parent_id = parent_id
        
        # 这些属性将由仓储层设置
        self.created_at = None
        self.updated_at = None
        self.product_count = 0
    
    def to_dict(self) -> Dict[str, Any]:
        """
        将分类转换为字典表示。
        
        Returns:
            分类的字典表示
        """
        try:
            id_str = str(self.id) if self.id else None
        except:
            id_str = None
            
        try:
            parent_id_str = str(self.parent_id) if self.parent_id else None
        except:
            parent_id_str = None
            
        result = {
            "id": id_str,
            "name": self.name,
            "description": self.description,
            "parent_id": parent_id_str
        }
        
        # 添加可选属性（如果存在）
        if hasattr(self, 'created_at') and self.created_at:
            result["created_at"] = self.created_at
        
        if hasattr(self, 'updated_at') and self.updated_at:
            result["updated_at"] = self.updated_at
        
        if hasattr(self, 'product_count'):
            result["product_count"] = self.product_count
            
        return result


class ProductSpecification(ValueObject):
    """
    商品规格值对象。
    表示商品的规格信息，如尺寸、颜色等。
    """
    
    def __init__(self, attributes: Dict[str, Any]):
        """
        初始化商品规格值对象。
        
        Args:
            attributes: 规格属性字典，如 {"color": "红色", "size": "M"}
        """
        self.attributes = attributes
    
    def get_attribute(self, key: str, default: Any = None) -> Any:
        """
        获取规格属性值。
        
        Args:
            key: 属性名
            default: 默认值，如果属性不存在则返回
            
        Returns:
            属性值或默认值
        """
        return self.attributes.get(key, default)
    
    def has_attribute(self, key: str) -> bool:
        """
        检查是否存在指定属性。
        
        Args:
            key: 属性名
            
        Returns:
            如果存在该属性则返回True，否则返回False
        """
        return key in self.attributes
    
    def to_dict(self) -> Dict[str, Any]:
        """
        将规格转换为字典表示。
        
        Returns:
            规格的字典表示
        """
        return self.attributes.copy()


class Rating(ValueObject):
    """
    商品评分值对象。
    表示商品的评分信息。
    """
    
    def __init__(self, value: Decimal, count: int = 0):
        """
        初始化商品评分值对象。
        
        Args:
            value: 评分值，范围1-5
            count: 评分数量
        """
        if not (0 <= value <= 5):
            raise ValueError("评分值必须在0到5之间")
        
        self.value = Decimal(value)
        self.count = count
    
    @classmethod
    def zero(cls) -> 'Rating':
        """
        创建零评分。
        
        Returns:
            零评分的Rating对象
        """
        return cls(Decimal('0'), 0)
    
    def add_rating(self, new_rating: Decimal) -> 'Rating':
        """
        添加新评分，计算新的平均评分。
        
        Args:
            new_rating: 新的评分值
            
        Returns:
            新的Rating对象
            
        Raises:
            ValueError: 如果新评分值不在1-5范围内
        """
        if not (1 <= new_rating <= 5):
            raise ValueError("评分值必须在1到5之间")
        
        new_count = self.count + 1
        new_value = ((self.value * self.count) + new_rating) / new_count
        return Rating(new_value, new_count)
    
    def to_dict(self) -> Dict[str, Any]:
        """
        将评分转换为字典表示。
        
        Returns:
            评分的字典表示
        """
        return {
            "value": float(self.value),
            "count": self.count
        }
    
    def __str__(self) -> str:
        """
        返回评分的字符串表示。
        
        Returns:
            评分的字符串表示
        """
        return f"{self.value:.1f} ({self.count})"


class SearchFacet:
    """
    搜索面板值对象。
    代表搜索结果的一个分面(facet)，如分类、价格范围等。
    """
    
    def __init__(self, name: str, display_name: str, items: list):
        """
        初始化搜索面板。
        
        Args:
            name: 面板名称
            display_name: 面板显示名称
            items: 面板项列表
        """
        self.name = name
        self.display_name = display_name
        self.items = items


class SearchQuery:
    """
    搜索查询值对象。
    封装搜索查询参数。
    """
    
    def __init__(
        self,
        keyword: str,
        filters: dict = None,
        page: int = 1,
        page_size: int = 20
    ):
        """
        初始化搜索查询。
        
        Args:
            keyword: 搜索关键词
            filters: 过滤条件
            page: 页码
            page_size: 每页大小
        """
        self.keyword = keyword
        self.filters = filters or {}
        self.page = max(1, page)  # 确保页码至少为1
        self.page_size = min(100, max(1, page_size))  # 限制页大小范围
    
    def get_cache_key(self) -> str:
        """
        生成缓存键。
        
        Returns:
            缓存键
        """
        key_parts = [
            f"search:{self.keyword}",
            f"page:{self.page}:{self.page_size}"
        ]
        
        for k, v in sorted(self.filters.items()):
            key_parts.append(f"{k}:{v}")
        
        return ":".join(key_parts)


class SearchResult:
    """
    搜索结果值对象。
    封装搜索结果数据。
    """
    
    def __init__(
        self,
        items: list,
        total: int,
        page: int,
        page_size: int,
        facets: dict = None
    ):
        """
        初始化搜索结果。
        
        Args:
            items: 结果项列表
            total: 总结果数
            page: 当前页码
            page_size: 每页大小
            facets: 搜索面板
        """
        self.items = items
        self.total = total
        self.page = page
        self.page_size = page_size
        self.facets = facets or {}
