"""
商品API视图。
提供RESTful API接口，处理HTTP请求并调用应用服务。
"""
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.decorators import api_view
from rest_framework.exceptions import NotFound, ValidationError
from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist
from django_redis import get_redis_connection
import uuid
import logging

from core.domain.exceptions import DomainException, EntityNotFoundException, ConcurrencyException
from core.infrastructure.api_view import ApiBaseView
from core.infrastructure.response import StatusCode
from products.application import (
    ProductApplicationService,
    # 命令
    CreateProductCommand,
    UpdateProductCommand,
    ChangeProductStateCommand,
    UpdateProductStockCommand,
    AddProductRatingCommand,
    # 查询
    GetProductQuery,
    ListProductsQuery,
    SearchProductsQuery,
    GetProductsByIdsQuery,
    GetRelatedProductsQuery,
)
from products.api.serializers import (
    # 请求序列化器
    ProductCreateSerializer,
    ProductUpdateSerializer,
    ProductStateChangeSerializer,
    ProductStockUpdateSerializer,
    ProductBatchStockUpdateSerializer,
    ProductRatingSerializer,
    ProductSearchSerializer,
    ProductBatchGetSerializer,
    # 响应序列化器
    ProductDetailSerializer,
    ProductListItemSerializer,
    PaginatedResponseSerializer,
    SearchResponseSerializer,
)

logger = logging.getLogger(__name__)


# 从依赖注入容器或全局配置获取应用服务实例
def get_product_service() -> ProductApplicationService:
    """获取商品应用服务实例"""
    # 这里应该从依赖注入容器或全局配置获取实例
    # 暂时使用简单工厂创建
    from core.infrastructure.cache import RedisCacheService
    from core.infrastructure.transaction import DjangoTransactionManager
    from products.infrastructure.factory import ProductInfrastructureFactory
    from products.domain.services import ProductService

    # 获取Redis连接
    redis_client = get_redis_connection("default")
    
    # 创建依赖服务
    cache_service = RedisCacheService(redis_client=redis_client)
    transaction_manager = DjangoTransactionManager()
    
    # 创建基础设施工厂
    factory = ProductInfrastructureFactory(
        cache_service=cache_service,
        transaction_manager=transaction_manager
    )
    
    # 初始化服务
    factory.initialize_services(preheat_cache=False)
    
    # 创建仓储
    product_repository = factory.create_product_repository()
    category_repository = factory.create_category_repository()
    inventory_lock_service = factory.create_inventory_lock_service()
    search_service = factory.create_search_service()
    
    # 创建领域服务
    product_service = ProductService(
        product_repository=product_repository,
        category_repository=category_repository
    )
    
    # 创建应用服务
    return ProductApplicationService(
        product_service=product_service,
        product_repository=product_repository,
        category_repository=category_repository,
        transaction_manager=transaction_manager,
        cache_service=cache_service
    )


