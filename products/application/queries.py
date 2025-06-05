"""
商品应用服务层的查询对象。
定义用于查询系统状态的查询。
"""
from typing import Any, Dict, Optional, List
from decimal import Decimal


class GetProductQuery:
    """获取单个商品的查询"""
    
    def __init__(self, id: str):
        """
        初始化获取商品查询。
        
        Args:
            id: 商品ID
        """
        self.id = id


class ListProductsQuery:
    """获取商品列表的查询"""
    
    def __init__(
        self,
        page: int = 1,
        page_size: int = 20,
        active_only: bool = True,
        sort_by: str = "updated_at",
        sort_direction: str = "desc",
        category_id: Optional[str] = None
    ):
        """
        初始化商品列表查询。
        
        Args:
            page: 页码
            page_size: 每页大小
            active_only: 是否只返回激活状态的商品
            sort_by: 排序字段
            sort_direction: 排序方向，'asc'或'desc'
            category_id: 分类ID过滤
        """
        self.page = max(1, page)  # 确保页码至少为1
        self.page_size = min(100, max(1, page_size))  # 限制页大小范围
        self.active_only = active_only
        self.sort_by = sort_by
        self.sort_direction = sort_direction
        self.category_id = category_id


class SearchProductsQuery:
    """搜索商品的查询"""
    
    def __init__(
        self,
        keyword: str,
        category_id: Optional[str] = None,
        min_price: Optional[Decimal] = None,
        max_price: Optional[Decimal] = None,
        page: int = 1,
        page_size: int = 20,
        sort_by: str = "relevance",
        sort_direction: str = "desc",
        include_facets: bool = True,
        facet_fields: Optional[List[str]] = None,
        selected_facets: Optional[Dict[str, List[str]]] = None
    ):
        """
        初始化搜索商品查询。
        
        Args:
            keyword: 搜索关键词
            category_id: 分类ID过滤
            min_price: 最低价格过滤
            max_price: 最高价格过滤
            page: 页码
            page_size: 每页大小
            sort_by: 排序字段
            sort_direction: 排序方向，'asc'或'desc'
            include_facets: 是否包含分面结果
            facet_fields: 需要聚合的分面字段列表
            selected_facets: 已选择的分面值，格式为{字段名: [选中的值列表]}
        """
        self.keyword = keyword
        self.category_id = category_id
        self.min_price = min_price
        self.max_price = max_price
        self.page = max(1, page)  # 确保页码至少为1
        self.page_size = min(100, max(1, page_size))  # 限制页大小范围
        self.sort_by = sort_by
        self.sort_direction = sort_direction
        self.include_facets = include_facets
        # 默认分面字段
        self.facet_fields = facet_fields or ["category_id", "price", "rating_value"]
        self.selected_facets = selected_facets or {}
    
    def get_filters(self) -> Dict[str, Any]:
        """
        获取过滤条件字典。
        
        Returns:
            过滤条件字典
        """
        filters = {}
        if self.category_id:
            filters["category_id"] = self.category_id
        if self.min_price is not None:
            filters["min_price"] = self.min_price
        if self.max_price is not None:
            filters["max_price"] = self.max_price
        
        # 添加已选择的分面值作为过滤条件
        if self.selected_facets:
            for field, values in self.selected_facets.items():
                if values:
                    filters[f"facet_{field}"] = values
        
        return filters
    
    def get_cache_key(self) -> str:
        """
        生成缓存键。
        
        Returns:
            缓存键字符串
        """
        key_parts = [
            f"search:{self.keyword}",
            f"cat:{self.category_id or 'all'}",
            f"price:{self.min_price or 0}-{self.max_price or 'max'}",
            f"page:{self.page}:{self.page_size}",
            f"sort:{self.sort_by}:{self.sort_direction}"
        ]
        
        # 添加已选择的分面值到缓存键
        if self.selected_facets:
            for field, values in self.selected_facets.items():
                if values:
                    key_parts.append(f"facet_{field}:{'-'.join(values)}")
        
        return ":".join(key_parts)


class GetProductsByIdsQuery:
    """根据ID列表获取多个商品的查询"""
    
    def __init__(self, ids: list[str]):
        """
        初始化根据ID列表获取商品查询。
        
        Args:
            ids: 商品ID列表
        """
        self.ids = ids


class GetRelatedProductsQuery:
    """获取相关商品的查询"""
    
    def __init__(self, product_id: str, limit: int = 5):
        """
        初始化获取相关商品查询。
        
        Args:
            product_id: 商品ID
            limit: 返回的最大数量
        """
        self.product_id = product_id
        self.limit = min(20, max(1, limit))  # 限制数量范围


class GetCategoryQuery:
    """获取单个分类的查询"""
    
    def __init__(self, id: str):
        """
        初始化获取分类查询。
        
        Args:
            id: 分类ID
        """
        self.id = id


class ListCategoriesQuery:
    """获取分类列表的查询"""
    
    def __init__(
        self,
        include_tree: bool = False,
        parent_id: Optional[str] = None
    ):
        """
        初始化分类列表查询。
        
        Args:
            include_tree: 是否包含子分类树结构
            parent_id: 父分类ID，如果提供则只返回该分类的子分类
        """
        self.include_tree = include_tree
        self.parent_id = parent_id

