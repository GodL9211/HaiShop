# Generated by Django 5.2 on 2025-06-04 15:59

import django.db.models.deletion
import uuid
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='ProductCategory',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('name', models.CharField(max_length=100, verbose_name='分类名称')),
                ('description', models.TextField(blank=True, verbose_name='分类描述')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='创建时间')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='更新时间')),
                ('parent', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='children', to='products.productcategory', verbose_name='父分类')),
            ],
            options={
                'verbose_name': '商品分类',
                'verbose_name_plural': '商品分类',
                'db_table': 'product_category',
            },
        ),
        migrations.CreateModel(
            name='Product',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('name', models.CharField(max_length=200, verbose_name='商品名称')),
                ('description', models.TextField(blank=True, verbose_name='商品描述')),
                ('price_amount', models.DecimalField(decimal_places=2, max_digits=10, verbose_name='价格金额')),
                ('price_currency', models.CharField(default='CNY', max_length=3, verbose_name='价格货币')),
                ('keywords', models.CharField(blank=True, max_length=500, verbose_name='搜索关键词')),
                ('state', models.CharField(choices=[('draft', '草稿'), ('active', '激活'), ('inactive', '未激活'), ('deleted', '已删除')], default='draft', max_length=20, verbose_name='商品状态')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='创建时间')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='更新时间')),
                ('version', models.PositiveIntegerField(default=0, verbose_name='版本号')),
                ('category', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='products', to='products.productcategory', verbose_name='商品分类')),
            ],
            options={
                'verbose_name': '商品',
                'verbose_name_plural': '商品',
                'db_table': 'product',
            },
        ),
        migrations.CreateModel(
            name='ProductInventory',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('available_quantity', models.PositiveIntegerField(default=0, verbose_name='可用数量')),
                ('reserved_quantity', models.PositiveIntegerField(default=0, verbose_name='预留数量')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='创建时间')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='更新时间')),
                ('version', models.PositiveIntegerField(default=0, verbose_name='版本号')),
                ('is_locked', models.BooleanField(default=False, verbose_name='是否锁定')),
                ('lock_expiry', models.DateTimeField(blank=True, null=True, verbose_name='锁定过期时间')),
                ('lock_key', models.CharField(blank=True, max_length=100, null=True, verbose_name='锁定键')),
                ('product', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='inventory', to='products.product', verbose_name='商品')),
            ],
            options={
                'verbose_name': '商品库存',
                'verbose_name_plural': '商品库存',
                'db_table': 'product_inventory',
            },
        ),
        migrations.CreateModel(
            name='ProductRating',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('rating_value', models.DecimalField(decimal_places=1, default=0.0, max_digits=2, verbose_name='评分值')),
                ('rating_count', models.PositiveIntegerField(default=0, verbose_name='评分数量')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='创建时间')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='更新时间')),
                ('product', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='rating', to='products.product', verbose_name='商品')),
            ],
            options={
                'verbose_name': '商品评分',
                'verbose_name_plural': '商品评分',
                'db_table': 'product_rating',
            },
        ),
        migrations.CreateModel(
            name='ProductReview',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('rating', models.PositiveSmallIntegerField(verbose_name='评分(1-5)')),
                ('content', models.TextField(verbose_name='评价内容')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='创建时间')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='更新时间')),
                ('product', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='reviews', to='products.product', verbose_name='商品')),
                ('user', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='product_reviews', to=settings.AUTH_USER_MODEL, verbose_name='用户')),
            ],
            options={
                'verbose_name': '商品评价',
                'verbose_name_plural': '商品评价',
                'db_table': 'product_review',
            },
        ),
        migrations.CreateModel(
            name='ProductSpecification',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('attributes', models.JSONField(default=dict, verbose_name='规格属性')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='创建时间')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='更新时间')),
                ('product', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='specification', to='products.product', verbose_name='商品')),
            ],
            options={
                'verbose_name': '商品规格',
                'verbose_name_plural': '商品规格',
                'db_table': 'product_specification',
            },
        ),
        migrations.AddIndex(
            model_name='productcategory',
            index=models.Index(fields=['name'], name='idx_category_name'),
        ),
        migrations.AddIndex(
            model_name='productcategory',
            index=models.Index(fields=['parent'], name='idx_category_parent'),
        ),
        migrations.AddIndex(
            model_name='product',
            index=models.Index(fields=['name'], name='idx_product_name'),
        ),
        migrations.AddIndex(
            model_name='product',
            index=models.Index(fields=['state'], name='idx_product_state'),
        ),
        migrations.AddIndex(
            model_name='product',
            index=models.Index(fields=['category'], name='idx_product_category'),
        ),
        migrations.AddIndex(
            model_name='product',
            index=models.Index(fields=['keywords'], name='idx_product_keywords'),
        ),
        migrations.AddIndex(
            model_name='product',
            index=models.Index(fields=['updated_at'], name='idx_product_updated'),
        ),
        migrations.AddIndex(
            model_name='product',
            index=models.Index(fields=['state', 'category'], name='idx_product_state_category'),
        ),
        migrations.AddIndex(
            model_name='product',
            index=models.Index(fields=['state', 'updated_at'], name='idx_product_state_updated'),
        ),
        migrations.AddIndex(
            model_name='product',
            index=models.Index(fields=['state', 'price_amount'], name='idx_product_state_price'),
        ),
        migrations.AddIndex(
            model_name='product',
            index=models.Index(condition=models.Q(('state', 'active')), fields=['price_amount'], name='idx_active_price'),
        ),
        migrations.AddIndex(
            model_name='product',
            index=models.Index(fields=['name', 'keywords'], name='idx_name_keywords'),
        ),
        migrations.AddConstraint(
            model_name='product',
            constraint=models.CheckConstraint(condition=models.Q(('price_amount__gte', 0)), name='price_amount_gte_0'),
        ),
        migrations.AddIndex(
            model_name='productinventory',
            index=models.Index(fields=['is_locked'], name='idx_inventory_locked'),
        ),
        migrations.AddIndex(
            model_name='productinventory',
            index=models.Index(fields=['lock_expiry'], name='idx_inventory_lock_expiry'),
        ),
        migrations.AddIndex(
            model_name='productinventory',
            index=models.Index(fields=['available_quantity'], name='idx_inventory_available_qty'),
        ),
        migrations.AddIndex(
            model_name='productreview',
            index=models.Index(fields=['product'], name='idx_review_product'),
        ),
        migrations.AddIndex(
            model_name='productreview',
            index=models.Index(fields=['user'], name='idx_review_user'),
        ),
        migrations.AddIndex(
            model_name='productreview',
            index=models.Index(fields=['rating'], name='idx_review_rating'),
        ),
        migrations.AddIndex(
            model_name='productreview',
            index=models.Index(fields=['created_at'], name='idx_review_created'),
        ),
    ]
