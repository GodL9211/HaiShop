"""
事务管理器模块。
提供事务控制的接口和实现。
"""
from abc import ABC, abstractmethod
from contextlib import contextmanager
from typing import Any, Generator, Optional
from django.db import transaction as django_transaction
from loguru import logger


class TransactionManager(ABC):
    """
    事务管理器接口。
    定义开启、提交和回滚事务的抽象方法。
    """
    
    @abstractmethod
    @contextmanager
    def start(self) -> Generator[None, None, None]:
        """
        开启一个事务。
        返回一个上下文管理器，用于在作用域结束时自动提交或回滚事务。
        
        Yields:
            None
        """
        pass
    
    @abstractmethod
    def commit(self) -> None:
        """
        提交当前事务。
        """
        pass
    
    @abstractmethod
    def rollback(self) -> None:
        """
        回滚当前事务。
        """
        pass


class DjangoTransactionManager(TransactionManager):
    """
    基于Django的事务管理器实现。
    使用Django的事务机制来管理事务。
    """
    
    @contextmanager
    def start(self) -> Generator[None, None, None]:
        """
        使用Django的事务机制开启一个事务。
        
        Yields:
            None
        """
        try:
            with django_transaction.atomic():
                logger.debug("事务已开启")
                yield
                logger.debug("事务已提交")
        except Exception as e:
            logger.error(f"事务回滚: {e}")
            raise
    
    def commit(self) -> None:
        """
        提交当前事务。
        由于使用了Django的atomic()上下文管理器，此方法不需要实际操作。
        """
        logger.debug("显式提交事务")
        # Django的atomic上下文管理器会自动提交事务
        pass
    
    def rollback(self) -> None:
        """
        回滚当前事务。
        由于使用了Django的atomic()上下文管理器，此方法通过抛出异常触发回滚。
        """
        logger.debug("显式回滚事务")
        # Django的atomic上下文管理器会在发生异常时自动回滚事务
        django_transaction.set_rollback(True)


class NoOpTransactionManager(TransactionManager):
    """
    空操作事务管理器。
    用于单元测试或不需要事务的场景。
    """
    
    @contextmanager
    def start(self) -> Generator[None, None, None]:
        """
        模拟开启一个事务，但实际上不做任何操作。
        
        Yields:
            None
        """
        try:
            logger.debug("模拟事务已开启")
            yield
            logger.debug("模拟事务已提交")
        except Exception:
            logger.debug("模拟事务已回滚")
            raise
    
    def commit(self) -> None:
        """
        模拟提交事务，但实际上不做任何操作。
        """
        logger.debug("模拟提交事务")
        pass
    
    def rollback(self) -> None:
        """
        模拟回滚事务，但实际上不做任何操作。
        """
        logger.debug("模拟回滚事务")
        pass 