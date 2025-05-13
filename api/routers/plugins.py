"""
روتر مدیریت پلاگین‌ها
"""
import logging
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query, Path

from api.models.plugin import (
    PluginCreate, PluginUpdate, PluginResponse, PluginDetail,
    PluginListResponse, PluginToggleRequest
)
from api.models.base import BaseResponse
from api.main import get_current_user, db_cache

router = APIRouter(prefix="/plugins", tags=["plugins"])
logger = logging.getLogger("api.plugins")


@router.get("/", response_model=PluginListResponse)
async def list_plugins(
    current_user: dict = Depends(get_current_user),
    page: int = Query(1, ge=1, description="شماره صفحه"),
    limit: int = Query(10, ge=1, le=100, description="تعداد آیتم در هر صفحه"),
    plugin_type: Optional[str] = Query(None, description="فیلتر براساس نوع پلاگین"),
    status: Optional[str] = Query(None, description="فیلتر براساس وضعیت پلاگین"),
    search: Optional[str] = Query(None, description="جستجو براساس نام یا توضیحات")
):
    """
    دریافت لیست پلاگین‌ها

    Args:
        current_user: کاربر جاری
        page: شماره صفحه
        limit: تعداد آیتم در هر صفحه
        plugin_type: نوع پلاگین
        status: وضعیت پلاگین
        search: متن جستجو

    Returns:
        PluginListResponse: لیست پلاگین‌ها
    """
    # محاسبه آفست
    offset = (page - 1) * limit

    # ساخت کوئری
    base_query = "FROM plugins"
    where_clauses = []
    params = []
    param_count = 1

    if search:
        where_clauses.append(f"(name ILIKE ${param_count} OR display_name ILIKE ${param_count} OR description ILIKE ${param_count})")
        params.append(f"%{search}%")
        param_count += 1

    if plugin_type:
        where_clauses.append(f"type = ${param_count}")
        params.append(plugin_type)
        param_count += 1

    if status:
        where_clauses.append(f"status = ${param_count}")
        params.append(status)
        param_count += 1

    if where_clauses:
        base_query += " WHERE " + " AND ".join(where_clauses)

    # کوئری شمارش
    count_query = f"SELECT COUNT(*) {base_query}"
    count_result = await db_cache.count("plugins", count_query, tuple(params))

    # کوئری دریافت پلاگین‌ها
    query = f"""
    SELECT id, name, display_name, description, version, author, type, status,
           config, module_path, dependencies, requires_restart, created_at, updated_at
    {base_query}
    ORDER BY name ASC
    LIMIT {limit} OFFSET {offset}
    """

    plugins = await db_cache.fetch_all("plugins", query, tuple(params))

    return {
        "success": True,
        "message": "لیست پلاگین‌ها با موفقیت دریافت شد",
        "data": plugins,
        "total": count_result,
        "page": page,
        "limit": limit
    }


@router.get("/{plugin_id}", response_model=PluginDetail)
async def get_plugin(
    plugin_id: int = Path(..., description="شناسه پلاگین"),
    current_user: dict = Depends(get_current_user)
):
    """
    دریافت اطلاعات یک پلاگین

    Args:
        plugin_id: شناسه پلاگین
        current_user: کاربر جاری

    Returns:
        PluginDetail: اطلاعات پلاگین
    """
    # دریافت پلاگین
    query = """
    SELECT id, name, display_name, description, version, author, type, status,
           config, module_path, dependencies, requires_restart, created_at, updated_at
    FROM plugins
    WHERE id = $1
    """

    plugin = await db_cache.fetch_one("plugins", query, (plugin_id,))

    if not plugin:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="پلاگین مورد نظر یافت نشد"
        )

    # دریافت فرمان‌های پلاگین
    commands_query = "SELECT command_name, description, usage, is_admin FROM plugin_commands WHERE plugin_id = $1"
    commands = await db_cache.fetch_all("plugin_commands", commands_query, (plugin_id,))

    # تبدیل به فرمت مناسب
    plugin["commands"] = commands if commands else []

    # دریافت ایونت‌های پلاگین
    events_query = "SELECT event_name FROM plugin_events WHERE plugin_id = $1"
    events_result = await db_cache.fetch_all("plugin_events", events_query, (plugin_id,))

    # استخراج نام ایونت‌ها
    events = [event["event_name"] for event in events_result] if events_result else []
    plugin["events"] = events

    # دریافت آخرین خطا
    error_query = "SELECT error_message FROM plugin_errors WHERE plugin_id = $1 ORDER BY created_at DESC LIMIT 1"
    error_result = await db_cache.fetch_one("plugin_errors", error_query, (plugin_id,))

    plugin["last_error"] = error_result["error_message"] if error_result else None

    return plugin


