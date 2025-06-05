"""
商品模块配置文件。
从Django设置中获取商品模块的配置。
"""
from django.conf import settings

# 获取商品模块配置，如果不存在则使用默认值
PRODUCT_SETTINGS = getattr(settings, 'PRODUCT_SETTINGS', {})

# 商品图片路径
PRODUCT_IMAGE_PATH = PRODUCT_SETTINGS.get('IMAGE_PATH', 'media/products/')

# 缓存超时设置（秒）
CACHE_TIMEOUT = PRODUCT_SETTINGS.get('CACHE_TIMEOUT', 3600)

# 相关商品数量限制
RELATED_PRODUCTS_LIMIT = PRODUCT_SETTINGS.get('RELATED_PRODUCTS_LIMIT', 5)

# 是否启用草稿商品（在API响应中包含草稿状态的商品）
ENABLE_DRAFT_PRODUCTS = PRODUCT_SETTINGS.get('ENABLE_DRAFT_PRODUCTS', False)

# 商品评分配置
RATING_MIN = 1
RATING_MAX = 10

# 商品搜索配置
SEARCH_RESULT_LIMIT = 50
SEARCH_FACET_LIMIT = 10 