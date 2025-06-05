"""
库存锁定服务实现。
结合乐观锁和分布式锁实现可靠的库存并发控制。
"""
from typing import Optional, Any, List, Tuple
import uuid
import time
from datetime import datetime, timedelta
from contextlib import contextmanager

from django.db import transaction, connection, DatabaseError
from django.db.models import F, Q
from django.utils import timezone

from core.domain.exceptions import (
    ConcurrencyException, 
    EntityNotFoundException, 
    LockAcquisitionException
)
from core.infrastructure.cache import CacheService
from products.domain import InventoryLockService
from products.infrastructure.models.product_models import (
    ProductInventory as ProductInventoryModel,
    Product as ProductModel
)


class MySQLInventoryLockService(InventoryLockService):
    """
    基于MySQL的库存锁定服务实现。
    
    结合数据库乐观锁和悲观锁实现可靠的库存并发控制。
    """
    
    def __init__(self, cache_service: CacheService, lock_timeout_seconds: int = 30):
        """
        初始化库存锁定服务。
        
        Args:
            cache_service: 缓存服务，用于分布式锁
            lock_timeout_seconds: 锁定超时时间（秒）
        """
        self.cache_service = cache_service
        self.lock_timeout_seconds = lock_timeout_seconds
    
    @contextmanager
    def lock_inventory(self, product_id: Any, lock_name: Optional[str] = None):
        """
        锁定商品库存的上下文管理器。
        
        结合MySQL的行级锁和乐观锁实现。
        
        Args:
            product_id: 商品ID
            lock_name: 锁名称，不提供则自动生成
            
        Yields:
            锁定成功
            
        Raises:
            EntityNotFoundException: 商品不存在
            LockAcquisitionException: 无法获取锁
        """
        lock_key = f"inventory_lock:{product_id}"
        lock_name = lock_name or f"lock_{uuid.uuid4()}"
        lock_acquired = False
        inventory = None
        
        try:
            # 1. 尝试获取分布式锁
            if not self.cache_service.set_nx(lock_key, lock_name, self.lock_timeout_seconds):
                # 检查锁是否已过期
                self._clean_expired_locks()
                
                # 重试获取锁
                if not self.cache_service.set_nx(lock_key, lock_name, self.lock_timeout_seconds):
                    raise LockAcquisitionException(f"无法获取商品库存锁: {product_id}")
            
            lock_acquired = True
            
            # 2. 获取库存记录并加行锁
            with transaction.atomic():
                try:
                    # 使用select_for_update获取行锁
                    inventory = ProductInventoryModel.objects.select_for_update(nowait=True).get(
                        product_id=product_id
                    )
                    
                    # 标记为锁定状态
                    inventory.is_locked = True
                    inventory.lock_expiry = timezone.now() + timedelta(seconds=self.lock_timeout_seconds)
                    inventory.lock_key = lock_name
                    inventory.save()
                    
                    # 返回上下文
                    yield
                    
                except ProductInventoryModel.DoesNotExist:
                    # 检查商品是否存在
                    if not ProductModel.objects.filter(id=product_id).exists():
                        raise EntityNotFoundException(f"商品不存在: {product_id}")
                    
                    # 创建库存记录
                    inventory = ProductInventoryModel.objects.create(
                        product_id=product_id,
                        available_quantity=0,
                        reserved_quantity=0,
                        is_locked=True,
                        lock_expiry=timezone.now() + timedelta(seconds=self.lock_timeout_seconds),
                        lock_key=lock_name
                    )
                    
                    # 返回上下文
                    yield
                    
                except DatabaseError as e:
                    # 行锁获取失败
                    raise LockAcquisitionException(f"库存正在被其他事务使用: {e}")
        
        finally:
            # 释放锁
            if lock_acquired:
                # 1. 释放数据库锁
                if inventory:
                    try:
                        with transaction.atomic():
                            # 重新获取最新状态
                            updated_inventory = ProductInventoryModel.objects.select_for_update().get(id=inventory.id)
                            # 只有当锁键匹配时才释放，防止释放其他进程的锁
                            if updated_inventory.lock_key == lock_name:
                                updated_inventory.is_locked = False
                                updated_inventory.lock_expiry = None
                                updated_inventory.lock_key = None
                                updated_inventory.save()
                    except Exception:
                        # 如果数据库操作失败，至少尝试释放分布式锁
                        pass
                
                # 2. 释放分布式锁 (仅当锁仍归属于我们时)
                self.cache_service.delete_if_equals(lock_key, lock_name)
    
    def reserve_stock(self, product_id: Any, quantity: int) -> bool:
        """
        预留库存。
        
        Args:
            product_id: 商品ID
            quantity: 预留数量
            
        Returns:
            预留成功返回True，否则False
            
        Raises:
            EntityNotFoundException: 商品不存在
            ConcurrencyException: 并发冲突
        """
        # 使用库存锁和乐观锁进行并发控制
        with self.lock_inventory(product_id):
            with transaction.atomic():
                try:
                    # 使用F表达式和版本号进行乐观锁控制
                    inventory = ProductInventoryModel.objects.get(product_id=product_id)
                    
                    # 检查库存是否充足
                    if inventory.available_quantity < quantity:
                        return False
                    
                    # 预留库存（使用F表达式防止覆盖其他进程的更新）
                    rows_updated = ProductInventoryModel.objects.filter(
                        id=inventory.id,
                        version=inventory.version,
                        available_quantity__gte=quantity
                    ).update(
                        available_quantity=F('available_quantity') - quantity,
                        reserved_quantity=F('reserved_quantity') + quantity,
                        version=F('version') + 1,
                        updated_at=timezone.now()
                    )
                    
                    if rows_updated == 0:
                        # 乐观锁冲突或库存不足
                        raise ConcurrencyException("库存并发更新冲突，请重试")
                    
                    return True
                    
                except ProductInventoryModel.DoesNotExist:
                    raise EntityNotFoundException(f"商品库存不存在: {product_id}")
    
    def release_stock(self, product_id: Any, quantity: int) -> bool:
        """
        释放已预留的库存。
        
        Args:
            product_id: 商品ID
            quantity: 释放数量
            
        Returns:
            释放成功返回True，否则False
            
        Raises:
            EntityNotFoundException: 商品不存在
            ConcurrencyException: 并发冲突
        """
        # 使用库存锁和乐观锁进行并发控制
        with self.lock_inventory(product_id):
            with transaction.atomic():
                try:
                    # 使用F表达式和版本号进行乐观锁控制
                    inventory = ProductInventoryModel.objects.get(product_id=product_id)
                    
                    # 检查预留库存是否充足
                    if inventory.reserved_quantity < quantity:
                        return False
                    
                    # 释放库存（使用F表达式防止覆盖其他进程的更新）
                    rows_updated = ProductInventoryModel.objects.filter(
                        id=inventory.id,
                        version=inventory.version,
                        reserved_quantity__gte=quantity
                    ).update(
                        available_quantity=F('available_quantity') + quantity,
                        reserved_quantity=F('reserved_quantity') - quantity,
                        version=F('version') + 1,
                        updated_at=timezone.now()
                    )
                    
                    if rows_updated == 0:
                        # 乐观锁冲突或预留库存不足
                        raise ConcurrencyException("库存并发更新冲突，请重试")
                    
                    return True
                    
                except ProductInventoryModel.DoesNotExist:
                    raise EntityNotFoundException(f"商品库存不存在: {product_id}")
    
    def confirm_stock(self, product_id: Any, quantity: int) -> bool:
        """
        确认库存，将预留库存转为已消耗。
        
        Args:
            product_id: 商品ID
            quantity: 确认数量
            
        Returns:
            确认成功返回True，否则False
            
        Raises:
            EntityNotFoundException: 商品不存在
            ConcurrencyException: 并发冲突
        """
        # 使用库存锁和乐观锁进行并发控制
        with self.lock_inventory(product_id):
            with transaction.atomic():
                try:
                    # 使用F表达式和版本号进行乐观锁控制
                    inventory = ProductInventoryModel.objects.get(product_id=product_id)
                    
                    # 检查预留库存是否充足
                    if inventory.reserved_quantity < quantity:
                        return False
                    
                    # 确认库存（使用F表达式防止覆盖其他进程的更新）
                    rows_updated = ProductInventoryModel.objects.filter(
                        id=inventory.id,
                        version=inventory.version,
                        reserved_quantity__gte=quantity
                    ).update(
                        reserved_quantity=F('reserved_quantity') - quantity,
                        version=F('version') + 1,
                        updated_at=timezone.now()
                    )
                    
                    if rows_updated == 0:
                        # 乐观锁冲突或预留库存不足
                        raise ConcurrencyException("库存并发更新冲突，请重试")
                    
                    return True
                    
                except ProductInventoryModel.DoesNotExist:
                    raise EntityNotFoundException(f"商品库存不存在: {product_id}")
    
    def batch_reserve_stock(self, items: List[Tuple[Any, int]]) -> List[Tuple[Any, bool, str]]:
        """
        批量预留库存。
        
        Args:
            items: 商品ID和数量的元组列表
            
        Returns:
            (商品ID, 是否成功, 错误信息)的元组列表
        """
        results = []
        
        for product_id, quantity in items:
            try:
                success = self.reserve_stock(product_id, quantity)
                results.append((product_id, success, "" if success else "库存不足"))
            except EntityNotFoundException:
                results.append((product_id, False, "商品不存在"))
            except ConcurrencyException:
                results.append((product_id, False, "并发冲突，请重试"))
            except LockAcquisitionException:
                results.append((product_id, False, "库存锁定失败，请重试"))
            except Exception as e:
                results.append((product_id, False, str(e)))
        
        return results
    
    def _clean_expired_locks(self):
        """清理过期的锁定状态"""
        try:
            # 清理数据库中过期的锁
            ProductInventoryModel.objects.filter(
                is_locked=True,
                lock_expiry__lt=timezone.now()
            ).update(
                is_locked=False,
                lock_expiry=None,
                lock_key=None
            )
        except Exception:
            # 清理过程中出现异常不应影响正常流程
            pass 