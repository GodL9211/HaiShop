"""
统一响应封装模块。
提供API响应的标准化结构，包括业务状态码、成功标志、消息、数据等。
"""
import time
import uuid
import typing as t
from django.conf import settings
from rest_framework.response import Response
from rest_framework import status as http_status
from dataclasses import dataclass, field


@dataclass
class ApiResponse:
    """API响应数据结构"""
    code: int = 10000  # 业务状态码
    success: bool = True  # 是否成功
    message: str = "操作成功"  # 响应消息
    data: t.Any = None  # 响应数据
    timestamp: int = field(default_factory=lambda: int(time.time() * 1000))  # 时间戳，毫秒级
    trace_id: str = field(default_factory=lambda: str(uuid.uuid4()))  # 追踪ID
    metadata: t.Dict[str, t.Any] = field(default_factory=dict)  # 元数据

    def to_dict(self) -> dict:
        """转换为字典"""
        result = {
            "code": self.code,
            "success": self.success,
            "message": self.message,
            "timestamp": self.timestamp,
            "traceId": self.trace_id,
        }
        
        # 只有在有数据时才添加data字段
        if self.data is not None:
            result["data"] = self.data
            
        # 只有在有元数据时才添加metadata字段
        if self.metadata:
            result["metadata"] = self.metadata
            
        return result


class ApiResponseBuilder:
    """API响应构建器"""
    
    @staticmethod
    def success(
        data: t.Any = None, 
        message: str = "操作成功", 
        code: int = 10000,
        metadata: t.Dict[str, t.Any] = None
    ) -> Response:
        """
        创建成功响应
        
        Args:
            data: 响应数据
            message: 响应消息
            code: 业务状态码
            metadata: 元数据
            
        Returns:
            Response: DRF响应对象
        """
        response = ApiResponse(
            code=code,
            success=True,
            message=message,
            data=data,
            metadata=metadata or {}
        )
        return Response(response.to_dict(), status=http_status.HTTP_200_OK)
    
    @staticmethod
    def created(
        data: t.Any = None, 
        message: str = "创建成功", 
        code: int = 10000,
        metadata: t.Dict[str, t.Any] = None
    ) -> Response:
        """
        创建资源成功响应
        
        Args:
            data: 响应数据
            message: 响应消息
            code: 业务状态码
            metadata: 元数据
            
        Returns:
            Response: DRF响应对象
        """
        response = ApiResponse(
            code=code,
            success=True,
            message=message,
            data=data,
            metadata=metadata or {}
        )
        return Response(response.to_dict(), status=http_status.HTTP_201_CREATED)
    
    @staticmethod
    def fail(
        message: str = "操作失败", 
        code: int = 50000, 
        data: t.Any = None,
        http_code: int = http_status.HTTP_400_BAD_REQUEST,
        metadata: t.Dict[str, t.Any] = None
    ) -> Response:
        """
        创建失败响应
        
        Args:
            message: 错误消息
            code: 业务状态码
            data: 错误详情数据
            http_code: HTTP状态码
            metadata: 元数据
            
        Returns:
            Response: DRF响应对象
        """
        response = ApiResponse(
            code=code,
            success=False,
            message=message,
            data=data,
            metadata=metadata or {}
        )
        return Response(response.to_dict(), status=http_code)
    
    @staticmethod
    def paginated(
        items: list,
        total: int,
        page: int,
        page_size: int,
        message: str = "查询成功",
        code: int = 10000,
        metadata: t.Dict[str, t.Any] = None
    ) -> Response:
        """
        创建分页响应
        
        Args:
            items: 分页项列表
            total: 总项数
            page: 当前页码
            page_size: 每页大小
            message: 响应消息
            code: 业务状态码
            metadata: 元数据
            
        Returns:
            Response: DRF响应对象
        """
        pagination_data = {
            "items": items,
            "pagination": {
                "total": total,
                "page": page,
                "pageSize": page_size,
                "hasMore": page * page_size < total
            }
        }
        
        response = ApiResponse(
            code=code,
            success=True,
            message=message,
            data=pagination_data,
            metadata=metadata or {}
        )
        return Response(response.to_dict(), status=http_status.HTTP_200_OK)


