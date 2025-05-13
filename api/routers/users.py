"""
روتر مدیریت کاربران
"""
import logging
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query, Path

from api.models.user import (
    UserCreate, UserUpdate, UserResponse, UserDetail,
    UserListResponse
)
from api.models.base import BaseResponse
from api.main import get_current_user, db_cache

router = APIRouter(prefix="/users", tags=["users"])
logger = logging.getLogger("api.users")


@router.get("/", response_model=UserListResponse)
async def list_users(
    current_user: dict = Depends(get_current_user),
    page: int = Query(1, ge=1, description="شماره صفحه"),
    limit: int = Query(10, ge=1, le=100, description="تعداد آیتم در هر صفحه"),
    search: Optional[str] = Query(None, description="جستجو براساس نام کاربری یا ایمیل")
):
    """
    دریافت لیست کاربران

    Args:
        current_user: کاربر جاری
        page: شماره صفحه
        limit: تعداد آیتم در هر صفحه
        search: متن جستجو

    Returns:
        UserListResponse: لیست کاربران
    """
    # بررسی دسترسی
    if current_user["role"] != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="شما دسترسی به این منبع را ندارید"
        )

    # محاسبه آفست
    offset = (page - 1) * limit

    # ساخت کوئری
    base_query = "FROM users"
    where_clauses = []
    params = []

    if search:
        where_clauses.append("(username ILIKE $1 OR email ILIKE $1)")
        params.append(f"%{search}%")

    if where_clauses:
        base_query += " WHERE " + " AND ".join(where_clauses)

    # کوئری شمارش
    count_query = f"SELECT COUNT(*) {base_query}"
    count_result = await db_cache.count("users", count_query, tuple(params))

    # کوئری دریافت کاربران
    query = f"""
    SELECT id, username, email, full_name, telegram_id, telegram_username, role,
           is_active, created_at, updated_at
    {base_query}
    ORDER BY id ASC
    LIMIT {limit} OFFSET {offset}
    """

    users = await db_cache.fetch_all("users", query, tuple(params))

    return {
        "success": True,
        "message": "لیست کاربران با موفقیت دریافت شد",
        "data": users,
        "total": count_result,
        "page": page,
        "limit": limit
    }


@router.get("/{user_id}", response_model=UserDetail)
async def get_user(
    user_id: int = Path(..., description="شناسه کاربر"),
    current_user: dict = Depends(get_current_user)
):
    """
    دریافت اطلاعات یک کاربر

    Args:
        user_id: شناسه کاربر
        current_user: کاربر جاری

    Returns:
        UserDetail: اطلاعات کاربر
    """
    # بررسی دسترسی
    if current_user["role"] != "admin" and current_user["id"] != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="شما دسترسی به این منبع را ندارید"
        )

    # دریافت کاربر
    query = """
    SELECT id, username, email, full_name, telegram_id, telegram_username, role,
           is_active, created_at, updated_at, last_login
    FROM users
    WHERE id = $1
    """

    user = await db_cache.fetch_one("users", query, (user_id,))

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="کاربر مورد نظر یافت نشد"
        )

    # دریافت تنظیمات کاربر
    settings_query = "SELECT settings FROM user_settings WHERE user_id = $1"
    settings_result = await db_cache.fetch_one("user_settings", settings_query, (user_id,))

    settings = settings_result["settings"] if settings_result else {}
    user["settings"] = settings

    return user


@router.post("/", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(
    user_data: UserCreate,
    current_user: dict = Depends(get_current_user)
):
    """
    ایجاد کاربر جدید

    Args:
        user_data: اطلاعات کاربر
        current_user: کاربر جاری

    Returns:
        UserResponse: اطلاعات کاربر ایجاد شده
    """
    # بررسی دسترسی
    if current_user["role"] != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="شما دسترسی به این منبع را ندارید"
        )

    # بررسی تکراری نبودن نام کاربری
    query = "SELECT id FROM users WHERE username = $1"
    existing_user = await db_cache.fetch_one("users", query, (user_data.username,))

    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="نام کاربری قبلاً استفاده شده است"
        )

    # ایجاد کاربر جدید
    insert_query = """
    INSERT INTO users (
        username, email, full_name, telegram_id, telegram_username,
        role, is_active, password_hash
    )
    VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
    RETURNING id, username, email, full_name, telegram_id, telegram_username,
              role, is_active, created_at, updated_at
    """

    params = (
        user_data.username,
        user_data.email,
        user_data.full_name,
        user_data.telegram_id,
        user_data.telegram_username,
        user_data.role,
        user_data.is_active,
        user_data.password.get_secret_value()  # در محیط واقعی از هش رمز استفاده کنید
    )

    try:
        result = await db_cache.fetch_one("users", insert_query, params)

        # ایجاد تنظیمات پیش‌فرض
        settings_query = """
        INSERT INTO user_settings (user_id, settings)
        VALUES ($1, $2)
        """

        await db_cache.execute(["user_settings"], settings_query, (result["id"], {}))

        return result
    except Exception as e:
        logger.error(f"خطا در ایجاد کاربر: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"خطا در ایجاد کاربر: {str(e)}"
        )


