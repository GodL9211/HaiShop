"""
商品应用服务。
定义商品相关的应用层服务，处理命令和查询，协调领域层和基础设施层。
"""
from typing import Any, Dict, List, Optional
from decimal import Decimal

from loguru import logger
from core.domain import Money
from core.infrastructure.transaction import TransactionManager
from core.infrastructure.cache import CacheService

from products.domain.services import ProductService
from products.domain.repositories import ProductRepository, CategoryRepository
from products.domain.value_objects import ProductCategory, ProductSpecification
from products.application.dtos import (
    ProductDTO, 
    ProductListDTO, 
    CategoryDTO,
    FacetDTO,
    FacetValueDTO
)
from products.application.commands import (
    CreateProductCommand,
    UpdateProductCommand,
    ChangeProductStateCommand,
    UpdateProductStockCommand,
    AddProductRatingCommand,
    CreateCategoryCommand,
    UpdateCategoryCommand,
    DeleteCategoryCommand
)
from products.application.queries import (
    GetProductQuery,
    ListProductsQuery,
    SearchProductsQuery,
    GetProductsByIdsQuery,
    GetRelatedProductsQuery,
    GetCategoryQuery,
    ListCategoriesQuery
)


class ProductApplicationService:
    """
    商品应用服务。
    处理商品相关的应用层逻辑，协调领域服务和仓储。
    """
    
    def __init__(
        self,
        product_service: ProductService,
        product_repository: ProductRepository,
        category_repository: CategoryRepository,
        transaction_manager: TransactionManager,
        cache_service: Optional[CacheService] = None
    ):
        """
        初始化商品应用服务。
        
        Args:
            product_service: 商品领域服务
            product_repository: 商品仓储
            category_repository: 分类仓储
            transaction_manager: 事务管理器
            cache_service: 缓存服务
        """
        self.product_service = product_service
        self.product_repository = product_repository
        self.category_repository = category_repository
        self.transaction_manager = transaction_manager
        self.cache_service = cache_service
    
    def _get_category_name(self, category_id: Any) -> Optional[str]:
        """
        获取分类名称。
        
        Args:
            category_id: 分类ID
            
        Returns:
            分类名称，如果分类不存在则返回None
        """
        if not category_id:
            return None
        
        # 确保category_id是字符串类型
        category_id_str = str(category_id)
        category = self.category_repository.get_by_id(category_id_str)
        return category.name if category else None
    
    def _invalidate_product_cache(self, product_id: str) -> None:
        """
        使商品缓存失效。
        
        Args:
            product_id: 商品ID
        """
        if self.cache_service:
            self.cache_service.delete(f"product:{product_id}")
            self.cache_service.delete_pattern("search:*")
    
    def _invalidate_category_cache(self, category_id: Optional[str] = None) -> None:
        """
        使分类缓存失效。
        
        Args:
            category_id: 分类ID，如果为None则使所有分类缓存失效
        """
        if self.cache_service:
            if category_id:
                # 删除当前分类的缓存
                self.cache_service.delete(f"category:{category_id}")
                
                # 获取分类信息，以便找到父分类
                try:
                    category = self.category_repository.get_by_id(category_id)
                    if category and category.parent_id:
                        # 如果有父分类，也需要使父分类的缓存失效
                        parent_id = str(category.parent_id)
                        self.cache_service.delete(f"category:{parent_id}")
                        # 删除父分类的子分类列表缓存
                        self.cache_service.delete(f"categories:all:{parent_id}")
                        self.cache_service.delete(f"categories:tree:{parent_id}")
                except Exception as e:
                    logger.error(f"获取分类信息失败: {e}")
            
            # 删除所有分类列表的缓存
            self.cache_service.delete("categories:all")
            self.cache_service.delete("categories:tree")
            # 删除所有以 categories: 开头的缓存
            self.cache_service.delete_pattern("categories:*")
    
    # ==================== 命令处理方法 ====================
    
    def create_product(self, command: CreateProductCommand) -> ProductDTO:
        """
        创建商品。
        
        Args:
            command: 创建商品命令
            
        Returns:
            创建的商品DTO
        """
        try:
            with self.transaction_manager.start():
                # 创建Money值对象
                price = Money(command.price)
                
                # 调用领域服务创建商品
                product_aggregate = self.product_service.create_product(
                    name=command.name,
                    description=command.description,
                    price=price,
                    keywords=command.keywords,
                    category_id=command.category_id,
                    specification=command.specification,
                    initial_stock=command.initial_stock
                )
                
                # 获取分类名称
                category_name = self._get_category_name(product_aggregate.product.category_id)
                
                # 创建DTO并返回
                return ProductDTO.from_aggregate(product_aggregate, category_name)
        except Exception as e:
            logger.error(f"创建商品失败: {e}")
            raise
    
    def update_product(self, command: UpdateProductCommand) -> ProductDTO:
        """
        更新商品。
        
        Args:
            command: 更新商品命令
            
        Returns:
            更新后的商品DTO
        """
        try:
            with self.transaction_manager.start():
                # 创建Money值对象(如果有价格更新)
                price = Money(command.price) if command.price is not None else None
                
                # 调用领域服务更新商品
                product_aggregate = self.product_service.update_product(
                    product_id=command.id,
                    name=command.name,
                    description=command.description,
                    price=price,
                    keywords=command.keywords,
                    category_id=command.category_id,
                    specification=command.specification
                )
                
                # 使缓存失效
                self._invalidate_product_cache(str(command.id))
                
                # 获取分类名称
                category_name = self._get_category_name(product_aggregate.product.category_id)
                
                # 创建DTO并返回
                return ProductDTO.from_aggregate(product_aggregate, category_name)
        except Exception as e:
            logger.error(f"更新商品失败: {e}")
            raise
    
    def change_product_state(self, command: ChangeProductStateCommand) -> ProductDTO:
        """
        变更商品状态。
        
        Args:
            command: 变更商品状态命令
            
        Returns:
            更新后的商品DTO
        """
        try:
            with self.transaction_manager.start():
                # 调用领域服务变更商品状态
                product_aggregate = self.product_service.change_product_state(
                    product_id=command.id,
                    activate=command.activate
                )
                
                # 使缓存失效
                self._invalidate_product_cache(str(command.id))
                
                # 获取分类名称
                category_name = self._get_category_name(product_aggregate.product.category_id)
                
                # 创建DTO并返回
                return ProductDTO.from_aggregate(product_aggregate, category_name)
        except Exception as e:
            logger.error(f"变更商品状态失败: {e}")
            raise
    
    def update_product_stock(self, command: UpdateProductStockCommand) -> ProductDTO:
        """
        更新商品库存。
        
        Args:
            command: 更新商品库存命令
            
        Returns:
            更新后的商品DTO
        """
        try:
            with self.transaction_manager.start():
                # 调用领域服务更新库存
                product_aggregate = self.product_service.update_stock(
                    product_id=command.id,
                    new_stock=command.stock,
                    reserved_stock=command.reserved_stock
                )
                
                # 使缓存失效
                self._invalidate_product_cache(str(command.id))
                
                # 获取分类名称
                category_name = self._get_category_name(product_aggregate.product.category_id)
                
                # 创建DTO并返回
                return ProductDTO.from_aggregate(product_aggregate, category_name)
        except Exception as e:
            logger.error(f"更新商品库存失败: {e}")
            raise
    
    def add_product_rating(self, command: AddProductRatingCommand) -> ProductDTO:
        """
        添加商品评分。
        
        Args:
            command: 添加商品评分命令
            
        Returns:
            更新后的商品DTO
        """
        try:
            with self.transaction_manager.start():
                # 调用领域服务添加评分
                product_aggregate = self.product_service.add_rating(
                    product_id=command.id,
                    rating_value=command.rating_value
                )
                
                # 使缓存失效
                self._invalidate_product_cache(str(command.id))
                
                # 获取分类名称
                category_name = self._get_category_name(product_aggregate.product.category_id)
                
                # 创建DTO并返回
                return ProductDTO.from_aggregate(product_aggregate, category_name)
        except Exception as e:
            logger.error(f"添加商品评分失败: {e}")
            raise
    
    # ==================== 查询处理方法 ====================
    
    def get_product(self, query: GetProductQuery) -> Optional[ProductDTO]:
        """
        获取单个商品。
        
        Args:
            query: 获取商品查询
            
        Returns:
            商品DTO，如果不存在则返回None
        """
        try:
            # 尝试从缓存获取
            if self.cache_service:
                cached_product = self.cache_service.get(f"product:{query.id}")
                if cached_product:
                    return cached_product
            
            # 从仓储获取
            product_aggregate = self.product_repository.get_by_id(str(query.id))
            if not product_aggregate:
                return None
            
            # 获取分类名称
            category_name = self._get_category_name(product_aggregate.product.category_id)
            
            # 创建DTO
            product_dto = ProductDTO.from_aggregate(product_aggregate, category_name)
            
            # 缓存结果
            if self.cache_service:
                self.cache_service.set(f"product:{query.id}", product_dto, ttl=300)
            
            return product_dto
        except Exception as e:
            logger.error(f"获取商品失败: {e}")
            raise
    
    def list_products(self, query: ListProductsQuery) -> ProductListDTO:
        """
        获取商品列表。
        
        Args:
            query: 商品列表查询
            
        Returns:
            商品列表DTO
        """
        try:
            # 计算偏移量
            skip = (query.page - 1) * query.page_size
            
            # 根据是否有分类ID选择不同的查询方法
            if query.category_id:
                # 按分类查询
                products, total = self.product_repository.find_by_category(
                    category_id=query.category_id,
                    page=query.page,
                    page_size=query.page_size
                )
            else:
                # 获取商品列表
                products, total = self.product_repository.list(
                    skip=skip,
                    limit=query.page_size
                )
            
            # 构建DTO列表
            product_dtos = []
            for product_aggregate in products:
                # 获取分类名称
                category_name = self._get_category_name(product_aggregate.product.category_id)
                
                # 创建DTO
                product_dto = ProductDTO.from_aggregate(product_aggregate, category_name)
                product_dtos.append(product_dto)
            
            # 创建并返回列表DTO
            return ProductListDTO(
                items=product_dtos,
                total=total,
                page=query.page,
                page_size=query.page_size
            )
        except Exception as e:
            logger.error(f"获取商品列表失败: {e}")
            raise
    
    def search_products(self, query: SearchProductsQuery) -> ProductListDTO:
        """
        搜索商品。
        
        Args:
            query: 搜索商品查询
            
        Returns:
            商品列表DTO
        """
        try:
            # 尝试从缓存获取
            cache_key = query.get_cache_key()
            if self.cache_service:
                cached_result = self.cache_service.get(cache_key)
                if cached_result:
                    return cached_result
            
            # 获取过滤条件
            filters = query.get_filters()
            
            # 调用仓储搜索
            products, total, facet_data = self.product_repository.search(
                keyword=query.keyword,
                filters=filters,
                page=query.page,
                page_size=query.page_size,
                include_facets=query.include_facets,
                facet_fields=query.facet_fields
            )
            
            # 构建DTO列表
            product_dtos = []
            for product_aggregate in products:
                # 获取分类名称
                category_name = self._get_category_name(product_aggregate.product.category_id)
                
                # 创建DTO
                product_dto = ProductDTO.from_aggregate(product_aggregate, category_name)
                product_dtos.append(product_dto)
            
            # 处理分面数据
            facet_dtos = []
            if query.include_facets and facet_data:
                facet_dtos = self._process_facet_data(facet_data, query.selected_facets)
            
            # 创建列表DTO
            result = ProductListDTO(
                items=product_dtos,
                total=total,
                page=query.page,
                page_size=query.page_size,
                facets=facet_dtos
            )
            
            # 缓存结果
            if self.cache_service:
                self.cache_service.set(cache_key, result, ttl=300)
            
            return result
        except Exception as e:
            logger.error(f"搜索商品失败: {e}")
            raise
    
    def _process_facet_data(
        self, 
        facet_data: Dict[str, Any], 
        selected_facets: Optional[Dict[str, List[str]]] = None
    ) -> List[FacetDTO]:
        """
        处理分面数据，转换为FacetDTO列表。
        
        Args:
            facet_data: 从仓储层返回的原始分面数据
            selected_facets: 已选择的分面值
            
        Returns:
            FacetDTO列表
        """
        selected_facets = selected_facets or {}
        facet_dtos = []
        
        # 分类分面
        if 'category_id' in facet_data:
            values = []
            for category_id, count in facet_data['category_id'].items():
                if not category_id:  # 跳过空分类
                    continue
                    
                # 获取分类名称
                category_name = self._get_category_name(category_id)
                if not category_name:
                    continue
                    
                # 检查是否被选中
                is_selected = (
                    'category_id' in selected_facets and 
                    category_id in selected_facets['category_id']
                )
                
                values.append(FacetValueDTO(
                    value=category_id,
                    count=count,
                    selected=is_selected
                ))
            
            if values:
                facet_dtos.append(FacetDTO(
                    name='category_id',
                    display_name='分类',
                    values=values
                ))
        
        # 价格区间分面
        if 'price' in facet_data:
            values = []
            for price_range, count in facet_data['price'].items():
                # 检查是否被选中
                is_selected = (
                    'price' in selected_facets and 
                    price_range in selected_facets['price']
                )
                
                values.append(FacetValueDTO(
                    value=price_range,
                    count=count,
                    selected=is_selected
                ))
            
            if values:
                facet_dtos.append(FacetDTO(
                    name='price',
                    display_name='价格',
                    values=values,
                    facet_type='range'
                ))
        
        # 评分分面
        if 'rating_value' in facet_data:
            values = []
            for rating, count in facet_data['rating_value'].items():
                # 检查是否被选中
                is_selected = (
                    'rating_value' in selected_facets and 
                    str(rating) in selected_facets['rating_value']
                )
                
                values.append(FacetValueDTO(
                    value=rating,
                    count=count,
                    selected=is_selected
                ))
            
            if values:
                facet_dtos.append(FacetDTO(
                    name='rating_value',
                    display_name='评分',
                    values=values
                ))
        
        # 处理其他分面...
        
        return facet_dtos
    
    def get_products_by_ids(self, query: GetProductsByIdsQuery) -> List[ProductDTO]:
        """
        根据ID列表获取多个商品。
        
        Args:
            query: 根据ID列表获取商品查询
            
        Returns:
            商品DTO列表
        """
        try:
            result = []
            for id in query.ids:
                # 确保ID是字符串类型
                product_dto = self.get_product(GetProductQuery(id=str(id)))
                if product_dto:
                    result.append(product_dto)
            return result
        except Exception as e:
            logger.error(f"根据ID列表获取商品失败: {e}")
            raise
    
    def get_related_products(self, query: GetRelatedProductsQuery) -> List[ProductDTO]:
        """
        获取相关商品。
        
        Args:
            query: 获取相关商品查询
            
        Returns:
            相关商品DTO列表
        """
        try:
            # 调用领域服务获取相关商品
            related_products = self.product_service.get_related_products(
                product_id=str(query.product_id),
                limit=query.limit
            )
            
            # 构建DTO列表
            product_dtos = []
            for product_aggregate in related_products:
                # 获取分类名称
                category_name = self._get_category_name(product_aggregate.product.category_id)
                
                # 创建DTO
                product_dto = ProductDTO.from_aggregate(product_aggregate, category_name)
                product_dtos.append(product_dto)
            
            return product_dtos
        except Exception as e:
            logger.error(f"获取相关商品失败: {e}")
            raise
    
    # ==================== 分类相关方法 ====================
    
    def get_category(self, query: GetCategoryQuery) -> Optional[CategoryDTO]:
        """
        获取单个分类。
        
        Args:
            query: 获取分类查询
            
        Returns:
            分类DTO，如果不存在则返回None
        """
        try:
            # 尝试从缓存获取
            if self.cache_service:
                cached_category = self.cache_service.get(f"category:{query.id}")
                if cached_category:
                    return cached_category
            
            # 从仓储获取
            category = self.category_repository.get_by_id(str(query.id))
            if not category:
                return None
            
            # 获取父分类名称
            parent_name = None
            if category.parent_id:
                parent = self.category_repository.get_by_id(str(category.parent_id))
                if parent:
                    parent_name = parent.name
            
            # 创建DTO
            category_dto = CategoryDTO.from_value_object(category, parent_name)
            
            # 缓存结果
            if self.cache_service:
                self.cache_service.set(f"category:{query.id}", category_dto, ttl=3600)
            
            return category_dto
        except Exception as e:
            logger.error(f"获取分类失败: {e}")
            raise
    
    def list_categories(self, query: ListCategoriesQuery) -> List[CategoryDTO]:
        """
        获取分类列表。
        
        Args:
            query: 分类列表查询
            
        Returns:
            分类DTO列表
        """
        try:
            # 尝试从缓存获取
            cache_key = "categories:tree" if query.include_tree else "categories:all"
            if query.parent_id:
                cache_key += f":{query.parent_id}"
            
            if self.cache_service:
                cached_categories = self.cache_service.get(cache_key)
                if cached_categories:
                    return cached_categories
            
            # 获取分类列表
            if query.parent_id:
                categories = self.category_repository.get_children(str(query.parent_id))
            else:
                categories = self.category_repository.get_all()
            
            # 构建分类DTO列表
            category_dtos = []
            
            if query.include_tree:
                # 构建树结构
                # 首先获取所有顶级分类
                root_categories = [c for c in categories if not c.parent_id]
                
                # 为每个顶级分类构建子树
                for root_category in root_categories:
                    # 获取该分类下的商品数量
                    product_count = self.category_repository.count_products_in_category(str(root_category.id))
                    
                    children = self._build_category_tree(root_category.id, categories)
                    category_dto = CategoryDTO.from_value_object(
                        root_category,
                        None,
                        children,
                        product_count
                    )
                    category_dtos.append(category_dto)
            else:
                # 平面列表
                # 预先计算每个分类的子分类数量
                children_count = {}
                for category in categories:
                    children_count[str(category.id)] = 0
                
                for category in categories:
                    if category.parent_id:
                        parent_id_str = str(category.parent_id)
                        if parent_id_str in children_count:
                            children_count[parent_id_str] += 1
                
                for category in categories:
                    parent_name = None
                    if category.parent_id:
                        for parent in categories:
                            if str(parent.id) == str(category.parent_id):
                                parent_name = parent.name
                                break
                    
                    # 查找该分类的子分类
                    children = []
                    for child in categories:
                        if child.parent_id and str(child.parent_id) == str(category.id):
                            child_dto = CategoryDTO.from_value_object(child, category.name)
                            children.append(child_dto)
                    
                    # 获取该分类下的商品数量
                    product_count = self.category_repository.count_products_in_category(str(category.id))
                    
                    category_dto = CategoryDTO.from_value_object(
                        category,
                        parent_name,
                        children,
                        product_count
                    )
                    category_dtos.append(category_dto)
            
            # 缓存结果
            if self.cache_service:
                self.cache_service.set(cache_key, category_dtos, ttl=3600)
            
            return category_dtos
        except Exception as e:
            logger.error(f"获取分类列表失败: {e}")
            raise
    
    def _build_category_tree(self, parent_id: Any, categories: List[ProductCategory]) -> List[CategoryDTO]:
        """
        构建分类树。
        
        Args:
            parent_id: 父分类ID
            categories: 所有分类列表
            
        Returns:
            子分类DTO列表
        """
        parent_id_str = str(parent_id)
        children = []
        child_categories = [c for c in categories if c.parent_id and str(c.parent_id) == parent_id_str]
        
        for child in child_categories:
            # 获取该子分类的商品数量
            product_count = self.category_repository.count_products_in_category(str(child.id))
            
            grand_children = self._build_category_tree(child.id, categories)
            child_dto = CategoryDTO.from_value_object(child, None, grand_children, product_count)
            children.append(child_dto)
            
        return children
    
    def create_category(self, command: CreateCategoryCommand) -> CategoryDTO:
        """
        创建分类。
        
        Args:
            command: 创建分类命令
            
        Returns:
            创建的分类DTO
        """
        try:
            with self.transaction_manager.start():
                # 验证父分类是否存在
                parent_name = None
                if command.parent_id:
                    parent_category = self.category_repository.get_by_id(str(command.parent_id))
                    if not parent_category:
                        raise ValueError(f"父分类不存在: ID={command.parent_id}")
                    parent_name = parent_category.name
                
                # 创建分类值对象
                category = ProductCategory(
                    id=None,  # ID将由仓储生成
                    name=command.name,
                    description=command.description,
                    parent_id=command.parent_id
                )
                
                # 保存分类
                saved_category = self.category_repository.save(category)
                
                # 使缓存失效
                if command.parent_id:
                    # 如果有父分类，需要特别刷新父分类的缓存
                    self._invalidate_category_cache(str(command.parent_id))
                else:
                    # 否则刷新所有分类缓存
                    self._invalidate_category_cache()
                
                # 创建DTO并返回
                return CategoryDTO.from_value_object(saved_category, parent_name)
        except Exception as e:
            logger.error(f"创建分类失败: {e}")
            raise
    
    def update_category(self, command: UpdateCategoryCommand) -> CategoryDTO:
        """
        更新分类。
        
        Args:
            command: 更新分类命令
            
        Returns:
            更新后的分类DTO
        """
        try:
            with self.transaction_manager.start():
                # 获取要更新的分类
                category = self.category_repository.get_by_id(str(command.id))
                if not category:
                    raise ValueError(f"分类不存在: ID={command.id}")
                
                # 验证父分类是否存在
                parent_name = None
                if command.parent_id:
                    # 检查是否形成循环引用
                    if str(command.parent_id) == str(command.id):
                        raise ValueError("分类不能将自己设为父分类")
                    
                    parent_category = self.category_repository.get_by_id(str(command.parent_id))
                    if not parent_category:
                        raise ValueError(f"父分类不存在: ID={command.parent_id}")
                    parent_name = parent_category.name
                
                # 更新分类属性
                updated_category = ProductCategory(
                    id=category.id,
                    name=command.name if command.name is not None else category.name,
                    description=command.description if command.description is not None else category.description,
                    parent_id=command.parent_id if command.parent_id is not None else category.parent_id
                )
                
                # 保存更新后的分类
                saved_category = self.category_repository.save(updated_category)
                
                # 使缓存失效
                self._invalidate_category_cache(str(command.id))
                
                # 创建DTO并返回
                return CategoryDTO.from_value_object(saved_category, parent_name)
        except Exception as e:
            logger.error(f"更新分类失败: {e}")
            raise
    
    def delete_category(self, command: DeleteCategoryCommand) -> None:
        """
        删除分类。
        
        Args:
            command: 删除分类命令
        """
        try:
            with self.transaction_manager.start():
                # 获取要删除的分类
                category = self.category_repository.get_by_id(str(command.id))
                if not category:
                    raise ValueError(f"分类不存在: ID={command.id}")
                
                # 检查是否有子分类
                children = self.category_repository.get_children(str(command.id))
                if children:
                    raise ValueError("不能删除有子分类的分类，请先删除所有子分类")
                
                # 检查是否有使用此分类的商品
                products, count = self.product_repository.find_by_category(
                    category_id=str(command.id),
                    page=1,
                    page_size=1
                )
                if count > 0:
                    raise ValueError("不能删除有关联商品的分类，请先移除商品的分类关联")
                
                # 删除分类
                self.category_repository.delete(category)
                
                # 使缓存失效
                self._invalidate_category_cache()
        except Exception as e:
            logger.error(f"删除分类失败: {e}")
            raise