# 状态码枚举
class StatusCode:
    """业务状态码定义"""
    
    # 成功状态码 (1xxxx)
    SUCCESS = 10000                # 通用成功
    CREATED = 10001                # 创建成功
    UPDATED = 10002                # 更新成功
    DELETED = 10003                # 删除成功
    
    # 客户端错误 (4xxxx)
    # 通用客户端错误 (400xx)
    BAD_REQUEST = 40000            # 错误的请求
    VALIDATION_ERROR = 40001       # 数据验证错误
    PARAM_ERROR = 40002            # 参数错误
    MISSING_PARAM = 40003          # 缺少参数
    
    # 认证和授权错误 (401xx-403xx)
    UNAUTHORIZED = 40100           # 未认证
    LOGIN_EXPIRED = 40101          # 登录过期
    TOKEN_INVALID = 40102          # 无效的令牌
    FORBIDDEN = 40300              # 权限不足
    
    # 资源错误 (404xx)
    NOT_FOUND = 40400              # 资源不存在
    ENTITY_NOT_FOUND = 40401       # 实体不存在
    USER_NOT_FOUND = 40402         # 用户不存在
    PRODUCT_NOT_FOUND = 40403      # 商品不存在
    ORDER_NOT_FOUND = 40404        # 订单不存在
    
    # 操作冲突 (409xx)
    CONFLICT = 40900               # 资源冲突
    OPTIMISTIC_LOCK_ERROR = 40901  # 乐观锁冲突
    DUPLICATE_ENTITY = 40902       # 实体重复
    
    # 商品模块错误 (410xx)
    PRODUCT_OFFLINE = 41000        # 商品已下线
    PRODUCT_STOCK_INSUFFICIENT = 41001  # 商品库存不足
    
    # 订单模块错误 (411xx)
    ORDER_CLOSED = 41100           # 订单已关闭
    ORDER_PAID = 41101             # 订单已支付
    ORDER_EXPIRED = 41102          # 订单已过期
    
    # 服务端错误 (5xxxx)
    SERVER_ERROR = 50000           # 服务器内部错误
    SERVICE_UNAVAILABLE = 50001    # 服务不可用
    DATABASE_ERROR = 50002         # 数据库错误
    CACHE_ERROR = 50003            # 缓存错误
    TIMEOUT_ERROR = 50004          # 超时错误
    THIRD_PARTY_SERVICE_ERROR = 50005  # 第三方服务错误


# 状态码对应的默认消息
STATUS_MESSAGE_MAPPING = {
    # 成功消息
    StatusCode.SUCCESS: "操作成功",
    StatusCode.CREATED: "创建成功",
    StatusCode.UPDATED: "更新成功",
    StatusCode.DELETED: "删除成功",
    
    # 客户端错误消息
    StatusCode.BAD_REQUEST: "请求参数错误",
    StatusCode.VALIDATION_ERROR: "数据验证失败",
    StatusCode.PARAM_ERROR: "参数错误",
    StatusCode.MISSING_PARAM: "缺少必要参数",
    
    # 认证和授权错误
    StatusCode.UNAUTHORIZED: "请先登录",
    StatusCode.LOGIN_EXPIRED: "登录已过期，请重新登录",
    StatusCode.TOKEN_INVALID: "无效的令牌",
    StatusCode.FORBIDDEN: "权限不足",
    
    # 资源错误
    StatusCode.NOT_FOUND: "资源不存在",
    StatusCode.ENTITY_NOT_FOUND: "实体不存在",
    StatusCode.USER_NOT_FOUND: "用户不存在",
    StatusCode.PRODUCT_NOT_FOUND: "商品不存在",
    StatusCode.ORDER_NOT_FOUND: "订单不存在",
    
    # 操作冲突
    StatusCode.CONFLICT: "资源冲突",
    StatusCode.OPTIMISTIC_LOCK_ERROR: "数据已被其他用户修改",
    StatusCode.DUPLICATE_ENTITY: "实体已存在",
    
    # 商品模块错误
    StatusCode.PRODUCT_OFFLINE: "商品已下线",
    StatusCode.PRODUCT_STOCK_INSUFFICIENT: "商品库存不足",
    
    # 订单模块错误
    StatusCode.ORDER_CLOSED: "订单已关闭",
    StatusCode.ORDER_PAID: "订单已支付",
    StatusCode.ORDER_EXPIRED: "订单已过期",
    
    # 服务端错误
    StatusCode.SERVER_ERROR: "服务器内部错误",
    StatusCode.SERVICE_UNAVAILABLE: "服务暂时不可用",
    StatusCode.DATABASE_ERROR: "数据库错误",
    StatusCode.CACHE_ERROR: "缓存服务错误",
    StatusCode.TIMEOUT_ERROR: "服务超时",
    StatusCode.THIRD_PARTY_SERVICE_ERROR: "第三方服务异常"
}


def get_status_message(code: int) -> str:
    """
    根据状态码获取对应的消息
    
    Args:
        code: 业务状态码
        
    Returns:
        str: 状态消息
    """
    return STATUS_MESSAGE_MAPPING.get(code, "未知状态") 