@router.put("/{user_id}", response_model=UserResponse)
async def update_user(
    user_data: UserUpdate,
    user_id: int = Path(..., description="شناسه کاربر"),
    current_user: dict = Depends(get_current_user)
):
    """
    به‌روزرسانی اطلاعات کاربر

    Args:
        user_data: اطلاعات به‌روزرسانی
        user_id: شناسه کاربر
        current_user: کاربر جاری

    Returns:
        UserResponse: اطلاعات کاربر به‌روزرسانی شده
    """
    # بررسی دسترسی
    if current_user["role"] != "admin" and current_user["id"] != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="شما دسترسی به این منبع را ندارید"
        )

    # بررسی وجود کاربر
    query = "SELECT id FROM users WHERE id = $1"
    existing_user = await db_cache.fetch_one("users", query, (user_id,))

    if not existing_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="کاربر مورد نظر یافت نشد"
        )

    # ساخت کوئری به‌روزرسانی
    update_fields = []
    params = []

    if user_data.username is not None:
        update_fields.append("username = $1")
        params.append(user_data.username)

    if user_data.email is not None:
        update_fields.append(f"email = ${len(params) + 1}")
        params.append(user_data.email)

    if user_data.full_name is not None:
        update_fields.append(f"full_name = ${len(params) + 1}")
        params.append(user_data.full_name)

    if user_data.telegram_username is not None:
        update_fields.append(f"telegram_username = ${len(params) + 1}")
        params.append(user_data.telegram_username)

    if user_data.role is not None:
        # فقط ادمین می‌تواند نقش را تغییر دهد
        if current_user["role"] != "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="شما دسترسی به تغییر نقش کاربر را ندارید"
            )
        update_fields.append(f"role = ${len(params) + 1}")
        params.append(user_data.role)

    if user_data.is_active is not None:
        # فقط ادمین می‌تواند وضعیت فعال بودن را تغییر دهد
        if current_user["role"] != "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="شما دسترسی به تغییر وضعیت فعال بودن کاربر را ندارید"
            )
        update_fields.append(f"is_active = ${len(params) + 1}")
        params.append(user_data.is_active)

    if user_data.password is not None:
        update_fields.append(f"password_hash = ${len(params) + 1}")
        params.append(user_data.password.get_secret_value())  # در محیط واقعی از هش رمز استفاده کنید

    if not update_fields:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="هیچ فیلدی برای به‌روزرسانی ارسال نشده است"
        )

    # افزودن شناسه کاربر به پارامترها
    params.append(user_id)

    # اجرای کوئری به‌روزرسانی
    update_query = f"""
    UPDATE users
    SET {", ".join(update_fields)}, updated_at = NOW()
    WHERE id = ${len(params)}
    RETURNING id, username, email, full_name, telegram_id, telegram_username,
              role, is_active, created_at, updated_at
    """

    try:
        result = await db_cache.fetch_one("users", update_query, tuple(params))
        return result
    except Exception as e:
        logger.error(f"خطا در به‌روزرسانی کاربر: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"خطا در به‌روزرسانی کاربر: {str(e)}"
        )


@router.delete("/{user_id}", response_model=BaseResponse)
async def delete_user(
    user_id: int = Path(..., description="شناسه کاربر"),
    current_user: dict = Depends(get_current_user)
):
    """
    حذف کاربر

    Args:
        user_id: شناسه کاربر
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

    # بررسی وجود کاربر
    query = "SELECT id FROM users WHERE id = $1"
    existing_user = await db_cache.fetch_one("users", query, (user_id,))

    if not existing_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="کاربر مورد نظر یافت نشد"
        )

    # حذف کاربر
    delete_query = "DELETE FROM users WHERE id = $1"

    try:
        await db_cache.execute(["users", "user_settings"], delete_query, (user_id,))

        return {
            "success": True,
            "message": "کاربر با موفقیت حذف شد"
        }
    except Exception as e:
        logger.error(f"خطا در حذف کاربر: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"خطا در حذف کاربر: {str(e)}"
        )
