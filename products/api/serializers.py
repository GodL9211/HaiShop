"""
商品API序列化器。
负责请求和响应的序列化、反序列化和验证。
"""
from rest_framework import serializers
from django.core.validators import MinValueValidator, MaxValueValidator
import uuid

# 商品序列化器
class ProductCreateSerializer(serializers.Serializer):
    """创建商品请求序列化器"""
    name = serializers.CharField(max_length=200, required=True)
    description = serializers.CharField(required=False, allow_blank=True)
    price_amount = serializers.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        validators=[MinValueValidator(0)]
    )
    price_currency = serializers.CharField(max_length=3, default="CNY")
    keywords = serializers.CharField(max_length=500, required=False, allow_blank=True)
    category_id = serializers.UUIDField(required=False, allow_null=True)
    attributes = serializers.JSONField(required=False, default=dict)
    stock_quantity = serializers.IntegerField(
        default=0,
        validators=[MinValueValidator(0)]
    )


class ProductUpdateSerializer(serializers.Serializer):
    """更新商品请求序列化器"""
    name = serializers.CharField(max_length=200, required=False)
    description = serializers.CharField(required=False, allow_blank=True)
    price_amount = serializers.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        validators=[MinValueValidator(0)],
        required=False
    )
    price_currency = serializers.CharField(max_length=3, required=False)
    keywords = serializers.CharField(max_length=500, required=False, allow_blank=True)
    category_id = serializers.UUIDField(required=False, allow_null=True)
    attributes = serializers.JSONField(required=False)


class ProductStateChangeSerializer(serializers.Serializer):
    """商品状态更改请求序列化器"""
    state = serializers.ChoiceField(
        choices=['draft', 'active', 'inactive', 'deleted'],
        required=True
    )


class ProductStockUpdateSerializer(serializers.Serializer):
    """商品库存更新请求序列化器"""
    available_quantity = serializers.IntegerField(
        validators=[MinValueValidator(0)],
        required=True
    )
    reserved_quantity = serializers.IntegerField(
        validators=[MinValueValidator(0)],
        required=False,
        default=0
    )


class ProductBatchStockUpdateSerializer(serializers.Serializer):
    """批量更新商品库存请求序列化器"""
    items = serializers.ListField(
        child=serializers.DictField(),
        min_length=1
    )

    def validate_items(self, value):
        """验证每个库存项都包含正确的字段"""
        for item in value:
            if 'product_id' not in item:
                raise serializers.ValidationError("每个库存项必须包含product_id字段")
            if 'available_quantity' not in item:
                raise serializers.ValidationError("每个库存项必须包含available_quantity字段")
            
            try:
                # 确保product_id可以转换为有效的UUID
                product_id_str = str(item['product_id'])
                uuid.UUID(product_id_str)
            except ValueError:
                raise serializers.ValidationError(f"无效的商品ID格式: {item['product_id']}")
            
            # 确保available_quantity是整数
            if not isinstance(item['available_quantity'], int) and not str(item['available_quantity']).isdigit():
                raise serializers.ValidationError("可用数量必须是整数")
            
            if int(item['available_quantity']) < 0:
                raise serializers.ValidationError("可用数量不能为负数")
                
            # 检查reserved_quantity（如果存在）
            if 'reserved_quantity' in item:
                if not isinstance(item['reserved_quantity'], int) and not str(item['reserved_quantity']).isdigit():
                    raise serializers.ValidationError("预留数量必须是整数")
                
                if int(item['reserved_quantity']) < 0:
                    raise serializers.ValidationError("预留数量不能为负数")
        return value


class ProductRatingSerializer(serializers.Serializer):
    """商品评分请求序列化器"""
    rating = serializers.IntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        required=True
    )
    content = serializers.CharField(required=False, allow_blank=True)


# 分类序列化器
class CategoryCreateSerializer(serializers.Serializer):
    """创建分类请求序列化器"""
    name = serializers.CharField(max_length=100, required=True)
    description = serializers.CharField(required=False, allow_blank=True)
    parent_id = serializers.UUIDField(required=False, allow_null=True)


class CategoryUpdateSerializer(serializers.Serializer):
    """更新分类请求序列化器"""
    name = serializers.CharField(max_length=100, required=False)
    description = serializers.CharField(required=False, allow_blank=True)
    parent_id = serializers.UUIDField(required=False, allow_null=True)


