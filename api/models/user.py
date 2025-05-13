"""
مدل‌های کاربر برای API
"""
from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field, validator, EmailStr, SecretStr
from enum import Enum

from api.models.base import BaseResponse


class UserRole(str, Enum):
    """نقش‌های کاربر"""
    ADMIN = "admin"
    USER = "user"
    GUEST = "guest"


class UserBase(BaseModel):
    """مدل پایه کاربر"""
    username: str = Field(..., min_length=3, max_length=50)
    email: Optional[EmailStr] = None
    full_name: Optional[str] = Field(None, max_length=100)
    telegram_id: Optional[int] = None
    telegram_username: Optional[str] = Field(None, max_length=50)
    role: UserRole = UserRole.USER
    is_active: bool = True


class UserCreate(UserBase):
    """مدل ایجاد کاربر"""
    password: SecretStr = Field(..., min_length=8)
    confirm_password: SecretStr = Field(..., min_length=8)

    @validator('confirm_password')
    def passwords_match(cls, v, values, **kwargs):
        if 'password' in values and v.get_secret_value() != values['password'].get_secret_value():
            raise ValueError('رمزهای عبور مطابقت ندارند')
        return v


class UserUpdate(BaseModel):
    """مدل به‌روزرسانی کاربر"""
    username: Optional[str] = Field(None, min_length=3, max_length=50)
    email: Optional[EmailStr] = None
    full_name: Optional[str] = Field(None, max_length=100)
    telegram_username: Optional[str] = Field(None, max_length=50)
    role: Optional[UserRole] = None
    is_active: Optional[bool] = None
    password: Optional[SecretStr] = Field(None, min_length=8)


class UserResponse(UserBase):
    """مدل پاسخ کاربر"""
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        orm_mode = True


class UserDetail(UserResponse):
    """مدل جزئیات کاربر"""
    last_login: Optional[datetime] = None
    settings: Optional[Dict[str, Any]] = None

    class Config:
        orm_mode = True


class UserLogin(BaseModel):
    """مدل ورود کاربر"""
    username: str
    password: SecretStr


class UserLoginResponse(BaseResponse):
    """مدل پاسخ ورود کاربر"""
    access_token: str
    token_type: str = "bearer"
    user: UserResponse


class UserListResponse(BaseResponse):
    """مدل پاسخ لیست کاربران"""
    data: List[UserResponse]
    total: int
    page: int
    limit: int
