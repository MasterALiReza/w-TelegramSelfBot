"""
مدل‌های پلاگین برای API
"""
from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field
from enum import Enum

from api.models.base import BaseResponse


class PluginStatus(str, Enum):
    """وضعیت پلاگین"""
    ACTIVE = "active"
    INACTIVE = "inactive"
    ERROR = "error"


class PluginType(str, Enum):
    """نوع پلاگین"""
    CORE = "core"
    SECURITY = "security"
    TOOLS = "tools"
    AI = "ai"
    ANALYTICS = "analytics"
    INTEGRATION = "integration"
    OTHER = "other"


class PluginBase(BaseModel):
    """مدل پایه پلاگین"""
    name: str = Field(..., min_length=2, max_length=50)
    display_name: str = Field(..., max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    version: str = Field(..., max_length=20)
    author: Optional[str] = Field(None, max_length=100)
    type: PluginType = PluginType.OTHER
    status: PluginStatus = PluginStatus.INACTIVE
    config: Optional[Dict[str, Any]] = None


class PluginCreate(PluginBase):
    """مدل ایجاد پلاگین"""
    module_path: str = Field(..., max_length=200)
    dependencies: Optional[List[str]] = None
    requires_restart: bool = False


class PluginUpdate(BaseModel):
    """مدل به‌روزرسانی پلاگین"""
    display_name: Optional[str] = Field(None, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    version: Optional[str] = Field(None, max_length=20)
    author: Optional[str] = Field(None, max_length=100)
    type: Optional[PluginType] = None
    status: Optional[PluginStatus] = None
    config: Optional[Dict[str, Any]] = None
    module_path: Optional[str] = Field(None, max_length=200)
    dependencies: Optional[List[str]] = None
    requires_restart: Optional[bool] = None


class PluginResponse(PluginBase):
    """مدل پاسخ پلاگین"""
    id: int
    module_path: str
    dependencies: Optional[List[str]] = None
    requires_restart: bool = False
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        orm_mode = True


class PluginDetail(PluginResponse):
    """مدل جزئیات پلاگین"""
    commands: Optional[List[Dict[str, Any]]] = None
    events: Optional[List[str]] = None
    last_error: Optional[str] = None

    class Config:
        orm_mode = True


class PluginListResponse(BaseResponse):
    """مدل پاسخ لیست پلاگین‌ها"""
    data: List[PluginResponse]
    total: int
    page: int
    limit: int


class PluginToggleRequest(BaseModel):
    """مدل درخواست تغییر وضعیت پلاگین"""
    status: PluginStatus
