"""
商品仓储的Django实现。
"""
from typing import Any, Dict, List, Optional, Tuple
from decimal import Decimal
import uuid
from django.db import transaction
from django.db.models import Q, Count

from products.domain.repositories import ProductRepository
from products.domain.aggregates import ProductAggregate
from products.domain.entities import Product
from products.domain.value_objects import Rating, ProductSpecification as DomainProductSpecification
from core.domain.value_objects import Money
from core.domain.events import DomainEvents

from products.infrastructure.models.product_models import (
    Product as ProductModel,
    ProductSpecification as ProductSpecificationModel,
    ProductInventory as ProductInventoryModel,
    ProductRating as ProductRatingModel
)


class DjangoProductRepository(ProductRepository):
    """
    基于Django ORM的商品仓储实现。
    """
    
    def get_by_id(self, id: Any) -> Optional[ProductAggregate]:
        """
        根据ID获取商品聚合根。
        
        Args:
            id: 商品ID
            
        Returns:
            找到的商品聚合根，如果不存在则返回None
        """
        try:
            # 确保id是字符串
            id_str = str(id)
            
            # 使用select_related优化查询，减少数据库访问次数
            product_model = ProductModel.objects.select_related(
                'specification', 
                'inventory', 
                'rating'
            ).get(id=id_str)
            
            return self._to_domain_aggregate(product_model)
        except (ProductModel.DoesNotExist, ValueError, TypeError):
            return None
    
    def save(self, product_aggregate: ProductAggregate) -> ProductAggregate:
        """
        保存商品聚合根。
        
        Args:
            product_aggregate: 要保存的商品聚合根
            
        Returns:
            保存后的商品聚合根
        """
        with transaction.atomic():
            # 获取商品实体和相关数据
            product_entity = product_aggregate.product
            specification = product_aggregate.specification
            stock_available = product_aggregate.stock_available
            stock_reserved = product_aggregate.stock_reserved
            rating = product_aggregate.rating
            
            # 转换为数据库模型
            if self.get_by_id(product_entity.id):
                # 更新已有商品
                product_model = ProductModel.objects.select_for_update().get(id=product_entity.id)
                
                # 更新商品基本信息
                product_model.name = product_entity.name
                product_model.description = product_entity.description
                product_model.price_amount = product_entity.price.amount
                product_model.price_currency = product_entity.price.currency
                product_model.keywords = product_entity.keywords
                product_model.category_id = product_entity.category_id
                product_model.state = product_entity.state
                product_model.version = product_entity.version
                product_model.save()
            else:
                # 创建新商品
                product_model = ProductModel.objects.create(
                    id=product_entity.id,
                    name=product_entity.name,
                    description=product_entity.description,
                    price_amount=product_entity.price.amount,
                    price_currency=product_entity.price.currency,
                    keywords=product_entity.keywords,
                    category_id=product_entity.category_id,
                    state=product_entity.state,
                    version=product_entity.version
                )
            
            # 更新或创建商品规格
            spec_model, _ = ProductSpecificationModel.objects.update_or_create(
                product=product_model,
                defaults={
                    'attributes': specification.to_dict()
                }
            )
            
            # 更新或创建商品库存
            inventory_model, _ = ProductInventoryModel.objects.update_or_create(
                product=product_model,
                defaults={
                    'available_quantity': stock_available,
                    'reserved_quantity': stock_reserved,
                    'version': product_aggregate.version
                }
            )
            
            # 更新或创建商品评分
            rating_model, _ = ProductRatingModel.objects.update_or_create(
                product=product_model,
                defaults={
                    'rating_value': rating.value,
                    'rating_count': rating.count
                }
            )
            
            # 发布领域事件
            for event in product_aggregate._domain_events:
                DomainEvents.publish(event)
            
            # 清空待发布的领域事件
            product_aggregate.clear_domain_events()
            
            return product_aggregate
    
    def delete(self, product_aggregate: ProductAggregate) -> None:
        """
        删除商品聚合根。
        在DDD中，我们通常不会物理删除数据，而是标记为已删除状态。
        
        Args:
            product_aggregate: 要删除的商品聚合根
        """
        product_entity = product_aggregate.product
        
        try:
            with transaction.atomic():
                product_model = ProductModel.objects.select_for_update().get(id=product_entity.id)
                product_model.state = ProductModel.StateChoices.DELETED
                product_model.save()
                
                # 发布领域事件
                for event in product_aggregate._domain_events:
                    DomainEvents.publish(event)
                
                # 清空待发布的领域事件
                product_aggregate.clear_domain_events()
        except ProductModel.DoesNotExist:
            pass
    
    def list(self, skip: int = 0, limit: int = 100) -> Tuple[List[ProductAggregate], int]:
        """
        获取商品列表。
        
        Args:
            skip: 跳过的记录数
            limit: 返回的最大记录数
            
        Returns:
            商品聚合根列表和总数的元组
        """
        # 构建基本查询集
        queryset = ProductModel.objects.select_related(
            'specification', 
            'inventory', 
            'rating'
        ).filter(
            state__in=[
                ProductModel.StateChoices.DRAFT,
                ProductModel.StateChoices.ACTIVE,
                ProductModel.StateChoices.INACTIVE
            ]
        )
        
        # 计算总数
        total = queryset.count()
        
        # 分页并排序
        product_models = queryset.order_by('-updated_at')[skip:skip+limit]
        
        # 转换为领域聚合
        products = [self._to_domain_aggregate(model) for model in product_models]
        
        return products, total
    
    def search(
        self, 
        keyword: str, 
        filters: Optional[Dict[str, Any]] = None,
        page: int = 1,
        page_size: int = 20,
        include_facets: bool = False,
        facet_fields: Optional[List[str]] = None
    ) -> Tuple[List[ProductAggregate], int, Optional[Dict[str, Any]]]:
        """
        搜索商品。
        
        Args:
            keyword: 搜索关键词
            filters: 过滤条件
            page: 页码
            page_size: 每页大小
            include_facets: 是否包含分面结果
            facet_fields: 需要聚合的分面字段列表
            
        Returns:
            商品聚合根列表、总数和分面结果的元组
        """
        # 计算偏移量
        offset = (page - 1) * page_size
        
        # 构建查询
        queryset = ProductModel.objects.select_related(
            'specification', 
            'inventory', 
            'rating'
        ).filter(
            state=ProductModel.StateChoices.ACTIVE
        )
        
        # 关键词搜索
        if keyword:
            queryset = queryset.filter(
                Q(name__icontains=keyword) | 
                Q(keywords__icontains=keyword) |
                Q(description__icontains=keyword)
            )
        
        # 应用过滤器
        if filters:
            if 'category_id' in filters:
                queryset = queryset.filter(category_id=filters['category_id'])
            
            if 'min_price' in filters:
                queryset = queryset.filter(price_amount__gte=filters['min_price'])
            
            if 'max_price' in filters:
                queryset = queryset.filter(price_amount__lte=filters['max_price'])
            
            # 处理分面选择的过滤条件
            for key, values in filters.items():
                if key.startswith('facet_'):
                    field_name = key[6:]  # 移除'facet_'前缀
                    if field_name == 'rating_value':
                        # 评分过滤需要特殊处理
                        rating_values = [float(v) for v in values if v.replace('.', '', 1).isdigit()]
                        if rating_values:
                            queryset = queryset.filter(rating__rating_value__in=rating_values)
                    elif field_name == 'price':
                        # 价格区间过滤需要特殊处理
                        for price_range in values:
                            try:
                                min_price, max_price = price_range.split('-')
                                if min_price and min_price != '0':
                                    queryset = queryset.filter(price_amount__gte=min_price)
                                if max_price and max_price != 'max':
                                    queryset = queryset.filter(price_amount__lte=max_price)
                            except ValueError:
                                continue
        
        # 计算总数
        total = queryset.count()
        
        # 获取分面数据
        facet_data = None
        if include_facets:
            facet_data = self._get_facet_data(queryset, facet_fields or ['category_id', 'price', 'rating_value'])
        
        # 分页
        product_models = queryset.order_by('-updated_at')[offset:offset+page_size]
        
        # 转换为领域聚合
        products = [self._to_domain_aggregate(model) for model in product_models]
        
        return products, total, facet_data
    
    def _get_facet_data(self, queryset, facet_fields: List[str]) -> Dict[str, Any]:
        """
        获取分面数据。
        
        Args:
            queryset: 查询集
            facet_fields: 需要聚合的字段列表
            
        Returns:
            分面数据字典
        """
        facet_data = {}
        
        # 分类分面
        if 'category_id' in facet_fields:
            category_counts = queryset.values('category_id').annotate(
                count=Count('category_id')
            ).order_by('-count')
            
            facet_data['category_id'] = {
                str(item['category_id']): item['count']
                for item in category_counts if item['category_id']
            }
        
        # 价格区间分面
        if 'price' in facet_fields:
            # 定义价格区间
            price_ranges = [
                (0, 100, '0-100'),
                (100, 500, '100-500'),
                (500, 1000, '500-1000'),
                (1000, 5000, '1000-5000'),
                (5000, None, '5000-max')
            ]
            
            price_facets = {}
            for min_price, max_price, range_key in price_ranges:
                q_filter = Q(price_amount__gte=min_price)
                if max_price is not None:
                    q_filter &= Q(price_amount__lt=max_price)
                    
                count = queryset.filter(q_filter).count()
                if count > 0:
                    price_facets[range_key] = count
                    
            facet_data['price'] = price_facets
        
        # 评分分面
        if 'rating_value' in facet_fields:
            rating_counts = queryset.values('rating__rating_value').annotate(
                count=Count('rating__rating_value')
            ).order_by('-rating__rating_value')
            
            facet_data['rating_value'] = {
                str(item['rating__rating_value']): item['count']
                for item in rating_counts if item['rating__rating_value'] is not None
            }
        
        return facet_data
    
    def find_by_category(
        self,
        category_id: Any,
        page: int = 1,
        page_size: int = 20
    ) -> Tuple[List[ProductAggregate], int]:
        """
        按分类查找商品。
        
        Args:
            category_id: 分类ID
            page: 页码
            page_size: 每页大小
            
        Returns:
            商品聚合根列表和总数的元组
        """
        # 计算偏移量
        offset = (page - 1) * page_size
        
        # 构建查询
        try:
            queryset = ProductModel.objects.select_related(
                'specification', 
                'inventory', 
                'rating'
            ).filter(
                category_id=category_id,
                state=ProductModel.StateChoices.ACTIVE
            )
            
            # 计算总数
            total = queryset.count()
            
            # 分页
            product_models = queryset.order_by('-updated_at')[offset:offset+page_size]
            
            # 转换为领域聚合
            products = [self._to_domain_aggregate(model) for model in product_models]
            
            return products, total
        except (ValueError, TypeError):
            # 处理无效的category_id
            return [], 0
    
    def find_by_keyword(
        self,
        keyword: str,
        page: int = 1,
        page_size: int = 20
    ) -> Tuple[List[ProductAggregate], int]:
        """
        按关键词查找商品。
        
        Args:
            keyword: 关键词
            page: 页码
            page_size: 每页大小
            
        Returns:
            商品聚合根列表和总数的元组
        """
        # 计算偏移量
        offset = (page - 1) * page_size
        
        # 构建查询
        queryset = ProductModel.objects.select_related(
            'specification', 
            'inventory', 
            'rating'
        ).filter(
            Q(name__icontains=keyword) | 
            Q(keywords__icontains=keyword),
            state=ProductModel.StateChoices.ACTIVE
        )
        
        # 计算总数
        total = queryset.count()
        
        # 分页
        product_models = queryset.order_by('-updated_at')[offset:offset+page_size]
        
        # 转换为领域聚合
        products = [self._to_domain_aggregate(model) for model in product_models]
        
        return products, total
    
    def _to_domain_aggregate(self, product_model: ProductModel) -> ProductAggregate:
        """
        将数据库模型转换为领域聚合根。
        
        Args:
            product_model: 商品数据库模型
            
        Returns:
            商品领域聚合根
        """
        # 创建商品实体
        product = Product(
            id=product_model.id,
            name=product_model.name,
            description=product_model.description,
            price=Money(product_model.price_amount, product_model.price_currency),
            keywords=product_model.keywords,
            category_id=product_model.category_id
        )
        
        # 设置商品状态
        product.state = product_model.state
        
        # 设置时间戳
        product.created_at = product_model.created_at
        product.updated_at = product_model.updated_at
        
        # 获取规格
        specification = DomainProductSpecification({})
        if hasattr(product_model, 'specification') and product_model.specification:
            specification = DomainProductSpecification(
                product_model.specification.attributes
            )
        
        # 获取库存
        stock_available = 0
        stock_reserved = 0
        if hasattr(product_model, 'inventory') and product_model.inventory:
            stock_available = product_model.inventory.available_quantity
            stock_reserved = product_model.inventory.reserved_quantity
        
        # 获取评分
        rating = Rating.zero()
        if hasattr(product_model, 'rating') and product_model.rating:
            rating = Rating(
                product_model.rating.rating_value,
                product_model.rating.rating_count
            )
        
        # 创建聚合根
        product_aggregate = ProductAggregate(
            product=product,
            specification=specification,
            stock_available=stock_available,
            stock_reserved=stock_reserved,
            rating=rating
        )
        
        # 设置版本号 - 使用循环调用increment_version方法
        for _ in range(product_model.version):
            product_aggregate.increment_version()
        
        return product_aggregate
    
    def batch_get(self, ids: List[Any]) -> List[ProductAggregate]:
        """
        批量获取商品聚合根。
        
        Args:
            ids: 商品ID列表
            
        Returns:
            商品聚合根列表
        """
        if not ids:
            return []
        
        # 确保所有ID都是字符串
        id_strs = [str(id_) for id_ in ids]
        
        # 使用select_related优化查询，减少数据库访问次数
        product_models = ProductModel.objects.select_related(
            'specification', 
            'inventory', 
            'rating'
        ).filter(id__in=id_strs)
        
        # 按输入的ID顺序返回结果
        result_map = {str(model.id): self._to_domain_aggregate(model) for model in product_models}
        return [result_map.get(str(id_)) for id_ in ids if str(id_) in result_map]
    
    def batch_save(self, product_aggregates: List[ProductAggregate]) -> List[ProductAggregate]:
        """
        批量保存商品聚合根。
        
        Args:
            product_aggregates: 要保存的商品聚合根列表
            
        Returns:
            保存后的商品聚合根列表
        """
        if not product_aggregates:
            return []
        
        result = []
        
        with transaction.atomic():
            for product_aggregate in product_aggregates:
                saved_aggregate = self.save(product_aggregate)
                result.append(saved_aggregate)
        
        return result
    
    def batch_search(
        self,
        keywords: List[str],
        filters: Optional[Dict[str, Any]] = None,
        page: int = 1,
        page_size: int = 20
    ) -> Dict[str, Tuple[List[ProductAggregate], int]]:
        """
        批量搜索商品。
        
        Args:
            keywords: 搜索关键词列表
            filters: 过滤条件
            page: 页码
            page_size: 每页大小
            
        Returns:
            关键词到商品列表和总数的映射
        """
        if not keywords:
            return {}
        
        result = {}
        
        for keyword in keywords:
            products, total = self.search(keyword, filters, page, page_size)
            result[keyword] = (products, total)
        
        return result
    
    def bulk_update_stock(self, stock_updates: List[Tuple[Any, int, int]]) -> List[Tuple[Any, bool]]:
        """
        批量更新库存。
        
        Args:
            stock_updates: (商品ID, 可用数量, 预留数量)的元组列表
            
        Returns:
            (商品ID, 是否成功)的元组列表
        """
        if not stock_updates:
            return []
        
        result = []
        
        with transaction.atomic():
            for product_id, available, reserved in stock_updates:
                try:
                    # 获取库存记录
                    inventory = ProductInventoryModel.objects.select_for_update().get(product_id=product_id)
                    
                    # 更新库存
                    inventory.available_quantity = available
                    inventory.reserved_quantity = reserved
                    inventory.version += 1
                    inventory.save()
                    
                    result.append((product_id, True))
                except ProductInventoryModel.DoesNotExist:
                    try:
                        # 检查商品是否存在
                        if not ProductModel.objects.filter(id=product_id).exists():
                            result.append((product_id, False))
                            continue
                        
                        # 创建库存记录
                        ProductInventoryModel.objects.create(
                            product_id=product_id,
                            available_quantity=available,
                            reserved_quantity=reserved,
                            version=0
                        )
                        
                        result.append((product_id, True))
                    except Exception:
                        result.append((product_id, False))
                except Exception:
                    result.append((product_id, False))
        
        return result
    
    def bulk_update_prices(self, price_updates: List[Tuple[Any, Decimal, str]]) -> List[Tuple[Any, bool]]:
        """
        批量更新价格。
        
        Args:
            price_updates: (商品ID, 价格金额, 价格货币)的元组列表
            
        Returns:
            (商品ID, 是否成功)的元组列表
        """
        if not price_updates:
            return []
        
        result = []
        
        with transaction.atomic():
            for product_id, price_amount, price_currency in price_updates:
                try:
                    # 获取商品记录
                    product = ProductModel.objects.select_for_update().get(id=product_id)
                    
                    # 更新价格
                    product.price_amount = price_amount
                    product.price_currency = price_currency
                    product.version += 1
                    product.save()
                    
                    result.append((product_id, True))
                except ProductModel.DoesNotExist:
                    result.append((product_id, False))
                except Exception:
                    result.append((product_id, False))
        
        return result
    
    def bulk_update_state(self, state_updates: List[Tuple[Any, str]]) -> List[Tuple[Any, bool]]:
        """
        批量更新商品状态。
        
        Args:
            state_updates: (商品ID, 状态)的元组列表
            
        Returns:
            (商品ID, 是否成功)的元组列表
        """
        if not state_updates:
            return []
        
        result = []
        
        with transaction.atomic():
            for product_id, state in state_updates:
                try:
                    # 验证状态值
                    if state not in [choice[0] for choice in ProductModel.StateChoices.choices]:
                        result.append((product_id, False))
                        continue
                    
                    # 获取商品记录
                    product = ProductModel.objects.select_for_update().get(id=product_id)
                    
                    # 更新状态
                    product.state = state
                    product.version += 1
                    product.save()
                    
                    result.append((product_id, True))
                except ProductModel.DoesNotExist:
                    result.append((product_id, False))
                except Exception:
                    result.append((product_id, False))
        
        return result 