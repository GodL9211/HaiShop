"""
统一异常处理器。
提供全局异常处理机制，将各种异常转换为统一的API响应格式。
"""
import logging
import traceback
from django.http import Http404
from django.core.exceptions import ValidationError, PermissionDenied
from django.urls.exceptions import NoReverseMatch
from rest_framework.views import exception_handler
from rest_framework.exceptions import (
    APIException, 
    NotAuthenticated, 
    AuthenticationFailed,
    NotFound, 
    PermissionDenied as DRFPermissionDenied,
    ValidationError as DRFValidationError
)
from rest_framework import status

from core.domain.exceptions import (
    DomainException,
    EntityNotFoundException,
    ConcurrencyException,
    ValidationException,
    AuthorizationException,
    LockAcquisitionException
)
from core.infrastructure.response import ApiResponseBuilder, StatusCode

logger = logging.getLogger(__name__)


def unified_exception_handler(exc, context):
    """
    统一异常处理器，将各种异常转换为统一的API响应格式。
    
    Args:
        exc: 异常对象
        context: 异常上下文
        
    Returns:
        Response: 统一格式的API响应
    """
    # 首先尝试使用DRF的默认处理器
    response = exception_handler(exc, context)
    
    # 记录异常信息
    request = context.get('request')
    if request:
        logger.error(
            f"处理请求时发生异常: {request.method} {request.path}\n"
            f"异常类型: {exc.__class__.__name__}\n"
            f"异常信息: {str(exc)}\n"
            f"异常追踪: {traceback.format_exc()}"
        )
    
    # 根据异常类型返回适当的响应
    
    # 1. 处理领域异常
    if isinstance(exc, EntityNotFoundException):
        return ApiResponseBuilder.fail(
            message=str(exc),
            code=StatusCode.ENTITY_NOT_FOUND,
            http_code=status.HTTP_404_NOT_FOUND
        )
    
    elif isinstance(exc, ValidationException):
        return ApiResponseBuilder.fail(
            message=str(exc),
            code=StatusCode.VALIDATION_ERROR,
            http_code=status.HTTP_400_BAD_REQUEST
        )
    
    elif isinstance(exc, ConcurrencyException):
        return ApiResponseBuilder.fail(
            message=str(exc),
            code=StatusCode.OPTIMISTIC_LOCK_ERROR,
            http_code=status.HTTP_409_CONFLICT
        )
    
    elif isinstance(exc, AuthorizationException):
        return ApiResponseBuilder.fail(
            message=str(exc),
            code=StatusCode.FORBIDDEN,
            http_code=status.HTTP_403_FORBIDDEN
        )
    
    elif isinstance(exc, LockAcquisitionException):
        return ApiResponseBuilder.fail(
            message=str(exc),
            code=StatusCode.CONFLICT,
            http_code=status.HTTP_423_LOCKED
        )
    
    elif isinstance(exc, DomainException):
        return ApiResponseBuilder.fail(
            message=str(exc),
            code=StatusCode.BAD_REQUEST,
            http_code=status.HTTP_400_BAD_REQUEST
        )
    
    # 2. 处理Django异常
    elif isinstance(exc, Http404):
        return ApiResponseBuilder.fail(
            message="请求的资源不存在",
            code=StatusCode.NOT_FOUND,
            http_code=status.HTTP_404_NOT_FOUND
        )
    
    elif isinstance(exc, ValidationError):
        return ApiResponseBuilder.fail(
            message="数据验证失败",
            code=StatusCode.VALIDATION_ERROR,
            data=str(exc),
            http_code=status.HTTP_400_BAD_REQUEST
        )
    
    elif isinstance(exc, PermissionDenied):
        return ApiResponseBuilder.fail(
            message="权限不足",
            code=StatusCode.FORBIDDEN,
            http_code=status.HTTP_403_FORBIDDEN
        )
    
    # 3. 处理DRF异常
    elif isinstance(exc, NotAuthenticated):
        return ApiResponseBuilder.fail(
            message="请先登录",
            code=StatusCode.UNAUTHORIZED,
            http_code=status.HTTP_401_UNAUTHORIZED
        )
    
    elif isinstance(exc, AuthenticationFailed):
        return ApiResponseBuilder.fail(
            message="身份验证失败",
            code=StatusCode.TOKEN_INVALID,
            http_code=status.HTTP_401_UNAUTHORIZED
        )
    
    elif isinstance(exc, DRFPermissionDenied):
        return ApiResponseBuilder.fail(
            message="权限不足",
            code=StatusCode.FORBIDDEN,
            http_code=status.HTTP_403_FORBIDDEN
        )
    
    elif isinstance(exc, NotFound):
        return ApiResponseBuilder.fail(
            message="请求的资源不存在",
            code=StatusCode.NOT_FOUND,
            http_code=status.HTTP_404_NOT_FOUND
        )
    
    elif isinstance(exc, DRFValidationError):
        return ApiResponseBuilder.fail(
            message="数据验证失败",
            code=StatusCode.VALIDATION_ERROR,
            data=exc.detail,
            http_code=status.HTTP_400_BAD_REQUEST
        )
    
    elif isinstance(exc, APIException):
        return ApiResponseBuilder.fail(
            message=str(exc),
            code=StatusCode.BAD_REQUEST,
            http_code=exc.status_code
        )
    
    # 4. 处理其他未预期的异常
    else:
        logger.error(f"未处理的异常: {exc.__class__.__name__} - {str(exc)}\n{traceback.format_exc()}")
        return ApiResponseBuilder.fail(
            message="服务器内部错误",
            code=StatusCode.SERVER_ERROR,
            http_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        ) 