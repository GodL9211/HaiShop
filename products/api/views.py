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


class ProductListCreateView(APIView):
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
            
            # 构造响应
            response_data = {
                'count': result.total,
                'next': result.page * result.page_size < result.total,
                'previous': result.page > 1,
                'page': result.page,
                'page_size': result.page_size,
                'results': [
                    ProductListItemSerializer(item).data
                    for item in result.items
                ]
            }
            
            return Response(response_data)
        except Exception as e:
            logger.error(f"获取商品列表失败: {str(e)}")
            return Response(
                {'error': '获取商品列表失败', 'detail': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def post(self, request):
        """创建商品"""
        # 验证请求数据
        serializer = ProductCreateSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {'error': '请求数据无效', 'detail': serializer.errors},
                status=status.HTTP_400_BAD_REQUEST
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
            return Response(
                ProductDetailSerializer(product).data,
                status=status.HTTP_201_CREATED
            )
        except EntityNotFoundException as e:
            return Response(
                {'error': '实体不存在', 'detail': str(e)},
                status=status.HTTP_404_NOT_FOUND
            )
        except ValidationError as e:
            return Response(
                {'error': '数据验证失败', 'detail': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
        except DomainException as e:
            return Response(
                {'error': '领域错误', 'detail': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            logger.error(f"创建商品失败: {str(e)}")
            return Response(
                {'error': '创建商品失败', 'detail': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class ProductDetailView(APIView):
    """商品详情、更新和删除接口"""
    
    def get(self, request, product_id):
        """获取商品详情"""
        try:
            # 创建查询对象
            if isinstance(product_id, uuid.UUID):
                product_uuid = product_id
            else:
                product_uuid = uuid.UUID(product_id)
                
            logger.info(f"获取商品详情: 查询ID={product_uuid}, 类型={type(product_id)}")
            query = GetProductQuery(id=str(product_uuid))
            
            # 调用应用服务
            product_service = get_product_service()
            
            try:
                product = product_service.get_product(query)
                logger.info(f"获取商品详情成功: {product}")
            except Exception as service_error:
                import traceback
                stack_trace = traceback.format_exc()
                logger.error(f"应用服务get_product调用失败: {str(service_error)}\n堆栈跟踪:\n{stack_trace}")
                raise
            
            if not product:
                return Response(
                    {'error': '商品不存在', 'detail': f"找不到ID为{product_uuid}的商品"},
                    status=status.HTTP_404_NOT_FOUND
                )
            
            # 将DTO转换为字典，避免序列化问题
            try:
                product_dict = product.to_dict() if hasattr(product, 'to_dict') else {}
                logger.info(f"商品详情转换为字典: {product_dict}")
            except Exception as dict_error:
                import traceback
                stack_trace = traceback.format_exc()
                logger.error(f"商品DTO转换为字典失败: {str(dict_error)}\n堆栈跟踪:\n{stack_trace}")
                raise
            
            # 返回商品详情
            return Response(product_dict)
        except ValueError as e:
            # 处理无效的UUID格式
            logger.error(f"无效的商品ID格式: {product_id}, 错误: {str(e)}")
            return Response(
                {'error': '无效的商品ID格式', 'detail': f"商品ID '{product_id}' 不是有效的UUID格式"},
                status=status.HTTP_400_BAD_REQUEST
            )
        except EntityNotFoundException:
            return Response(
                {'error': '商品不存在', 'detail': f"找不到ID为{product_id}的商品"},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            import traceback
            stack_trace = traceback.format_exc()
            logger.error(f"获取商品详情失败: {str(e)}\n堆栈跟踪:\n{stack_trace}")
            return Response(
                {'error': '获取商品详情失败', 'detail': str(e), 'stack_trace': stack_trace},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def put(self, request, product_id):
        """更新商品"""
        # 验证请求数据
        serializer = ProductUpdateSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {'error': '请求数据无效', 'detail': serializer.errors},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # 创建命令对象
        data = serializer.validated_data
        if isinstance(product_id, uuid.UUID):
            product_uuid = product_id
        else:
            product_uuid = uuid.UUID(product_id)
            
        command = UpdateProductCommand(
            id=str(product_uuid),
            name=data.get('name'),
            description=data.get('description'),
            price=data.get('price_amount'),
            keywords=data.get('keywords'),
            category_id=data.get('category_id'),
            specification=data.get('attributes')
        )
        
        # 调用应用服务
        try:
            product_service = get_product_service()
            product = product_service.update_product(command)
            
            # 返回更新后的商品
            return Response(ProductDetailSerializer(product).data)
        except EntityNotFoundException:
            return Response(
                {'error': '商品不存在', 'detail': f"找不到ID为{product_uuid}的商品"},
                status=status.HTTP_404_NOT_FOUND
            )
        except ValidationError as e:
            return Response(
                {'error': '数据验证失败', 'detail': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
        except DomainException as e:
            return Response(
                {'error': '领域错误', 'detail': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            import traceback
            stack_trace = traceback.format_exc()
            logger.error(f"更新商品失败: {str(e)}\n堆栈跟踪:\n{stack_trace}")
            return Response(
                {'error': '更新商品失败', 'detail': str(e), 'stack_trace': stack_trace},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def patch(self, request, product_id):
        """部分更新商品"""
        # 处理逻辑与PUT方法相同，但允许部分字段
        return self.put(request, product_id)
    
    def delete(self, request, product_id):
        """删除商品（标记为已删除状态）"""
        try:
            # 创建命令对象
            if isinstance(product_id, uuid.UUID):
                product_uuid = product_id
            else:
                product_uuid = uuid.UUID(product_id)
                
            command = ChangeProductStateCommand(
                id=str(product_uuid),
                activate=False
            )
            
            # 调用应用服务
            product_service = get_product_service()
            product_service.change_product_state(command)
            
            # 返回成功响应
            return Response(status=status.HTTP_204_NO_CONTENT)
        except EntityNotFoundException:
            return Response(
                {'error': '商品不存在', 'detail': f"找不到ID为{product_id}的商品"},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            import traceback
            stack_trace = traceback.format_exc()
            logger.error(f"删除商品失败: {str(e)}\n堆栈跟踪:\n{stack_trace}")
            return Response(
                {'error': '删除商品失败', 'detail': str(e), 'stack_trace': stack_trace},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class ProductStateView(APIView):
    """商品状态更改接口"""
    
    def put(self, request, product_id):
        """更改商品状态"""
        # 验证请求数据
        serializer = ProductStateChangeSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {'error': '请求数据无效', 'detail': serializer.errors},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # 创建命令对象
        if isinstance(product_id, uuid.UUID):
            product_uuid = product_id
        else:
            product_uuid = uuid.UUID(product_id)
            
        command = ChangeProductStateCommand(
            id=str(product_uuid),
            activate=serializer.validated_data['state'] == 'active'
        )
        
        # 调用应用服务
        try:
            product_service = get_product_service()
            product = product_service.change_product_state(command)
            
            # 返回更新后的商品
            return Response(ProductDetailSerializer(product).data)
        except EntityNotFoundException:
            return Response(
                {'error': '商品不存在', 'detail': f"找不到ID为{product_uuid}的商品"},
                status=status.HTTP_404_NOT_FOUND
            )
        except DomainException as e:
            return Response(
                {'error': '领域错误', 'detail': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            import traceback
            stack_trace = traceback.format_exc()
            logger.error(f"更改商品状态失败: {str(e)}\n堆栈跟踪:\n{stack_trace}")
            return Response(
                {'error': '更改商品状态失败', 'detail': str(e), 'stack_trace': stack_trace},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class ProductStockView(APIView):
    """商品库存更新接口"""
    
    def put(self, request, product_id):
        """更新商品库存"""
        # 验证请求数据
        serializer = ProductStockUpdateSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {'error': '请求数据无效', 'detail': serializer.errors},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # 创建命令对象
        data = serializer.validated_data
        if isinstance(product_id, uuid.UUID):
            product_uuid = product_id
        else:
            product_uuid = uuid.UUID(product_id)
            
        command = UpdateProductStockCommand(
            id=str(product_uuid),
            stock=data['available_quantity'],
            reserved_stock=data.get('reserved_quantity', 0)
        )
        
        # 调用应用服务
        try:
            product_service = get_product_service()
            product = product_service.update_product_stock(command)
            
            # 返回更新后的商品
            return Response(ProductDetailSerializer(product).data)
        except EntityNotFoundException:
            return Response(
                {'error': '商品不存在', 'detail': f"找不到ID为{product_uuid}的商品"},
                status=status.HTTP_404_NOT_FOUND
            )
        except ConcurrencyException as e:
            return Response(
                {'error': '并发冲突', 'detail': str(e)},
                status=status.HTTP_409_CONFLICT
            )
        except DomainException as e:
            return Response(
                {'error': '领域错误', 'detail': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            import traceback
            stack_trace = traceback.format_exc()
            logger.error(f"更新商品库存失败: {str(e)}\n堆栈跟踪:\n{stack_trace}")
            return Response(
                {'error': '更新商品库存失败', 'detail': str(e), 'stack_trace': stack_trace},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class ProductRatingView(APIView):
    """商品评分接口"""
    
    def post(self, request, product_id):
        """添加商品评分"""
        # 验证请求数据
        serializer = ProductRatingSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {'error': '请求数据无效', 'detail': serializer.errors},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # 创建命令对象
        data = serializer.validated_data
        try:
            if isinstance(product_id, uuid.UUID):
                product_uuid = product_id
            else:
                product_uuid = uuid.UUID(product_id)
                
            command = AddProductRatingCommand(
                id=str(product_uuid),
                rating_value=data['rating']
            )
            
            # 调用应用服务
            product_service = get_product_service()
            product = product_service.add_product_rating(command)
            
            # 返回更新后的商品
            return Response(ProductDetailSerializer(product).data)
        except ValueError as e:
            # 处理无效的UUID格式
            logger.error(f"无效的商品ID格式: {product_id}, 错误: {str(e)}")
            return Response(
                {'error': '无效的商品ID格式', 'detail': f"商品ID '{product_id}' 不是有效的UUID格式"},
                status=status.HTTP_400_BAD_REQUEST
            )
        except EntityNotFoundException:
            return Response(
                {'error': '商品不存在', 'detail': f"找不到ID为{product_id}的商品"},
                status=status.HTTP_404_NOT_FOUND
            )
        except DomainException as e:
            return Response(
                {'error': '领域错误', 'detail': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            import traceback
            stack_trace = traceback.format_exc()
            logger.error(f"添加商品评分失败: {str(e)}\n堆栈跟踪:\n{stack_trace}")
            return Response(
                {'error': '添加商品评分失败', 'detail': str(e), 'stack_trace': stack_trace},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class RelatedProductsView(APIView):
    """相关商品接口"""
    
    def get(self, request, product_id):
        """获取相关商品"""
        try:
            # 导入商品模块配置
            from products.domain.config import RELATED_PRODUCTS_LIMIT
            
            # 创建查询对象
            if isinstance(product_id, uuid.UUID):
                product_uuid = product_id
            else:
                product_uuid = uuid.UUID(product_id)
                
            logger.info(f"获取相关商品: 查询ID={product_uuid}, 类型={type(product_id)}")
            query = GetRelatedProductsQuery(
                product_id=str(product_uuid),
                limit=int(request.query_params.get('limit', RELATED_PRODUCTS_LIMIT))
            )
            
            # 调用应用服务
            product_service = get_product_service()
            result = product_service.get_related_products(query)
            
            # 返回相关商品
            return Response([
                ProductListItemSerializer(item).data
                for item in result
            ])
        except EntityNotFoundException:
            return Response(
                {'error': '商品不存在', 'detail': f"找不到ID为{product_id}的商品"},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            import traceback
            stack_trace = traceback.format_exc()
            logger.error(f"获取相关商品失败: {str(e)}\n堆栈跟踪:\n{stack_trace}")
            return Response(
                {'error': '获取相关商品失败', 'detail': str(e), 'stack_trace': stack_trace},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class ProductSearchView(APIView):
    """商品搜索接口"""
    
    def get(self, request):
        """搜索商品"""
        # 验证请求参数
        serializer = ProductSearchSerializer(data=request.query_params)
        if not serializer.is_valid():
            return Response(
                {'error': '请求参数无效', 'detail': serializer.errors},
                status=status.HTTP_400_BAD_REQUEST
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
            
            # 构造响应
            response_data = {
                'count': result.total,
                'next': result.page * result.page_size < result.total,
                'previous': result.page > 1,
                'page': result.page,
                'page_size': result.page_size,
                'results': [
                    ProductListItemSerializer(item).data
                    for item in result.items
                ],
                'facets': [facet.to_dict() for facet in result.facets] if result.facets else []
            }
            
            return Response(response_data)
        except Exception as e:
            logger.error(f"搜索商品失败: {str(e)}")
            return Response(
                {'error': '搜索商品失败', 'detail': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class ProductBatchView(APIView):
    """商品批量操作接口"""
    
    def post(self, request):
        """批量获取商品"""
        # 验证请求数据
        serializer = ProductBatchGetSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {'error': '请求数据无效', 'detail': serializer.errors},
                status=status.HTTP_400_BAD_REQUEST
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
            return Response([
                ProductDetailSerializer(product).data
                for product in products
            ])
        except Exception as e:
            logger.error(f"批量获取商品失败: {str(e)}")
            return Response(
                {'error': '批量获取商品失败', 'detail': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class ProductBatchStockView(APIView):
    """商品批量库存更新接口"""
    
    def put(self, request):
        """批量更新商品库存"""
        # 验证请求数据
        serializer = ProductBatchStockUpdateSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {'error': '请求数据无效', 'detail': serializer.errors},
                status=status.HTTP_400_BAD_REQUEST
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
                    # 确保product_id是字符串
                    product_id_str = str(product_id)
                    command = UpdateProductStockCommand(
                        id=product_id_str,
                        stock=int(item['available_quantity']),
                        reserved_stock=int(item.get('reserved_quantity', 0))
                    )
                    
                    # 调用应用服务
                    product = product_service.update_product_stock(command)
                    
                    # 添加成功结果
                    results.append({
                        'product_id': product_id,
                        'success': True,
                        'data': ProductDetailSerializer(product).data
                    })
                except Exception as e:
                    # 添加失败结果
                    results.append({
                        'product_id': product_id,
                        'success': False,
                        'error': str(e)
                    })
            
            # 返回批量结果
            return Response(results)
        except Exception as e:
            import traceback
            stack_trace = traceback.format_exc()
            logger.error(f"批量更新商品库存失败: {str(e)}\n堆栈跟踪:\n{stack_trace}")
            return Response(
                {'error': '批量更新商品库存失败', 'detail': str(e), 'stack_trace': stack_trace},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class CategoryListCreateView(APIView):
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
            
            # 构造分页响应
            response_data = {
                'count': total,
                'next': end_idx < total,
                'previous': page > 1,
                'page': page,
                'page_size': page_size,
                'total_pages': (total + page_size - 1) // page_size if page_size > 0 else 0,
                'results': result_dicts[start_idx:end_idx]
            }
            
            # 返回分类列表
            return Response(response_data)
        except Exception as e:
            logger.error(f"获取分类列表失败: {str(e)}")
            return Response(
                {'error': '获取分类列表失败', 'detail': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def post(self, request):
        """创建分类"""
        from products.api.serializers import CategoryCreateSerializer
        from products.application.commands import CreateCategoryCommand
        
        # 验证请求数据
        serializer = CategoryCreateSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {'error': '请求数据无效', 'detail': serializer.errors},
                status=status.HTTP_400_BAD_REQUEST
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
            return Response(
                CategorySerializer(category).data,
                status=status.HTTP_201_CREATED
            )
        except EntityNotFoundException as e:
            return Response(
                {'error': '实体不存在', 'detail': str(e)},
                status=status.HTTP_404_NOT_FOUND
            )
        except DomainException as e:
            return Response(
                {'error': '领域错误', 'detail': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            logger.error(f"创建分类失败: {str(e)}")
            return Response(
                {'error': '创建分类失败', 'detail': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class CategoryDetailView(APIView):
    """分类详情、更新和删除接口"""
    
    def get(self, request, category_id):
        """获取分类详情"""
        from products.application.queries import GetCategoryQuery
        
        try:
            # 创建查询对象
            if isinstance(category_id, uuid.UUID):
                category_uuid = category_id
            else:
                category_uuid = uuid.UUID(category_id)
                
            query = GetCategoryQuery(id=str(category_uuid))
            
            # 调用应用服务
            product_service = get_product_service()
            category = product_service.get_category(query)
            
            # 返回分类详情
            from products.api.serializers import CategorySerializer
            return Response(CategorySerializer(category).data)
        except EntityNotFoundException:
            return Response(
                {'error': '分类不存在', 'detail': f"找不到ID为{category_id}的分类"},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            import traceback
            stack_trace = traceback.format_exc()
            logger.error(f"获取分类详情失败: {str(e)}\n堆栈跟踪:\n{stack_trace}")
            return Response(
                {'error': '获取分类详情失败', 'detail': str(e), 'stack_trace': stack_trace},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def put(self, request, category_id):
        """更新分类"""
        from products.api.serializers import CategoryUpdateSerializer
        from products.application.commands import UpdateCategoryCommand
        
        # 验证请求数据
        serializer = CategoryUpdateSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {'error': '请求数据无效', 'detail': serializer.errors},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # 创建命令对象
        data = serializer.validated_data
        if isinstance(category_id, uuid.UUID):
            category_uuid = category_id
        else:
            category_uuid = uuid.UUID(category_id)
            
        command = UpdateCategoryCommand(
            id=str(category_uuid),
            name=data.get('name'),
            description=data.get('description'),
            parent_id=data.get('parent_id')
        )
        
        # 调用应用服务
        try:
            product_service = get_product_service()
            category = product_service.update_category(command)
            
            # 返回更新后的分类
            from products.api.serializers import CategorySerializer
            return Response(CategorySerializer(category).data)
        except EntityNotFoundException:
            return Response(
                {'error': '分类不存在', 'detail': f"找不到ID为{category_uuid}的分类"},
                status=status.HTTP_404_NOT_FOUND
            )
        except DomainException as e:
            return Response(
                {'error': '领域错误', 'detail': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            import traceback
            stack_trace = traceback.format_exc()
            logger.error(f"更新分类失败: {str(e)}\n堆栈跟踪:\n{stack_trace}")
            return Response(
                {'error': '更新分类失败', 'detail': str(e), 'stack_trace': stack_trace},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def delete(self, request, category_id):
        """删除分类"""
        from products.application.commands import DeleteCategoryCommand
        
        try:
            # 创建命令对象
            if isinstance(category_id, uuid.UUID):
                category_uuid = category_id
            else:
                category_uuid = uuid.UUID(category_id)
                
            command = DeleteCategoryCommand(id=str(category_uuid))
            
            # 调用应用服务
            product_service = get_product_service()
            product_service.delete_category(command)
            
            # 返回成功响应
            return Response(status=status.HTTP_204_NO_CONTENT)
        except EntityNotFoundException:
            return Response(
                {'error': '分类不存在', 'detail': f"找不到ID为{category_id}的分类"},
                status=status.HTTP_404_NOT_FOUND
            )
        except DomainException as e:
            return Response(
                {'error': '领域错误', 'detail': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            import traceback
            stack_trace = traceback.format_exc()
            logger.error(f"删除分类失败: {str(e)}\n堆栈跟踪:\n{stack_trace}")
            return Response(
                {'error': '删除分类失败', 'detail': str(e), 'stack_trace': stack_trace},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            ) 