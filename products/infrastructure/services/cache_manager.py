"""
商品缓存管理服务。
负责缓存预热、失效和更新。
"""
import logging
from typing import List, Any, Dict, Optional, Set
import threading
import time

from django.db.models import Count, Q, F, Sum, Avg
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver

from core.infrastructure.cache import CacheService
from products.domain import ProductCategory
from products.infrastructure.models.product_models import (
    Product as ProductModel,
    ProductCategory as ProductCategoryModel,
    ProductInventory as ProductInventoryModel,
    ProductRating as ProductRatingModel
)
from products.infrastructure.repositories.django_product_repository import DjangoProductRepository


logger = logging.getLogger(__name__)


class ProductCacheManager:
    """
    商品缓存管理服务。
    负责缓存预热、失效和更新策略。
    """
    
    # 缓存键前缀
    KEY_PRODUCT = "product:"  # 单个商品缓存键前缀
    KEY_PRODUCTS_LIST = "products:list:"  # 商品列表缓存键前缀
    KEY_CATEGORY = "category:"  # 分类缓存键前缀
    KEY_SEARCH = "search:"  # 搜索结果缓存键前缀
    KEY_POPULAR = "popular:"  # 热门商品缓存键前缀
    KEY_STATS = "stats:"  # 统计数据缓存键前缀
    
    # 缓存超时时间（秒）
    TTL_PRODUCT = 3600  # 单个商品缓存1小时
    TTL_PRODUCTS_LIST = 1800  # 商品列表缓存30分钟
    TTL_CATEGORY = 7200  # 分类缓存2小时
    TTL_SEARCH = 300  # 搜索结果缓存5分钟
    TTL_POPULAR = 1800  # 热门商品缓存30分钟
    TTL_STATS = 3600  # 统计数据缓存1小时
    
    # 热门商品数量
    POPULAR_PRODUCTS_COUNT = 20
    
    def __init__(
        self, 
        cache_service: CacheService, 
        product_repository: DjangoProductRepository
    ):
        """
        初始化缓存管理服务。
        
        Args:
            cache_service: 缓存服务
            product_repository: 商品仓储
        """
        self.cache_service = cache_service
        self.product_repository = product_repository
        
        # 缓存预热标志
        self._preheated = False
        
        # 注册数据库模型变更事件处理器
        self._register_signal_handlers()
    
    def preheat_cache(self, async_preheat: bool = True):
        """
        预热缓存。
        
        Args:
            async_preheat: 是否异步预热
        """
        if async_preheat:
            # 异步预热
            threading.Thread(target=self._do_preheat_cache).start()
        else:
            # 同步预热
            self._do_preheat_cache()
    
    def _do_preheat_cache(self):
        """执行缓存预热"""
        if self._preheated:
            return
        
        logger.info("开始预热商品缓存...")
        start_time = time.time()
        
        try:
            # 1. 预热热门商品
            self._preheat_popular_products()
            
            # 2. 预热分类
            self._preheat_categories()
            
            # 3. 预热统计数据
            self._preheat_stats()
            
            # 标记为已预热
            self._preheated = True
            
            logger.info(f"商品缓存预热完成，耗时: {time.time() - start_time:.2f}秒")
        except Exception as e:
            logger.error(f"商品缓存预热失败: {e}")
    
    def _preheat_popular_products(self):
        """预热热门商品"""
        logger.info("预热热门商品...")
        
        # 获取热门商品
        try:
            popular_products = ProductModel.objects.filter(
                state=ProductModel.StateChoices.ACTIVE
            ).annotate(
                inventory_sum=Sum('inventory__available_quantity')
            ).filter(
                inventory_sum__gt=0
            ).order_by('-updated_at')[:self.POPULAR_PRODUCTS_COUNT]
            
            # 将热门商品转换为领域对象并缓存
            products = []
            for product_model in popular_products:
                # 转换为领域对象
                product_aggregate = self.product_repository._to_domain_aggregate(product_model)
                products.append(product_aggregate)
                
                # 缓存单个商品
                self.cache_service.set(
                    f"{self.KEY_PRODUCT}{product_model.id}",
                    product_aggregate,
                    self.TTL_PRODUCT
                )
            
            # 缓存热门商品列表
            self.cache_service.set(
                f"{self.KEY_POPULAR}top{self.POPULAR_PRODUCTS_COUNT}",
                products,
                self.TTL_POPULAR
            )
            
            logger.info(f"已预热{len(products)}个热门商品")
        except Exception as e:
            logger.error(f"预热热门商品失败: {e}")
    
    def _preheat_categories(self):
        """预热分类"""
        logger.info("预热商品分类...")
        
        try:
            # 获取所有分类
            categories = ProductCategoryModel.objects.all()
            
            # 缓存分类
            for category in categories:
                # 转换为领域对象
                category_entity = ProductCategory(
                    id=category.id,
                    name=category.name,
                    description=category.description,
                    parent_id=category.parent_id
                )
                
                # 缓存分类
                self.cache_service.set(
                    f"{self.KEY_CATEGORY}{category.id}",
                    category_entity,
                    self.TTL_CATEGORY
                )
            
            logger.info(f"已预热{categories.count()}个分类")
        except Exception as e:
            logger.error(f"预热分类失败: {e}")
    
    def _preheat_stats(self):
        """预热统计数据"""
        logger.info("预热统计数据...")
        
        try:
            # 计算商品总数
            total_products = ProductModel.objects.filter(
                state=ProductModel.StateChoices.ACTIVE
            ).count()
            
            # 计算分类统计
            category_stats = list(ProductModel.objects.filter(
                state=ProductModel.StateChoices.ACTIVE
            ).values('category_id').annotate(
                count=Count('id')
            ).order_by('-count'))
            
            # 计算平均价格
            avg_price = ProductModel.objects.filter(
                state=ProductModel.StateChoices.ACTIVE
            ).aggregate(avg_price=Avg('price_amount'))['avg_price'] or 0
            
            # 构建统计数据
            stats = {
                'total_products': total_products,
                'category_stats': category_stats,
                'avg_price': float(avg_price)
            }
            
            # 缓存统计数据
            self.cache_service.set(
                f"{self.KEY_STATS}all",
                stats,
                self.TTL_STATS
            )
            
            logger.info("统计数据预热完成")
        except Exception as e:
            logger.error(f"预热统计数据失败: {e}")
    
    def invalidate_product_cache(self, product_id: Any):
        """
        使单个商品缓存失效。
        
        Args:
            product_id: 商品ID
        """
        # 使商品缓存失效
        self.cache_service.delete(f"{self.KEY_PRODUCT}{product_id}")
        
        # 使相关列表缓存失效
        self._invalidate_related_caches()
        
        logger.debug(f"商品缓存已失效: {product_id}")
    
    def invalidate_category_cache(self, category_id: Any):
        """
        使分类缓存失效。
        
        Args:
            category_id: 分类ID
        """
        # 使分类缓存失效
        self.cache_service.delete(f"{self.KEY_CATEGORY}{category_id}")
        
        # 使相关列表缓存失效
        self._invalidate_related_caches()
        
        logger.debug(f"分类缓存已失效: {category_id}")
    
    def invalidate_search_cache(self, keyword: str = None):
        """
        使搜索缓存失效。
        
        Args:
            keyword: 搜索关键词，如果不提供则使所有搜索缓存失效
        """
        if keyword:
            # 使特定关键词的搜索缓存失效
            pattern = f"{self.KEY_SEARCH}*keyword:{keyword}*"
            self.cache_service.delete_pattern(pattern)
            logger.debug(f"搜索缓存已失效: {keyword}")
        else:
            # 使所有搜索缓存失效
            pattern = f"{self.KEY_SEARCH}*"
            self.cache_service.delete_pattern(pattern)
            logger.debug("所有搜索缓存已失效")
    
    def _invalidate_related_caches(self):
        """使相关列表缓存失效"""
        # 使商品列表缓存失效
        self.cache_service.delete_pattern(f"{self.KEY_PRODUCTS_LIST}*")
        
        # 使热门商品缓存失效
        self.cache_service.delete_pattern(f"{self.KEY_POPULAR}*")
        
        # 使统计数据缓存失效
        self.cache_service.delete_pattern(f"{self.KEY_STATS}*")
        
        logger.debug("相关列表缓存已失效")
    
    def get_popular_products(self, count: int = 10) -> List[Any]:
        """
        获取热门商品。
        
        Args:
            count: 返回的商品数量
            
        Returns:
            热门商品列表
        """
        # 尝试从缓存获取
        cache_key = f"{self.KEY_POPULAR}top{count}"
        cached = self.cache_service.get(cache_key)
        
        if cached:
            return cached[:count]
        
        # 如果缓存未命中，则重新计算并缓存
        try:
            popular_products = ProductModel.objects.filter(
                state=ProductModel.StateChoices.ACTIVE
            ).annotate(
                inventory_sum=Sum('inventory__available_quantity')
            ).filter(
                inventory_sum__gt=0
            ).order_by('-updated_at')[:count]
            
            # 将热门商品转换为领域对象
            products = []
            for product_model in popular_products:
                # 转换为领域对象
                product_aggregate = self.product_repository._to_domain_aggregate(product_model)
                products.append(product_aggregate)
            
            # 缓存热门商品列表
            self.cache_service.set(
                cache_key,
                products,
                self.TTL_POPULAR
            )
            
            return products
        except Exception as e:
            logger.error(f"获取热门商品失败: {e}")
            return []
    
    def _register_signal_handlers(self):
        """注册数据库模型变更事件处理器"""
        # 商品变更事件处理器
        @receiver(post_save, sender=ProductModel)
        def handle_product_save(sender, instance, **kwargs):
            self.invalidate_product_cache(instance.id)
            if kwargs.get('created', False):
                # 新创建的商品
                self._invalidate_related_caches()
        
        # 商品删除事件处理器
        @receiver(post_delete, sender=ProductModel)
        def handle_product_delete(sender, instance, **kwargs):
            self.invalidate_product_cache(instance.id)
            self._invalidate_related_caches()
        
        # 分类变更事件处理器
        @receiver(post_save, sender=ProductCategoryModel)
        def handle_category_save(sender, instance, **kwargs):
            self.invalidate_category_cache(instance.id)
            self._invalidate_related_caches()
        
        # 库存变更事件处理器
        @receiver(post_save, sender=ProductInventoryModel)
        def handle_inventory_save(sender, instance, **kwargs):
            self.invalidate_product_cache(instance.product_id)
            self._invalidate_related_caches()
        
        # 评分变更事件处理器
        @receiver(post_save, sender=ProductRatingModel)
        def handle_rating_save(sender, instance, **kwargs):
            self.invalidate_product_cache(instance.product_id)
            self._invalidate_related_caches() 