# 搜索序列化器
class ProductSearchSerializer(serializers.Serializer):
    """商品搜索请求序列化器"""
    keyword = serializers.CharField(required=False, allow_blank=True)
    category_id = serializers.UUIDField(required=False, allow_null=True)
    min_price = serializers.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        required=False,
        allow_null=True
    )
    max_price = serializers.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        required=False,
        allow_null=True
    )
    page = serializers.IntegerField(min_value=1, default=1)
    page_size = serializers.IntegerField(min_value=1, max_value=100, default=20)
    include_facets = serializers.BooleanField(default=True)
    facet_fields = serializers.ListField(
        child=serializers.CharField(),
        required=False,
        allow_empty=True
    )
    selected_facets = serializers.DictField(
        child=serializers.ListField(child=serializers.CharField()),
        required=False
    )


# 批量操作序列化器
class ProductBatchGetSerializer(serializers.Serializer):
    """批量获取商品请求序列化器"""
    product_ids = serializers.ListField(
        child=serializers.UUIDField(),
        min_length=1,
        max_length=100
    )


# 响应序列化器
class MoneySerializer(serializers.Serializer):
    """金额值对象序列化器"""
    amount = serializers.DecimalField(max_digits=10, decimal_places=2, allow_null=True)
    currency = serializers.CharField(max_length=3, allow_null=True, allow_blank=True)
    
    def to_representation(self, instance):
        """
        确保能够处理字典或具有amount和currency属性的对象
        """
        if instance is None:
            return {'amount': None, 'currency': None}
            
        if isinstance(instance, dict):
            return {
                'amount': instance.get('amount'),
                'currency': instance.get('currency')
            }
        
        try:
            return {
                'amount': instance.amount,
                'currency': instance.currency
            }
        except AttributeError:
            return {'amount': None, 'currency': None}


class ProductSpecificationSerializer(serializers.Serializer):
    """商品规格序列化器"""
    
    def to_representation(self, instance):
        """
        直接返回规格字典，不需要attributes键
        """
        # 如果已经是字典，直接返回
        if isinstance(instance, dict):
            return instance
        # 如果有attributes属性，返回它
        if hasattr(instance, 'attributes'):
            return instance.attributes
        # 否则返回空字典
        return {}


class CategorySerializer(serializers.Serializer):
    """分类响应序列化器"""
    id = serializers.UUIDField()
    name = serializers.CharField()
    description = serializers.CharField()
    parent_id = serializers.UUIDField(allow_null=True)


class ProductListItemSerializer(serializers.Serializer):
    """商品列表项响应序列化器"""
    id = serializers.UUIDField(allow_null=True)
    name = serializers.CharField(allow_null=True)
    price = MoneySerializer()
    category_id = serializers.UUIDField(allow_null=True)
    state = serializers.CharField(allow_null=True)
    rating_value = serializers.DecimalField(max_digits=2, decimal_places=1, allow_null=True)
    rating_count = serializers.IntegerField(allow_null=True)
    stock_available = serializers.IntegerField(allow_null=True)
    created_at = serializers.DateTimeField(allow_null=True)
    updated_at = serializers.DateTimeField(allow_null=True)


class ProductDetailSerializer(serializers.Serializer):
    """商品详情响应序列化器"""
    id = serializers.UUIDField(allow_null=True)
    name = serializers.CharField(allow_null=True)
    description = serializers.CharField(allow_null=True, allow_blank=True)
    price = MoneySerializer()
    keywords = serializers.CharField(allow_null=True, allow_blank=True)
    category_id = serializers.UUIDField(allow_null=True)
    specification = serializers.DictField(allow_null=True)
    state = serializers.CharField(allow_null=True)
    rating_value = serializers.DecimalField(max_digits=2, decimal_places=1, allow_null=True)
    rating_count = serializers.IntegerField(allow_null=True)
    stock_available = serializers.IntegerField(allow_null=True)
    stock_reserved = serializers.IntegerField(allow_null=True)
    created_at = serializers.DateTimeField(allow_null=True)
    updated_at = serializers.DateTimeField(allow_null=True)


class PaginatedResponseSerializer(serializers.Serializer):
    """分页响应序列化器"""
    count = serializers.IntegerField()
    next = serializers.BooleanField()
    previous = serializers.BooleanField()
    page = serializers.IntegerField()
    page_size = serializers.IntegerField()
    results = serializers.ListField(child=serializers.DictField())


class FacetValueSerializer(serializers.Serializer):
    """分面值响应序列化器"""
    value = serializers.CharField(allow_null=True)
    count = serializers.IntegerField()
    selected = serializers.BooleanField(default=False)


class FacetSerializer(serializers.Serializer):
    """分面响应序列化器"""
    name = serializers.CharField()
    display_name = serializers.CharField()
    type = serializers.CharField(default="terms")
    values = FacetValueSerializer(many=True)


class SearchResponseSerializer(PaginatedResponseSerializer):
    """搜索响应序列化器"""
    facets = FacetSerializer(many=True, required=False) 