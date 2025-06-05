"""
商品模块URL配置。
包含API路由和其他页面路由。
"""
from django.urls import path, include

urlpatterns = [
    # API路由
    path('api/', include('products.api.urls')),
    
    # 其他页面路由（如后台管理页面等）
    # ...
] 