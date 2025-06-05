from django.db import models

# 引用基础设施层的模型
from products.infrastructure.models.product_models import (
    Product,
    ProductCategory,
    ProductSpecification,
    ProductInventory,
    ProductRating,
    ProductReview
)

# Create your models here.
