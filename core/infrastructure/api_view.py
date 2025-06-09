"""
API视图基类。
提供统一的API视图类，用于规范API响应格式和处理通用逻辑。
"""
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.viewsets import ViewSet

from core.infrastructure.response import ApiResponseBuilder, StatusCode


class ApiBaseView(APIView):
    """API视图基类，提供统一的响应方法"""
    
    def success_response(self, data=None, message="操作成功", code=StatusCode.SUCCESS, metadata=None):
        """
        成功响应
        
        Args:
            data: 响应数据
            message: 响应消息
            code: 业务状态码
            metadata: 元数据
            
        Returns:
            Response: 统一格式的响应
        """
        return ApiResponseBuilder.success(data=data, message=message, code=code, metadata=metadata)
    
    def created_response(self, data=None, message="创建成功", code=StatusCode.CREATED, metadata=None):
        """
        创建成功响应
        
        Args:
            data: 响应数据
            message: 响应消息
            code: 业务状态码
            metadata: 元数据
            
        Returns:
            Response: 统一格式的响应
        """
        return ApiResponseBuilder.created(data=data, message=message, code=code, metadata=metadata)
    
    def failed_response(self, message="操作失败", code=StatusCode.BAD_REQUEST, 
                        data=None, http_code=status.HTTP_400_BAD_REQUEST, metadata=None):
        """
        失败响应
        
        Args:
            message: 错误消息
            code: 业务状态码
            data: 错误详情数据
            http_code: HTTP状态码
            metadata: 元数据
            
        Returns:
            Response: 统一格式的响应
        """
        return ApiResponseBuilder.fail(
            message=message, code=code, data=data, http_code=http_code, metadata=metadata
        )
    
    def paginated_response(self, items, total, page, page_size, 
                           message="查询成功", code=StatusCode.SUCCESS, metadata=None):
        """
        分页响应
        
        Args:
            items: 分页项列表
            total: 总项数
            page: 当前页码
            page_size: 每页大小
            message: 响应消息
            code: 业务状态码
            metadata: 元数据
            
        Returns:
            Response: 统一格式的响应
        """
        return ApiResponseBuilder.paginated(
            items=items, total=total, page=page, page_size=page_size,
            message=message, code=code, metadata=metadata
        )


class ApiBaseViewSet(ViewSet):
    """API视图集基类，提供统一的响应方法"""
    
    def success_response(self, data=None, message="操作成功", code=StatusCode.SUCCESS, metadata=None):
        """
        成功响应
        
        Args:
            data: 响应数据
            message: 响应消息
            code: 业务状态码
            metadata: 元数据
            
        Returns:
            Response: 统一格式的响应
        """
        return ApiResponseBuilder.success(data=data, message=message, code=code, metadata=metadata)
    
    def created_response(self, data=None, message="创建成功", code=StatusCode.CREATED, metadata=None):
        """
        创建成功响应
        
        Args:
            data: 响应数据
            message: 响应消息
            code: 业务状态码
            metadata: 元数据
            
        Returns:
            Response: 统一格式的响应
        """
        return ApiResponseBuilder.created(data=data, message=message, code=code, metadata=metadata)
    
    def failed_response(self, message="操作失败", code=StatusCode.BAD_REQUEST, 
                        data=None, http_code=status.HTTP_400_BAD_REQUEST, metadata=None):
        """
        失败响应
        
        Args:
            message: 错误消息
            code: 业务状态码
            data: 错误详情数据
            http_code: HTTP状态码
            metadata: 元数据
            
        Returns:
            Response: 统一格式的响应
        """
        return ApiResponseBuilder.fail(
            message=message, code=code, data=data, http_code=http_code, metadata=metadata
        )
    
    def paginated_response(self, items, total, page, page_size, 
                           message="查询成功", code=StatusCode.SUCCESS, metadata=None):
        """
        分页响应
        
        Args:
            items: 分页项列表
            total: 总项数
            page: 当前页码
            page_size: 每页大小
            message: 响应消息
            code: 业务状态码
            metadata: 元数据
            
        Returns:
            Response: 统一格式的响应
        """
        return ApiResponseBuilder.paginated(
            items=items, total=total, page=page, page_size=page_size,
            message=message, code=code, metadata=metadata
        ) 