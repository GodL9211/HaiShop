"""
商品API URL配置。
定义RESTful API的路由映射。
"""
from django.urls import path
from products.api import views

# API URL模式
urlpatterns = [
    # 商品API
    path('products/', views.ProductListCreateView.as_view(), name='product-list-create'),
    path('products/<uuid:product_id>/', views.ProductDetailView.as_view(), name='product-detail'),
    path('products/<uuid:product_id>/state/', views.ProductStateView.as_view(), name='product-state'),
    path('products/<uuid:product_id>/stock/', views.ProductStockView.as_view(), name='product-stock'),
    path('products/<uuid:product_id>/rating/', views.ProductRatingView.as_view(), name='product-rating'),
    path('products/<uuid:product_id>/related/', views.RelatedProductsView.as_view(), name='product-related'),
    
    # 批量操作API
    path('products/batch/', views.ProductBatchView.as_view(), name='product-batch'),
    path('products/batch/stock/', views.ProductBatchStockView.as_view(), name='product-batch-stock'),
    
    # 搜索API
    path('products/search/', views.ProductSearchView.as_view(), name='product-search'),
    
    # 分类API
    path('categories/', views.CategoryListCreateView.as_view(), name='category-list-create'),
    path('categories/<uuid:category_id>/', views.CategoryDetailView.as_view(), name='category-detail'),
] 