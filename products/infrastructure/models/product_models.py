"""
商品基础设施层数据库模型。
定义与商品领域相关的Django ORM模型。
"""
import uuid
from decimal import Decimal
from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()


class ProductCategory(models.Model):
    """商品分类数据库模型"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100, verbose_name="分类名称")
    description = models.TextField(blank=True, verbose_name="分类描述")
    parent = models.ForeignKey(
        'self', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='children',
        verbose_name="父分类"
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新时间")
    
    class Meta:
        db_table = 'product_category'
        verbose_name = "商品分类"
        verbose_name_plural = "商品分类"
        indexes = [
            models.Index(fields=['name'], name='idx_category_name'),
            models.Index(fields=['parent'], name='idx_category_parent'),
        ]
    
    def __str__(self):
        return self.name


class Product(models.Model):
    """商品数据库模型"""
    
    # 商品状态选项
    class StateChoices(models.TextChoices):
        DRAFT = 'draft', '草稿'
        ACTIVE = 'active', '激活'
        INACTIVE = 'inactive', '未激活'
        DELETED = 'deleted', '已删除'
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=200, verbose_name="商品名称")
    description = models.TextField(blank=True, verbose_name="商品描述")
    price_amount = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        verbose_name="价格金额"
    )
    price_currency = models.CharField(
        max_length=3, 
        default="CNY", 
        verbose_name="价格货币"
    )
    keywords = models.CharField(
        max_length=500, 
        blank=True, 
        verbose_name="搜索关键词"
    )
    category = models.ForeignKey(
        ProductCategory, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='products',
        verbose_name="商品分类"
    )
    state = models.CharField(
        max_length=20, 
        choices=StateChoices.choices, 
        default=StateChoices.DRAFT,
        verbose_name="商品状态"
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新时间")
    
    # 版本号，用于乐观锁
    version = models.PositiveIntegerField(default=0, verbose_name="版本号")
    
    class Meta:
        db_table = 'product'
        verbose_name = "商品"
        verbose_name_plural = "商品"
        indexes = [
            models.Index(fields=['name'], name='idx_product_name'),
            models.Index(fields=['state'], name='idx_product_state'),
            models.Index(fields=['category'], name='idx_product_category'),
            models.Index(fields=['keywords'], name='idx_product_keywords'),
            models.Index(fields=['updated_at'], name='idx_product_updated'),
            # 添加复合索引，优化常用查询场景
            models.Index(fields=['state', 'category'], name='idx_product_state_category'),
            models.Index(fields=['state', 'updated_at'], name='idx_product_state_updated'),
            models.Index(fields=['state', 'price_amount'], name='idx_product_state_price'),
            # 使用条件索引，仅对活跃商品创建索引，减少索引维护开销
            models.Index(fields=['price_amount'], condition=models.Q(state='active'), name='idx_active_price'),
            # 为全文搜索创建专用索引
            models.Index(fields=['name', 'keywords'], name='idx_name_keywords'),
        ]
        
        # 添加数据库级别约束
        constraints = [
            # 确保价格不为负数
            models.CheckConstraint(check=models.Q(price_amount__gte=0), name='price_amount_gte_0'),
        ]
    
    def __str__(self):
        return self.name


class ProductSpecification(models.Model):
    """商品规格数据库模型"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    product = models.OneToOneField(
        Product, 
        on_delete=models.CASCADE, 
        related_name='specification',
        verbose_name="商品"
    )
    attributes = models.JSONField(default=dict, verbose_name="规格属性")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新时间")
    
    class Meta:
        db_table = 'product_specification'
        verbose_name = "商品规格"
        verbose_name_plural = "商品规格"
    
    def __str__(self):
        return f"{self.product.name}的规格"


class ProductInventory(models.Model):
    """商品库存数据库模型"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    product = models.OneToOneField(
        Product, 
        on_delete=models.CASCADE, 
        related_name='inventory',
        verbose_name="商品"
    )
    available_quantity = models.PositiveIntegerField(default=0, verbose_name="可用数量")
    reserved_quantity = models.PositiveIntegerField(default=0, verbose_name="预留数量")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新时间")
    
    # 版本号，用于乐观锁
    version = models.PositiveIntegerField(default=0, verbose_name="版本号")
    
    # 添加锁定信息，跟踪锁定状态
    is_locked = models.BooleanField(default=False, verbose_name="是否锁定")
    lock_expiry = models.DateTimeField(null=True, blank=True, verbose_name="锁定过期时间")
    lock_key = models.CharField(max_length=100, null=True, blank=True, verbose_name="锁定键")
    
    class Meta:
        db_table = 'product_inventory'
        verbose_name = "商品库存"
        verbose_name_plural = "商品库存"
        indexes = [
            # 添加库存索引，优化库存查询和更新
            models.Index(fields=['is_locked'], name='idx_inventory_locked'),
            models.Index(fields=['lock_expiry'], name='idx_inventory_lock_expiry'),
            models.Index(fields=['available_quantity'], name='idx_inventory_available_qty'),
        ]
    
    def __str__(self):
        return f"{self.product.name}的库存"
    
    @property
    def total_quantity(self):
        """总库存数量"""
        return self.available_quantity + self.reserved_quantity


class ProductRating(models.Model):
    """商品评分数据库模型"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    product = models.OneToOneField(
        Product, 
        on_delete=models.CASCADE, 
        related_name='rating',
        verbose_name="商品"
    )
    rating_value = models.DecimalField(
        max_digits=2, 
        decimal_places=1, 
        default=0.0,
        verbose_name="评分值"
    )
    rating_count = models.PositiveIntegerField(default=0, verbose_name="评分数量")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新时间")
    
    class Meta:
        db_table = 'product_rating'
        verbose_name = "商品评分"
        verbose_name_plural = "商品评分"
    
    def __str__(self):
        return f"{self.product.name}的评分"


class ProductReview(models.Model):
    """商品评价数据库模型"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    product = models.ForeignKey(
        Product, 
        on_delete=models.CASCADE, 
        related_name='reviews',
        verbose_name="商品"
    )
    user = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True,
        related_name='product_reviews',
        verbose_name="用户"
    )
    rating = models.PositiveSmallIntegerField(verbose_name="评分(1-5)")
    content = models.TextField(verbose_name="评价内容")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新时间")
    
    class Meta:
        db_table = 'product_review'
        verbose_name = "商品评价"
        verbose_name_plural = "商品评价"
        indexes = [
            models.Index(fields=['product'], name='idx_review_product'),
            models.Index(fields=['user'], name='idx_review_user'),
            models.Index(fields=['rating'], name='idx_review_rating'),
            models.Index(fields=['created_at'], name='idx_review_created'),
        ]
    
    def __str__(self):
        return f"{self.user}对{self.product.name}的评价" 