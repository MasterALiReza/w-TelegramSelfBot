"""
مدل‌های پایه برای API
"""
from typing import Optional, List, Dict, Any, Generic, TypeVar
from pydantic import BaseModel, Field
from pydantic.generics import GenericModel


class BaseResponse(BaseModel):
    """مدل پایه برای پاسخ‌های API"""
    success: bool = True
    message: Optional[str] = None


class PaginationParams(BaseModel):
    """پارامترهای صفحه‌بندی"""
    page: int = Field(1, ge=1, description="شماره صفحه")
    limit: int = Field(10, ge=1, le=100, description="تعداد آیتم در هر صفحه")


class PaginationMeta(BaseModel):
    """متادیتای صفحه‌بندی"""
    page: int
    limit: int
    total: int
    total_pages: int
    has_next: bool
    has_prev: bool


T = TypeVar('T')


class PaginatedResponse(GenericModel, Generic[T]):
    """پاسخ صفحه‌بندی شده"""
    success: bool = True
    message: Optional[str] = None
    data: List[T]
    meta: PaginationMeta


class ErrorResponse(BaseModel):
    """مدل پاسخ خطا"""
    success: bool = False
    message: str
    error_code: Optional[str] = None
    details: Optional[Dict[str, Any]] = None


class Token(BaseModel):
    """مدل توکن دسترسی"""
    access_token: str
    token_type: str


class TokenData(BaseModel):
    """مدل داده‌های توکن"""
    user_id: Optional[int] = None