@router.post("/", response_model=PluginResponse, status_code=status.HTTP_201_CREATED)
async def create_plugin(
    plugin_data: PluginCreate,
    current_user: dict = Depends(get_current_user)
):
    """
    ایجاد پلاگین جدید

    Args:
        plugin_data: اطلاعات پلاگین
        current_user: کاربر جاری

    Returns:
        PluginResponse: اطلاعات پلاگین ایجاد شده
    """
    # بررسی دسترسی
    if current_user["role"] != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="شما دسترسی به این منبع را ندارید"
        )

    # بررسی تکراری نبودن نام پلاگین
    query = "SELECT id FROM plugins WHERE name = $1"
    existing_plugin = await db_cache.fetch_one("plugins", query, (plugin_data.name,))

    if existing_plugin:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="نام پلاگین قبلاً استفاده شده است"
        )

    # ایجاد پلاگین جدید
    insert_query = """
    INSERT INTO plugins (
        name, display_name, description, version, author, type, status,
        config, module_path, dependencies, requires_restart
    )
    VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
    RETURNING id, name, display_name, description, version, author, type, status,
              config, module_path, dependencies, requires_restart, created_at, updated_at
    """

    params = (
        plugin_data.name,
        plugin_data.display_name,
        plugin_data.description,
        plugin_data.version,
        plugin_data.author,
        plugin_data.type,
        plugin_data.status,
        plugin_data.config,
        plugin_data.module_path,
        plugin_data.dependencies,
        plugin_data.requires_restart
    )

    try:
        result = await db_cache.fetch_one("plugins", insert_query, params)
        return result
    except Exception as e:
        logger.error(f"خطا در ایجاد پلاگین: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"خطا در ایجاد پلاگین: {str(e)}"
        )


@router.put("/{plugin_id}", response_model=PluginResponse)
async def update_plugin(
    plugin_data: PluginUpdate,
    plugin_id: int = Path(..., description="شناسه پلاگین"),
    current_user: dict = Depends(get_current_user)
):
    """
    به‌روزرسانی اطلاعات پلاگین

    Args:
        plugin_data: اطلاعات به‌روزرسانی
        plugin_id: شناسه پلاگین
        current_user: کاربر جاری

    Returns:
        PluginResponse: اطلاعات پلاگین به‌روزرسانی شده
    """
    # بررسی دسترسی
    if current_user["role"] != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="شما دسترسی به این منبع را ندارید"
        )

    # بررسی وجود پلاگین
    query = "SELECT id FROM plugins WHERE id = $1"
    existing_plugin = await db_cache.fetch_one("plugins", query, (plugin_id,))

    if not existing_plugin:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="پلاگین مورد نظر یافت نشد"
        )

    # ساخت کوئری به‌روزرسانی
    update_fields = []
    params = []
    param_count = 1

    if plugin_data.display_name is not None:
        update_fields.append(f"display_name = ${param_count}")
        params.append(plugin_data.display_name)
        param_count += 1

    if plugin_data.description is not None:
        update_fields.append(f"description = ${param_count}")
        params.append(plugin_data.description)
        param_count += 1

    if plugin_data.version is not None:
        update_fields.append(f"version = ${param_count}")
        params.append(plugin_data.version)
        param_count += 1

    if plugin_data.author is not None:
        update_fields.append(f"author = ${param_count}")
        params.append(plugin_data.author)
        param_count += 1

    if plugin_data.type is not None:
        update_fields.append(f"type = ${param_count}")
        params.append(plugin_data.type)
        param_count += 1

    if plugin_data.status is not None:
        update_fields.append(f"status = ${param_count}")
        params.append(plugin_data.status)
        param_count += 1

    if plugin_data.config is not None:
        update_fields.append(f"config = ${param_count}")
        params.append(plugin_data.config)
        param_count += 1

    if plugin_data.module_path is not None:
        update_fields.append(f"module_path = ${param_count}")
        params.append(plugin_data.module_path)
        param_count += 1

    if plugin_data.dependencies is not None:
        update_fields.append(f"dependencies = ${param_count}")
        params.append(plugin_data.dependencies)
        param_count += 1

    if plugin_data.requires_restart is not None:
        update_fields.append(f"requires_restart = ${param_count}")
        params.append(plugin_data.requires_restart)
        param_count += 1

    if not update_fields:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="هیچ فیلدی برای به‌روزرسانی ارسال نشده است"
        )

    # افزودن شناسه پلاگین به پارامترها
    params.append(plugin_id)

    # اجرای کوئری به‌روزرسانی
    update_query = f"""
    UPDATE plugins
    SET {", ".join(update_fields)}, updated_at = NOW()
    WHERE id = ${param_count}
    RETURNING id, name, display_name, description, version, author, type, status,
              config, module_path, dependencies, requires_restart, created_at, updated_at
    """

    try:
        result = await db_cache.fetch_one("plugins", update_query, tuple(params))
        return result
    except Exception as e:
        logger.error(f"خطا در به‌روزرسانی پلاگین: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"خطا در به‌روزرسانی پلاگین: {str(e)}"
        )