class ProductListCreateView(ApiBaseView):
    """商品列表和创建接口"""
    
    def get(self, request):
        """获取商品列表"""
        # 解析查询参数
        page = int(request.query_params.get('page', 1))
        page_size = int(request.query_params.get('page_size', 20))
        category_id = request.query_params.get('category_id')
        if category_id:
            category_id = uuid.UUID(category_id)
        
        # 创建查询对象
        query = ListProductsQuery(
            page=page,
            page_size=page_size,
            category_id=category_id
        )
        
        # 调用应用服务
        try:
            product_service = get_product_service()
            result = product_service.list_products(query)
            
            # 使用统一响应格式返回结果
            serialized_items = [
                ProductListItemSerializer(item).data
                for item in result.items
            ]
            
            return self.paginated_response(
                items=serialized_items,
                total=result.total,
                page=result.page,
                page_size=result.page_size,
                message="获取商品列表成功"
            )
        except Exception as e:
            logger.error(f"获取商品列表失败: {str(e)}")
            return self.failed_response(
                message="获取商品列表失败",
                code=StatusCode.SERVER_ERROR,
                data={"detail": str(e)},
                http_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def post(self, request):
        """创建商品"""
        # 验证请求数据
        serializer = ProductCreateSerializer(data=request.data)
        if not serializer.is_valid():
            return self.failed_response(
                message="请求数据无效",
                code=StatusCode.VALIDATION_ERROR,
                data=serializer.errors,
                http_code=status.HTTP_400_BAD_REQUEST
            )
        
        # 创建命令对象
        data = serializer.validated_data
        command = CreateProductCommand(
            name=data['name'],
            description=data.get('description', ''),
            price=data['price_amount'],
            keywords=data.get('keywords', ''),
            category_id=data.get('category_id'),
            specification=data.get('attributes', {}),
            initial_stock=data.get('stock_quantity', 0)
        )
        
        # 调用应用服务
        try:
            product_service = get_product_service()
            product = product_service.create_product(command)
            
            # 返回创建的商品
            return self.created_response(
                data=ProductDetailSerializer(product).data,
                message="商品创建成功",
                code=StatusCode.CREATED
            )
        except EntityNotFoundException as e:
            return self.failed_response(
                message=str(e),
                code=StatusCode.ENTITY_NOT_FOUND,
                http_code=status.HTTP_404_NOT_FOUND
            )
        except ValidationError as e:
            return self.failed_response(
                message="数据验证失败",
                code=StatusCode.VALIDATION_ERROR,
                data=str(e),
                http_code=status.HTTP_400_BAD_REQUEST
            )
        except DomainException as e:
            return self.failed_response(
                message=str(e),
                code=StatusCode.BAD_REQUEST,
                http_code=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            logger.error(f"创建商品失败: {str(e)}")
            return self.failed_response(
                message="创建商品失败",
                code=StatusCode.SERVER_ERROR,
                data={"detail": str(e)},
                http_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class ProductDetailView(ApiBaseView):
    """商品详情、更新和删除接口"""
    
    def get(self, request, product_id):
        """获取商品详情"""
        try:
            # 检查 product_id 是否已经是 UUID 对象
            if not isinstance(product_id, uuid.UUID):
                product_id = uuid.UUID(product_id)
            
            # 创建查询对象
            query = GetProductQuery(id=product_id)
            
            # 调用应用服务
            product_service = get_product_service()
            product = product_service.get_product(query)
            
            # 返回商品详情
            return self.success_response(
                data=ProductDetailSerializer(product).data,
                message="获取商品详情成功"
            )
        except ValueError:
            return self.failed_response(
                message="商品ID格式无效",
                code=StatusCode.PARAM_ERROR,
                http_code=status.HTTP_400_BAD_REQUEST
            )
        except EntityNotFoundException:
            return self.failed_response(
                message="商品不存在",
                code=StatusCode.PRODUCT_NOT_FOUND,
                http_code=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            logger.error(f"获取商品详情失败: {str(e)}")
            return self.failed_response(
                message="获取商品详情失败",
                code=StatusCode.SERVER_ERROR,
                data={"detail": str(e)},
                http_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def put(self, request, product_id):
        """更新商品"""
        try:
            # 检查 product_id 是否已经是 UUID 对象
            if not isinstance(product_id, uuid.UUID):
                product_id = uuid.UUID(product_id)
            
            # 验证请求数据
            serializer = ProductUpdateSerializer(data=request.data)
            if not serializer.is_valid():
                return self.failed_response(
                    message="请求数据无效",
                    code=StatusCode.VALIDATION_ERROR,
                    data=serializer.errors,
                    http_code=status.HTTP_400_BAD_REQUEST
                )
            
            # 创建命令对象
            data = serializer.validated_data
            command = UpdateProductCommand(
                id=product_id,
                name=data.get('name'),
                description=data.get('description'),
                price=data.get('price_amount'),
                keywords=data.get('keywords'),
                category_id=data.get('category_id'),
                specification=data.get('attributes')
            )
            
            # 调用应用服务
            product_service = get_product_service()
            product = product_service.update_product(command)
            
            # 返回更新后的商品
            return self.success_response(
                data=ProductDetailSerializer(product).data,
                message="商品更新成功",
                code=StatusCode.UPDATED
            )
        except ValueError:
            return self.failed_response(
                message="商品ID格式无效",
                code=StatusCode.PARAM_ERROR,
                http_code=status.HTTP_400_BAD_REQUEST
            )
        except EntityNotFoundException:
            return self.failed_response(
                message="商品不存在",
                code=StatusCode.PRODUCT_NOT_FOUND,
                http_code=status.HTTP_404_NOT_FOUND
            )
        except ValidationError as e:
            return self.failed_response(
                message="数据验证失败",
                code=StatusCode.VALIDATION_ERROR,
                data=str(e),
                http_code=status.HTTP_400_BAD_REQUEST
            )
        except ConcurrencyException as e:
            return self.failed_response(
                message=str(e),
                code=StatusCode.OPTIMISTIC_LOCK_ERROR,
                http_code=status.HTTP_409_CONFLICT
            )
        except DomainException as e:
            return self.failed_response(
                message=str(e),
                code=StatusCode.BAD_REQUEST,
                http_code=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            logger.error(f"更新商品失败: {str(e)}")
            return self.failed_response(
                message="更新商品失败",
                code=StatusCode.SERVER_ERROR,
                data={"detail": str(e)},
                http_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def patch(self, request, product_id):
        """部分更新商品 - 调用完整更新接口"""
        return self.put(request, product_id)
    
    def delete(self, request, product_id):
        """删除商品"""
        try:
            # 检查 product_id 是否已经是 UUID 对象
            if not isinstance(product_id, uuid.UUID):
                product_id = uuid.UUID(product_id)
            
            # 创建命令对象，将状态设置为 'deleted'
            command = ChangeProductStateCommand(
                id=product_id,
                activate=False  # 设置为非激活状态
            )
            
            # 调用应用服务
            product_service = get_product_service()
            try:
                product_service.change_product_state(command)
            except EntityNotFoundException:
                # 如果商品不存在，也视为删除成功（幂等删除）
                pass
            except DomainException as e:
                # 如果是状态转换错误，我们也视为成功的删除
                # 因为无论如何，用户的意图是将商品标记为不可用
                if "商品状态不能从" not in str(e) or "变更为" not in str(e):
                    raise
            
            # 返回成功响应
            return self.success_response(
                message="商品删除成功",
                code=StatusCode.DELETED
            )
        except ValueError:
            return self.failed_response(
                message="商品ID格式无效",
                code=StatusCode.PARAM_ERROR,
                http_code=status.HTTP_400_BAD_REQUEST
            )
        except DomainException as e:
            return self.failed_response(
                message=str(e),
                code=StatusCode.BAD_REQUEST,
                http_code=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            logger.error(f"删除商品失败: {str(e)}")
            return self.failed_response(
                message="删除商品失败",
                code=StatusCode.SERVER_ERROR,
                data={"detail": str(e)},
                http_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class ProductStateView(ApiBaseView):
    """商品状态管理接口"""
    
    def put(self, request, product_id):
        """更改商品状态（激活/停用）"""
        try:
            # 检查 product_id 是否已经是 UUID 对象
            if not isinstance(product_id, uuid.UUID):
                product_id = uuid.UUID(product_id)
            
            # 验证请求数据
            serializer = ProductStateChangeSerializer(data=request.data)
            if not serializer.is_valid():
                return self.failed_response(
                    message="请求数据无效",
                    code=StatusCode.VALIDATION_ERROR,
                    data=serializer.errors,
                    http_code=status.HTTP_400_BAD_REQUEST
                )
            
            # 创建命令对象
            data = serializer.validated_data
            state = data['state']
            # 将状态值映射到布尔值
            activate = state == 'active'
            
            command = ChangeProductStateCommand(
                id=product_id,
                activate=activate
            )
            
            # 调用应用服务
            product_service = get_product_service()
            product = product_service.change_product_state(command)
            
            # 返回更新后的商品
            state_message = "商品已上线" if activate else "商品已下线"
            return self.success_response(
                data=ProductDetailSerializer(product).data,
                message=state_message,
                code=StatusCode.UPDATED
            )
        except ValueError:
            return self.failed_response(
                message="商品ID格式无效",
                code=StatusCode.PARAM_ERROR,
                http_code=status.HTTP_400_BAD_REQUEST
            )
        except EntityNotFoundException:
            return self.failed_response(
                message="商品不存在",
                code=StatusCode.PRODUCT_NOT_FOUND,
                http_code=status.HTTP_404_NOT_FOUND
            )
        except DomainException as e:
            return self.failed_response(
                message=str(e),
                code=StatusCode.BAD_REQUEST,
                http_code=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            logger.error(f"更改商品状态失败: {str(e)}")
            return self.failed_response(
                message="更改商品状态失败",
                code=StatusCode.SERVER_ERROR,
                data={"detail": str(e)},
                http_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class ProductStockView(ApiBaseView):
    """商品库存管理接口"""
    
    def put(self, request, product_id):
        """更新商品库存"""
        try:
            # 检查 product_id 是否已经是 UUID 对象
            if not isinstance(product_id, uuid.UUID):
                product_id = uuid.UUID(product_id)
            
            # 验证请求数据
            serializer = ProductStockUpdateSerializer(data=request.data)
            if not serializer.is_valid():
                return self.failed_response(
                    message="请求数据无效",
                    code=StatusCode.VALIDATION_ERROR,
                    data=serializer.errors,
                    http_code=status.HTTP_400_BAD_REQUEST
                )
            
            # 创建命令对象
            data = serializer.validated_data
            command = UpdateProductStockCommand(
                id=product_id,
                stock=data['available_quantity'],
                reserved_stock=data.get('reserved_quantity', 0)
            )
            
            # 调用应用服务
            product_service = get_product_service()
            updated_product = product_service.update_product_stock(command)
            
            # 返回更新后的库存信息
            return self.success_response(
                data=ProductDetailSerializer(updated_product).data,
                message="商品库存更新成功",
                code=StatusCode.UPDATED
            )
        except ValueError:
            return self.failed_response(
                message="商品ID格式无效",
                code=StatusCode.PARAM_ERROR,
                http_code=status.HTTP_400_BAD_REQUEST
            )
        except EntityNotFoundException:
            return self.failed_response(
                message="商品不存在",
                code=StatusCode.PRODUCT_NOT_FOUND,
                http_code=status.HTTP_404_NOT_FOUND
            )
        except DomainException as e:
            return self.failed_response(
                message=str(e),
                code=StatusCode.BAD_REQUEST,
                http_code=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            logger.error(f"更新商品库存失败: {str(e)}")
            return self.failed_response(
                message="更新商品库存失败",
                code=StatusCode.SERVER_ERROR,
                data={"detail": str(e)},
                http_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class ProductRatingView(ApiBaseView):
    """商品评分接口"""
    
    def post(self, request, product_id):
        """添加商品评分"""
        try:
            # 检查 product_id 是否已经是 UUID 对象
            if not isinstance(product_id, uuid.UUID):
                product_id = uuid.UUID(product_id)
            
            # 验证请求数据
            serializer = ProductRatingSerializer(data=request.data)
            if not serializer.is_valid():
                return self.failed_response(
                    message="请求数据无效",
                    code=StatusCode.VALIDATION_ERROR,
                    data=serializer.errors,
                    http_code=status.HTTP_400_BAD_REQUEST
                )
            
            # 创建命令对象
            data = serializer.validated_data
            command = AddProductRatingCommand(
                id=product_id,
                rating_value=data['rating']
            )
            
            # 调用应用服务
            product_service = get_product_service()
            product = product_service.add_product_rating(command)
            
            # 返回更新后的评分信息
            return self.success_response(
                data=ProductDetailSerializer(product).data,
                message="商品评分添加成功",
                code=StatusCode.CREATED
            )
        except ValueError:
            return self.failed_response(
                message="商品ID格式无效",
                code=StatusCode.PARAM_ERROR,
                http_code=status.HTTP_400_BAD_REQUEST
            )
        except EntityNotFoundException:
            return self.failed_response(
                message="商品不存在",
                code=StatusCode.PRODUCT_NOT_FOUND,
                http_code=status.HTTP_404_NOT_FOUND
            )
        except ValidationError as e:
            return self.failed_response(
                message="数据验证失败",
                code=StatusCode.VALIDATION_ERROR,
                data=str(e),
                http_code=status.HTTP_400_BAD_REQUEST
            )
        except DomainException as e:
            return self.failed_response(
                message=str(e),
                code=StatusCode.BAD_REQUEST,
                http_code=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            logger.error(f"添加商品评分失败: {str(e)}")
            return self.failed_response(
                message="添加商品评分失败",
                code=StatusCode.SERVER_ERROR,
                data={"detail": str(e)},
                http_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class RelatedProductsView(ApiBaseView):
    """相关商品接口"""
    
    def get(self, request, product_id):
        """获取相关商品"""
        try:
            # 检查 product_id 是否已经是 UUID 对象
            if not isinstance(product_id, uuid.UUID):
                product_id = uuid.UUID(product_id)
            
            # 导入商品模块配置
            from products.domain.config import RELATED_PRODUCTS_LIMIT
            
            # 创建查询对象
            query = GetRelatedProductsQuery(
                product_id=str(product_id),
                limit=int(request.query_params.get('limit', RELATED_PRODUCTS_LIMIT))
            )
            
            # 调用应用服务
            product_service = get_product_service()
            result = product_service.get_related_products(query)
            
            # 返回相关商品
            serialized_items = [
                ProductListItemSerializer(item).data
                for item in result
            ]
            
            return self.success_response(
                data=serialized_items,
                message="获取相关商品成功"
            )
        except ValueError:
            return self.failed_response(
                message="商品ID格式无效",
                code=StatusCode.PARAM_ERROR,
                http_code=status.HTTP_400_BAD_REQUEST
            )
        except EntityNotFoundException:
            return self.failed_response(
                message="商品不存在",
                code=StatusCode.PRODUCT_NOT_FOUND,
                http_code=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            logger.error(f"获取相关商品失败: {str(e)}")
            return self.failed_response(
                message="获取相关商品失败",
                code=StatusCode.SERVER_ERROR,
                data={"detail": str(e)},
                http_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class ProductSearchView(ApiBaseView):
    """商品搜索接口"""
    
    def get(self, request):
        """搜索商品"""
        # 验证请求参数
        serializer = ProductSearchSerializer(data=request.query_params)
        if not serializer.is_valid():
            return self.failed_response(
                message="请求参数无效",
                code=StatusCode.VALIDATION_ERROR,
                data=serializer.errors,
                http_code=status.HTTP_400_BAD_REQUEST
            )
        
        # 创建查询对象
        data = serializer.validated_data
        
        # 处理已选择的分面
        selected_facets = data.get('selected_facets', {})
        
        # 处理分类ID
        category_id = data.get('category_id')
        if category_id:
            # 如果通过URL参数提供了分类ID，添加到已选择的分面中
            if 'category_id' not in selected_facets:
                selected_facets['category_id'] = []
            selected_facets['category_id'].append(str(category_id))
        
        # 处理价格范围
        min_price = data.get('min_price')
        max_price = data.get('max_price')
        if min_price is not None or max_price is not None:
            price_range = f"{min_price or 0}-{max_price or 'max'}"
            if 'price' not in selected_facets:
                selected_facets['price'] = []
            selected_facets['price'].append(price_range)
        
        query = SearchProductsQuery(
            keyword=data.get('keyword', ''),
            category_id=category_id,
            min_price=min_price,
            max_price=max_price,
            page=data.get('page', 1),
            page_size=data.get('page_size', 20),
            include_facets=data.get('include_facets', True),
            facet_fields=data.get('facet_fields'),
            selected_facets=selected_facets
        )
        
        # 调用应用服务
        try:
            product_service = get_product_service()
            result = product_service.search_products(query)
            
            # 构造响应数据
            serialized_items = [
                ProductListItemSerializer(item).data
                for item in result.items
            ]
            
            # 准备元数据（分面信息）
            metadata = None
            if result.facets:
                metadata = {
                    "facets": result.facets,
                    "appliedFilters": selected_facets
                }
            
            # 返回搜索结果
            return self.paginated_response(
                items=serialized_items,
                total=result.total,
                page=result.page,
                page_size=result.page_size,
                message="商品搜索成功",
                metadata=metadata
            )
        except ValidationError as e:
            return self.failed_response(
                message="数据验证失败",
                code=StatusCode.VALIDATION_ERROR,
                data=str(e),
                http_code=status.HTTP_400_BAD_REQUEST
            )
        except DomainException as e:
            return self.failed_response(
                message=str(e),
                code=StatusCode.BAD_REQUEST,
                http_code=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            logger.error(f"搜索商品失败: {str(e)}")
            return self.failed_response(
                message="搜索商品失败",
                code=StatusCode.SERVER_ERROR,
                data={"detail": str(e)},
                http_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class ProductBatchView(ApiBaseView):
    """商品批量操作接口"""
    
    def post(self, request):
        """批量获取商品"""
        # 验证请求数据
        serializer = ProductBatchGetSerializer(data=request.data)
        if not serializer.is_valid():
            return self.failed_response(
                message="请求数据无效",
                code=StatusCode.VALIDATION_ERROR,
                data=serializer.errors,
                http_code=status.HTTP_400_BAD_REQUEST
            )
        
        # 创建查询对象
        query = GetProductsByIdsQuery(
            ids=serializer.validated_data['product_ids']
        )
        
        # 调用应用服务
        try:
            product_service = get_product_service()
            products = product_service.get_products_by_ids(query)
            
            # 返回商品列表
            serialized_items = [
                ProductDetailSerializer(product).data
                for product in products
            ]
            
            return self.success_response(
                data=serialized_items,
                message="批量获取商品成功"
            )
        except Exception as e:
            logger.error(f"批量获取商品失败: {str(e)}")
            return self.failed_response(
                message="批量获取商品失败",
                code=StatusCode.SERVER_ERROR,
                data={"detail": str(e)},
                http_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class ProductBatchStockView(ApiBaseView):
    """商品批量库存更新接口"""
    
    def put(self, request):
        """批量更新商品库存"""
        # 验证请求数据
        serializer = ProductBatchStockUpdateSerializer(data=request.data)
        if not serializer.is_valid():
            return self.failed_response(
                message="请求数据无效",
                code=StatusCode.VALIDATION_ERROR,
                data=serializer.errors,
                http_code=status.HTTP_400_BAD_REQUEST
            )
        
        # 获取库存项
        items = serializer.validated_data['items']
        
        # 调用应用服务
        try:
            product_service = get_product_service()
            results = []
            
            # 处理每个库存项
            for item in items:
                product_id = item['product_id']
                try:
                    # 确保product_id是UUID
                    if isinstance(product_id, str):
                        product_id = uuid.UUID(product_id)
                        
                    command = UpdateProductStockCommand(
                        id=product_id,
                        stock=int(item['available_quantity']),
                        reserved_stock=item.get('reserved_quantity', 0)
                    )
                    
                    # 调用应用服务
                    updated_product = product_service.update_product_stock(command)
                    
                    # 添加成功结果
                    results.append({
                        'product_id': str(product_id),
                        'success': True,
                        'product': ProductDetailSerializer(updated_product).data
                    })
                except Exception as e:
                    # 添加失败结果
                    results.append({
                        'product_id': str(product_id),
                        'success': False,
                        'error': str(e)
                    })
            
            # 返回批量结果
            return self.success_response(
                data=results,
                message="批量更新商品库存成功"
            )
        except Exception as e:
            logger.error(f"批量更新商品库存失败: {str(e)}")
            return self.failed_response(
                message="批量更新商品库存失败",
                code=StatusCode.SERVER_ERROR,
                data={"detail": str(e)},
                http_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class CategoryListCreateView(ApiBaseView):
    """分类列表和创建接口"""
    
    def get(self, request):
        """获取分类列表"""
        try:
            # 解析查询参数
            include_tree = request.query_params.get('include_tree', 'false').lower() == 'true'
            parent_id = request.query_params.get('parent_id')
            page = int(request.query_params.get('page', 1))
            page_size = int(request.query_params.get('page_size', 20))
            
            if parent_id:
                parent_id = uuid.UUID(parent_id)
            
            # 创建查询对象
            from products.application.queries import ListCategoriesQuery
            query = ListCategoriesQuery(
                include_tree=include_tree,
                parent_id=parent_id
            )
            
            # 调用应用服务
            product_service = get_product_service()
            result = product_service.list_categories(query)
            
            # 将DTO列表转换为字典列表
            result_dicts = [category.to_dict() for category in result]
            
            # 手动实现分页
            total = len(result_dicts)
            start_idx = (page - 1) * page_size
            end_idx = min(start_idx + page_size, total)
            
            # 返回分页结果
            return self.paginated_response(
                items=result_dicts[start_idx:end_idx],
                total=total,
                page=page,
                page_size=page_size,
                message="获取分类列表成功"
            )
        except Exception as e:
            logger.error(f"获取分类列表失败: {str(e)}")
            return self.failed_response(
                message="获取分类列表失败",
                code=StatusCode.SERVER_ERROR,
                data={"detail": str(e)},
                http_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def post(self, request):
        """创建分类"""
        from products.api.serializers import CategoryCreateSerializer
        from products.application.commands import CreateCategoryCommand
        
        # 验证请求数据
        serializer = CategoryCreateSerializer(data=request.data)
        if not serializer.is_valid():
            return self.failed_response(
                message="请求数据无效",
                code=StatusCode.VALIDATION_ERROR,
                data=serializer.errors,
                http_code=status.HTTP_400_BAD_REQUEST
            )
        
        # 创建命令对象
        data = serializer.validated_data
        command = CreateCategoryCommand(
            name=data['name'],
            description=data.get('description', ''),
            parent_id=data.get('parent_id')
        )
        
        # 调用应用服务
        try:
            product_service = get_product_service()
            category = product_service.create_category(command)
            
            # 返回创建的分类
            from products.api.serializers import CategorySerializer
            return self.created_response(
                data=CategorySerializer(category).data,
                message="分类创建成功",
                code=StatusCode.CREATED
            )
        except EntityNotFoundException as e:
            return self.failed_response(
                message=str(e),
                code=StatusCode.ENTITY_NOT_FOUND,
                http_code=status.HTTP_404_NOT_FOUND
            )
        except DomainException as e:
            return self.failed_response(
                message=str(e),
                code=StatusCode.BAD_REQUEST,
                http_code=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            logger.error(f"创建分类失败: {str(e)}")
            return self.failed_response(
                message="创建分类失败",
                code=StatusCode.SERVER_ERROR,
                data={"detail": str(e)},
                http_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class CategoryDetailView(ApiBaseView):
    """分类详情、更新和删除接口"""
    
    def get(self, request, category_id):
        """获取分类详情"""
        from products.application.queries import GetCategoryQuery
        
        try:
            # 检查 category_id 是否已经是 UUID 对象
            if not isinstance(category_id, uuid.UUID):
                category_id = uuid.UUID(category_id)
                
            query = GetCategoryQuery(id=str(category_id))
            
            # 调用应用服务
            product_service = get_product_service()
            category = product_service.get_category(query)
            
            # 返回分类详情
            from products.api.serializers import CategorySerializer
            return self.success_response(
                data=CategorySerializer(category).data,
                message="获取分类详情成功"
            )
        except ValueError:
            return self.failed_response(
                message="分类ID格式无效",
                code=StatusCode.PARAM_ERROR,
                http_code=status.HTTP_400_BAD_REQUEST
            )
        except EntityNotFoundException:
            return self.failed_response(
                message="分类不存在",
                code=StatusCode.ENTITY_NOT_FOUND,
                http_code=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            logger.error(f"获取分类详情失败: {str(e)}")
            return self.failed_response(
                message="获取分类详情失败",
                code=StatusCode.SERVER_ERROR,
                data={"detail": str(e)},
                http_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def put(self, request, category_id):
        """更新分类"""
        from products.api.serializers import CategoryUpdateSerializer
        from products.application.commands import UpdateCategoryCommand
        
        try:
            # 检查 category_id 是否已经是 UUID 对象
            if not isinstance(category_id, uuid.UUID):
                category_id = uuid.UUID(category_id)
            
            # 验证请求数据
            serializer = CategoryUpdateSerializer(data=request.data)
            if not serializer.is_valid():
                return self.failed_response(
                    message="请求数据无效",
                    code=StatusCode.VALIDATION_ERROR,
                    data=serializer.errors,
                    http_code=status.HTTP_400_BAD_REQUEST
                )
            
            # 创建命令对象
            data = serializer.validated_data
            command = UpdateCategoryCommand(
                id=str(category_id),
                name=data.get('name'),
                description=data.get('description'),
                parent_id=data.get('parent_id')
            )
            
            # 调用应用服务
            product_service = get_product_service()
            category = product_service.update_category(command)
            
            # 返回更新后的分类
            from products.api.serializers import CategorySerializer
            return self.success_response(
                data=CategorySerializer(category).data,
                message="分类更新成功",
                code=StatusCode.UPDATED
            )
        except ValueError:
            return self.failed_response(
                message="分类ID格式无效",
                code=StatusCode.PARAM_ERROR,
                http_code=status.HTTP_400_BAD_REQUEST
            )
        except EntityNotFoundException:
            return self.failed_response(
                message="分类不存在",
                code=StatusCode.ENTITY_NOT_FOUND,
                http_code=status.HTTP_404_NOT_FOUND
            )
        except DomainException as e:
            return self.failed_response(
                message=str(e),
                code=StatusCode.BAD_REQUEST,
                http_code=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            logger.error(f"更新分类失败: {str(e)}")
            return self.failed_response(
                message="更新分类失败",
                code=StatusCode.SERVER_ERROR,
                data={"detail": str(e)},
                http_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def delete(self, request, category_id):
        """删除分类"""
        from products.application.commands import DeleteCategoryCommand
        
        try:
            # 检查 category_id 是否已经是 UUID 对象
            if not isinstance(category_id, uuid.UUID):
                category_id = uuid.UUID(category_id)
                
            command = DeleteCategoryCommand(id=str(category_id))
            
            # 调用应用服务
            product_service = get_product_service()
            try:
                product_service.delete_category(command)
            except EntityNotFoundException:
                # 如果分类不存在，也视为删除成功（幂等删除）
                pass
            
            # 返回成功响应
            return self.success_response(
                message="分类删除成功",
                code=StatusCode.DELETED
            )
        except ValueError:
            return self.failed_response(
                message="分类ID格式无效",
                code=StatusCode.PARAM_ERROR,
                http_code=status.HTTP_400_BAD_REQUEST
            )
        except DomainException as e:
            return self.failed_response(
                message=str(e),
                code=StatusCode.BAD_REQUEST,
                http_code=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            logger.error(f"删除分类失败: {str(e)}")
            return self.failed_response(
                message="删除分类失败",
                code=StatusCode.SERVER_ERROR,
                data={"detail": str(e)},
                http_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            ) 