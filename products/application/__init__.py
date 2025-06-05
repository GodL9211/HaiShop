"""
商品应用服务层包。
提供商品相关的应用服务、数据传输对象、命令和查询。
"""

# DTO
from products.application.dtos import (
    ProductDTO,
    ProductListDTO,
    CategoryDTO,
    ProductCreateDTO,
    ProductUpdateDTO,
    ProductStockUpdateDTO,
    ProductRatingDTO
)

# 命令
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

# 查询
from products.application.queries import (
    GetProductQuery,
    ListProductsQuery,
    SearchProductsQuery,
    GetProductsByIdsQuery,
    GetRelatedProductsQuery,
    GetCategoryQuery,
    ListCategoriesQuery
)

# 应用服务
from products.application.product_service import ProductApplicationService

__all__ = [
    # DTO
    'ProductDTO',
    'ProductListDTO',
    'CategoryDTO',
    'ProductCreateDTO',
    'ProductUpdateDTO',
    'ProductStockUpdateDTO',
    'ProductRatingDTO',
    
    # 命令
    'CreateProductCommand',
    'UpdateProductCommand',
    'ChangeProductStateCommand',
    'UpdateProductStockCommand',
    'AddProductRatingCommand',
    'CreateCategoryCommand',
    'UpdateCategoryCommand',
    'DeleteCategoryCommand',
    
    # 查询
    'GetProductQuery',
    'ListProductsQuery',
    'SearchProductsQuery',
    'GetProductsByIdsQuery',
    'GetRelatedProductsQuery',
    'GetCategoryQuery',
    'ListCategoriesQuery',
    
    # 应用服务
    'ProductApplicationService',
]