@router.patch("/{plugin_id}/toggle", response_model=PluginResponse)
async def toggle_plugin(
    toggle_data: PluginToggleRequest,
    plugin_id: int = Path(..., description="شناسه پلاگین"),
    current_user: dict = Depends(get_current_user)
):
    """
    تغییر وضعیت پلاگین (فعال/غیرفعال)

    Args:
        toggle_data: داده‌های تغییر وضعیت
        plugin_id: شناسه پلاگین
        current_user: کاربر جاری

    Returns:
        PluginResponse: اطلاعات پلاگین به‌روزرسانی شده
    """
    # بررسی دسترسی
    if current_user["role"] != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="شما دسترسی به این منبع را ندارید"
        )

    # بررسی وجود پلاگین
    query = "SELECT id FROM plugins WHERE id = $1"
    existing_plugin = await db_cache.fetch_one("plugins", query, (plugin_id,))

    if not existing_plugin:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="پلاگین مورد نظر یافت نشد"
        )

    # اجرای کوئری به‌روزرسانی
    update_query = """
    UPDATE plugins
    SET status = $1, updated_at = NOW()
    WHERE id = $2
    RETURNING id, name, display_name, description, version, author, type, status,
              config, module_path, dependencies, requires_restart, created_at, updated_at
    """

    try:
        result = await db_cache.fetch_one("plugins", update_query, (toggle_data.status, plugin_id))
        return result
    except Exception as e:
        logger.error(f"خطا در تغییر وضعیت پلاگین: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"خطا در تغییر وضعیت پلاگین: {str(e)}"
        )


@router.delete("/{plugin_id}", response_model=BaseResponse)
async def delete_plugin(
    plugin_id: int = Path(..., description="شناسه پلاگین"),
    current_user: dict = Depends(get_current_user)
):
    """
    حذف پلاگین

    Args:
        plugin_id: شناسه پلاگین
        current_user: کاربر جاری

    Returns:
        BaseResponse: پاسخ
    """
    # بررسی دسترسی
    if current_user["role"] != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="شما دسترسی به این منبع را ندارید"
        )

    # بررسی وجود پلاگین
    query = "SELECT id, name FROM plugins WHERE id = $1"
    existing_plugin = await db_cache.fetch_one("plugins", query, (plugin_id,))

    if not existing_plugin:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="پلاگین مورد نظر یافت نشد"
        )

    plugin_name = existing_plugin["name"]

    # بررسی پلاگین‌های هسته
    if existing_plugin.get("type") == "core":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="پلاگین‌های هسته قابل حذف نیستند"
        )

    # حذف پلاگین
    delete_query = "DELETE FROM plugins WHERE id = $1"

    try:
        await db_cache.execute(["plugins", "plugin_commands", "plugin_events", "plugin_errors"], delete_query, (plugin_id,))

        return {
            "success": True,
            "message": f"پلاگین '{plugin_name}' با موفقیت حذف شد"
        }
    except Exception as e:
        logger.error(f"خطا در حذف پلاگین: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"خطا در حذف پلاگین: {str(e)}"
        )
