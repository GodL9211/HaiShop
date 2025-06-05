"""
商品API异常处理器。
提供统一的异常处理机制，转换领域异常为HTTP响应。
"""
from rest_framework.views import exception_handler
from rest_framework.response import Response
from rest_framework import status
import logging
from rest_framework.exceptions import NotFound
from django.http import Http404
from django.urls.exceptions import NoReverseMatch
from django.core.exceptions import ValidationError
import uuid

from core.domain.exceptions import (
    DomainException,
    EntityNotFoundException,
    ConcurrencyException,
    ValidationException,
    AuthorizationException,
    LockAcquisitionException
)

logger = logging.getLogger(__name__)


def api_exception_handler(exc, context):
    """
    自定义异常处理器，将领域异常转换为HTTP响应。
    
    Args:
        exc: 异常对象
        context: 异常上下文
        
    Returns:
        HTTP响应对象
    """
    # 首先调用DRF默认的异常处理器
    response = exception_handler(exc, context)
    
    # 如果默认处理器已经处理了异常，直接返回
    if response is not None:
        return response
    
    # 处理领域异常
    if isinstance(exc, EntityNotFoundException):
        return Response(
            {'error': '实体不存在', 'detail': str(exc)},
            status=status.HTTP_404_NOT_FOUND
        )
    
    elif isinstance(exc, ValidationException):
        return Response(
            {'error': '数据验证失败', 'detail': str(exc)},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    elif isinstance(exc, ConcurrencyException):
        return Response(
            {'error': '并发冲突', 'detail': str(exc)},
            status=status.HTTP_409_CONFLICT
        )
    
    elif isinstance(exc, AuthorizationException):
        return Response(
            {'error': '权限不足', 'detail': str(exc)},
            status=status.HTTP_403_FORBIDDEN
        )
    
    elif isinstance(exc, LockAcquisitionException):
        return Response(
            {'error': '资源锁定失败', 'detail': str(exc)},
            status=status.HTTP_423_LOCKED
        )
    
    elif isinstance(exc, DomainException):
        return Response(
            {'error': '领域错误', 'detail': str(exc)},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # 处理未知异常
    logger.error(f"未处理的异常: {exc.__class__.__name__} - {str(exc)}")
    return Response(
        {'error': '服务器内部错误', 'detail': '请联系管理员'},
        status=status.HTTP_500_INTERNAL_SERVER_ERROR
    )