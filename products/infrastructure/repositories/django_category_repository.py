"""
基于Django ORM的分类仓储实现。
实现领域仓储接口，处理领域对象与数据库模型之间的转换。
"""
from typing import Any, List, Optional
from django.db import transaction
from loguru import logger

from products.domain import CategoryRepository, ProductCategory as DomainProductCategory
from products.infrastructure.models.product_models import ProductCategory as ProductCategoryModel


class DjangoCategoryRepository(CategoryRepository):
    """
    基于Django ORM的分类仓储实现。
    """
    
    def get_by_id(self, id: Any) -> Optional[DomainProductCategory]:
        """
        根据ID获取分类。
        
        Args:
            id: 分类ID
            
        Returns:
            找到的分类，如果不存在则返回None
        """
        try:
            category_model = ProductCategoryModel.objects.get(id=id)
            return self._to_domain_entity(category_model)
        except (ProductCategoryModel.DoesNotExist, ValueError, TypeError):
            return None
    
    def save(self, category: DomainProductCategory) -> DomainProductCategory:
        """
        保存分类。
        
        Args:
            category: 要保存的分类
            
        Returns:
            保存后的分类
        """
        with transaction.atomic():
            # 检查分类是否已存在
            if self.get_by_id(category.id):
                # 更新已有分类
                category_model = ProductCategoryModel.objects.get(id=category.id)
                category_model.name = category.name
                category_model.description = category.description
                category_model.parent_id = category.parent_id
                category_model.save()
            else:
                # 创建新分类
                category_model = ProductCategoryModel.objects.create(
                    id=category.id,
                    name=category.name,
                    description=category.description,
                    parent_id=category.parent_id
                )
            
            return self._to_domain_entity(category_model)
    
    def delete(self, category: DomainProductCategory) -> None:
        """
        删除分类。
        
        Args:
            category: 要删除的分类
        """
        try:
            with transaction.atomic():
                # 检查是否有子分类
                children = ProductCategoryModel.objects.filter(parent_id=category.id)
                if children.exists():
                    # 如果有子分类，则将子分类的父分类指向当前分类的父分类
                    children.update(parent_id=category.parent_id)
                
                # 删除分类
                ProductCategoryModel.objects.filter(id=category.id).delete()
        except ProductCategoryModel.DoesNotExist:
            pass
    
    def get_all(self) -> List[DomainProductCategory]:
        """
        获取所有分类。
        
        Returns:
            所有分类的列表
        """
        category_models = ProductCategoryModel.objects.all().order_by('name')
        return [self._to_domain_entity(model) for model in category_models]
    
    def get_children(self, parent_id: Any) -> List[DomainProductCategory]:
        """
        获取子分类。
        
        Args:
            parent_id: 父分类ID
            
        Returns:
            子分类列表
        """
        try:
            category_models = ProductCategoryModel.objects.filter(parent_id=parent_id).order_by('name')
            return [self._to_domain_entity(model) for model in category_models]
        except (ValueError, TypeError):
            return []
        except Exception as e:
            logger.error(f"获取子分类失败: {e}")
            raise
    
    def count_products_in_category(self, category_id: Any) -> int:
        """
        获取分类下的商品数量。
        
        Args:
            category_id: 分类ID
            
        Returns:
            分类下的商品数量
        """
        return self._get_product_count(category_id)
    
    def _to_domain_entity(self, category_model: ProductCategoryModel) -> DomainProductCategory:
        """
        将数据库模型转换为领域实体。
        
        Args:
            category_model: 分类数据库模型
            
        Returns:
            分类领域实体
        """
        category = DomainProductCategory(
            id=category_model.id,
            name=category_model.name,
            description=category_model.description,
            parent_id=category_model.parent_id
        )
        
        # 添加创建时间和更新时间
        category.created_at = category_model.created_at
        category.updated_at = category_model.updated_at
        
        # 添加关联的商品数量
        product_count = self._get_product_count(category_model.id)
        category.product_count = product_count
        
        # 添加调试日志
        logger.debug(f"分类 {category_model.id} ({category_model.name}) 的商品数量: {product_count}")
        
        return category
    
    def _get_product_count(self, category_id: Any) -> int:
        """
        获取分类关联的商品数量。
        
        Args:
            category_id: 分类ID
            
        Returns:
            关联的商品数量
        """
        try:
            from products.infrastructure.models.product_models import Product
            
            # 直接计算当前分类下的商品数量（不包括子分类）
            direct_count = Product.objects.filter(category_id=category_id).count()
            logger.debug(f"分类 {category_id} 直接关联的商品数量: {direct_count}")
            
            # 获取所有子分类ID
            from django.db.models import Q
            from products.infrastructure.models.product_models import ProductCategory
            
            # 获取所有子分类ID（包括子分类的子分类）
            child_ids = []
            
            def collect_child_ids(parent_id):
                children = ProductCategory.objects.filter(parent_id=parent_id)
                for child in children:
                    child_ids.append(child.id)
                    collect_child_ids(child.id)
            
            # 收集所有子分类ID
            collect_child_ids(category_id)
            
            # 如果有子分类，计算子分类下的商品数量
            child_count = 0
            if child_ids:
                child_count = Product.objects.filter(category_id__in=child_ids).count()
                logger.debug(f"分类 {category_id} 的所有子分类关联的商品数量: {child_count}")
            
            total_count = direct_count + child_count
            logger.debug(f"分类 {category_id} 的总商品数量: {total_count}")
            
            return total_count
            
        except Exception as e:
            logger.error(f"获取分类商品数量失败: {e}")
            return 0 