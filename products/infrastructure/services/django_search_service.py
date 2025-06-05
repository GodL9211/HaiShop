"""
基于Django的商品搜索服务实现。
结合缓存和数据库实现高效的商品搜索功能。
"""
from typing import Dict, Any, Tuple, List, Optional
from decimal import Decimal
from django.db.models import Q, Count, Avg

from core.infrastructure.cache import CacheService
from core.domain.exceptions import DomainException
from products.domain import (
    SearchService, 
    ProductAggregate, 
    SearchQuery, 
    SearchResult, 
    SearchFacet
)
from products.infrastructure.repositories.django_product_repository import DjangoProductRepository


class DjangoSearchService(SearchService):
    """
    基于Django的商品搜索服务实现。
    """
    
    def __init__(self, product_repository: DjangoProductRepository, cache_service: CacheService):
        """
        初始化搜索服务。
        
        Args:
            product_repository: 商品仓储
            cache_service: 缓存服务
        """
        self.product_repository = product_repository
        self.cache_service = cache_service
    
    def search(self, query: SearchQuery) -> SearchResult:
        """
        搜索商品。
        
        Args:
            query: 搜索查询对象
            
        Returns:
            搜索结果
        """
        # 尝试从缓存获取
        cache_key = self._get_cache_key(query)
        cached_result = self.cache_service.get(cache_key)
        if cached_result:
            return cached_result
        
        try:
            # 执行搜索
            products, total = self.product_repository.search(
                query.keyword,
                query.filters,
                query.page,
                query.page_size
            )
            
            # 计算搜索面板(facets)
            facets = self._calculate_facets(query)
            
            # 创建搜索结果
            result = SearchResult(
                items=products,
                total=total,
                page=query.page,
                page_size=query.page_size,
                facets=facets
            )
            
            # 缓存结果
            self.cache_service.set(cache_key, result, ttl=300)  # 5分钟缓存
            
            return result
        except Exception as e:
            raise DomainException(f"搜索失败: {str(e)}")
    
    def _get_cache_key(self, query: SearchQuery) -> str:
        """
        生成缓存键。
        
        Args:
            query: 搜索查询对象
            
        Returns:
            缓存键
        """
        # 构建基础缓存键
        key_parts = [
            f"search",
            f"keyword:{query.keyword}",
            f"page:{query.page}",
            f"size:{query.page_size}"
        ]
        
        # 添加过滤条件
        if query.filters:
            for k, v in sorted(query.filters.items()):
                key_parts.append(f"{k}:{v}")
        
        return ":".join(key_parts)
    
    def _calculate_facets(self, query: SearchQuery) -> Dict[str, SearchFacet]:
        """
        计算搜索面板(facets)。
        
        Args:
            query: 搜索查询对象
            
        Returns:
            搜索面板
        """
        from products.infrastructure.models.product_models import (
            Product as ProductModel,
            ProductCategory as ProductCategoryModel
        )
        
        # 基础查询
        base_queryset = ProductModel.objects.filter(state=ProductModel.StateChoices.ACTIVE)
        
        # 应用关键词过滤
        if query.keyword:
            base_queryset = base_queryset.filter(
                Q(name__icontains=query.keyword) | 
                Q(keywords__icontains=query.keyword) |
                Q(description__icontains=query.keyword)
            )
        
        # 计算分类面板
        category_facet = self._calculate_category_facet(base_queryset)
        
        # 计算价格范围面板
        price_facet = self._calculate_price_facet(base_queryset)
        
        # 返回所有面板
        return {
            'category': category_facet,
            'price': price_facet
        }
    
    def _calculate_category_facet(self, queryset) -> SearchFacet:
        """
        计算分类面板。
        
        Args:
            queryset: 基础查询集
            
        Returns:
            分类面板
        """
        from products.infrastructure.models.product_models import ProductCategory as ProductCategoryModel
        
        # 获取分类统计
        category_counts = queryset.values('category_id').annotate(
            count=Count('id')
        ).order_by('-count')
        
        # 获取分类信息
        facet_items = []
        for item in category_counts[:10]:  # 最多显示10个分类
            category_id = item['category_id']
            if category_id:
                try:
                    category = ProductCategoryModel.objects.get(id=category_id)
                    facet_items.append({
                        'value': str(category_id),
                        'label': category.name,
                        'count': item['count']
                    })
                except ProductCategoryModel.DoesNotExist:
                    pass
        
        return SearchFacet(
            name='category',
            display_name='分类',
            items=facet_items
        )
    
    def _calculate_price_facet(self, queryset) -> SearchFacet:
        """
        计算价格范围面板。
        
        Args:
            queryset: 基础查询集
            
        Returns:
            价格范围面板
        """
        # 获取价格统计
        price_stats = queryset.aggregate(
            min_price=Avg('price_amount') * 0.5,  # 最低价格约为平均价格的一半
            max_price=Avg('price_amount') * 1.5   # 最高价格约为平均价格的1.5倍
        )
        
        min_price = int(price_stats['min_price'] or 0)
        max_price = int(price_stats['max_price'] or 1000)
        
        # 计算价格区间
        step = (max_price - min_price) / 4  # 将价格分为4个区间
        
        facet_items = []
        for i in range(4):
            range_start = min_price + i * step
            range_end = min_price + (i + 1) * step
            
            # 统计该价格区间的商品数量
            count = queryset.filter(
                price_amount__gte=range_start,
                price_amount__lt=range_end if i < 3 else max_price + 1  # 最后一个区间包含最大值
            ).count()
            
            facet_items.append({
                'value': f"{int(range_start)}-{int(range_end)}",
                'label': f"¥{int(range_start)} - ¥{int(range_end)}",
                'count': count
            })
        
        return SearchFacet(
            name='price',
            display_name='价格区间',
            items=facet_items
        ) 