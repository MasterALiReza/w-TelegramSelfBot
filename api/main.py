"""
ماژول اصلی API سلف بات تلگرام
"""
import os
import logging
from typing import Dict, Any, Optional

from fastapi import FastAPI, Depends, HTTPException, status, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
import jwt
from datetime import datetime, timedelta

from core.config import Config
from core.database import Database
from core.redis_manager import initialize_redis
from core.database_cache import DatabaseCache

# تنظیم لاگر
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
)
logger = logging.getLogger("api")

# ایجاد نمونه FastAPI
app = FastAPI(
    title="Telegram SelfBot API",
    description="API مدیریت سلف بات تلگرام",
    version="1.0.0",
)

# اضافه کردن CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # در محیط تولید باید محدود شود
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# تعریف متغیرهای سراسری
config = None
db = None
redis = None
db_cache = None


@app.on_event("startup")
async def startup_event():
    """
    ایونت راه‌اندازی سرور
    """
    global config, db, redis, db_cache

    try:
        # بارگذاری تنظیمات
        logger.info("در حال بارگذاری تنظیمات...")
        config = Config()

        # اتصال به دیتابیس
        logger.info("در حال اتصال به دیتابیس...")
        db = Database(
            host=config.get("DB_HOST"),
            user=config.get("DB_USER"),
            password=config.get("DB_PASSWORD"),
            database=config.get("DB_NAME"),
            port=config.get("DB_PORT", 5432),
        )
        await db.connect()

        # اتصال به Redis
        logger.info("در حال اتصال به Redis...")
        redis = await initialize_redis(
            host=config.get("REDIS_HOST", "localhost"),
            port=config.get("REDIS_PORT", 6379),
            db=config.get("REDIS_DB", 0),
            password=config.get("REDIS_PASSWORD"),
            prefix=config.get("REDIS_PREFIX", "selfbot:")
        )

        # ایجاد مدیریت کش دیتابیس
        db_cache = DatabaseCache(db, redis)

        logger.info("سرور API با موفقیت راه‌اندازی شد.")
    except Exception as e:
        logger.error(f"خطا در راه‌اندازی سرور API: {str(e)}")
        raise


@app.on_event("shutdown")
async def shutdown_event():
    """
    ایونت خاموش کردن سرور
    """
    global db, redis

    try:
        # قطع اتصال از دیتابیس
        if db:
            logger.info("در حال قطع اتصال از دیتابیس...")
            await db.disconnect()

        # قطع اتصال از Redis
        if redis:
            logger.info("در حال قطع اتصال از Redis...")
            await redis.disconnect()

        logger.info("سرور API با موفقیت خاموش شد.")
    except Exception as e:
        logger.error(f"خطا در خاموش کردن سرور API: {str(e)}")


# ----- احراز هویت ----- #

# ساخت OAuth2
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# کلید رمزنگاری JWT
SECRET_KEY = os.environ.get("JWT_SECRET_KEY", "supersecretkey")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 24 ساعت


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """
    ایجاد توکن دسترسی

    Args:
        data: داده‌های کاربر
        expires_delta: زمان انقضا

    Returns:
        str: توکن دسترسی
    """
    to_encode = data.copy()

    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


async def get_current_user(token: str = Depends(oauth2_scheme)):
    """
    دریافت کاربر جاری

    Args:
        token: توکن دسترسی

    Returns:
        dict: اطلاعات کاربر

    Raises:
        HTTPException: در صورت نامعتبر بودن توکن
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="توکن نامعتبر است",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        # رمزگشایی توکن
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")

        if user_id is None:
            raise credentials_exception

        # دریافت اطلاعات کاربر از دیتابیس
        query = "SELECT * FROM users WHERE id = $1"
        user = await db_cache.fetch_one("users", query, (user_id,))

        if user is None:
            raise credentials_exception

        return user
    except jwt.PyJWTError:
        raise credentials_exception


@app.post("/token", response_model=Dict[str, str])
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()):
    """
    دریافت توکن دسترسی

    Args:
        form_data: فرم ورود کاربر

    Returns:
        Dict[str, str]: توکن دسترسی

    Raises:
        HTTPException: در صورت نامعتبر بودن نام کاربری یا رمز عبور
    """
    # بررسی اعتبار نام کاربری و رمز عبور
    query = "SELECT * FROM users WHERE username = $1"
    user = await db_cache.fetch_one("users", query, (form_data.username,))

    if not user or user["password_hash"] != form_data.password:  # در محیط واقعی از هش رمز استفاده کنید
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="نام کاربری یا رمز عبور نادرست است",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # ایجاد توکن دسترسی
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": str(user["id"])},
        expires_delta=access_token_expires
    )

    return {"access_token": access_token, "token_type": "bearer"}


# ----- ثبت روترها ----- #

from api.routers import users, plugins

app.include_router(users.router)
app.include_router(plugins.router)

# ----- مسیرهای عمومی ----- #

@app.get("/")
async def root():
    """
    مسیر اصلی

    Returns:
        Dict[str, str]: پیام خوش‌آمدگویی
    """
    return {"message": "به API سلف بات تلگرام خوش آمدید!"}


@app.get("/status")
async def status():
    """
    وضعیت سرور

    Returns:
        Dict[str, Any]: وضعیت سرور
    """
    return {
        "status": "online",
        "timestamp": datetime.utcnow().isoformat(),
        "database": "connected" if db else "disconnected",
        "redis": "connected" if redis else "disconnected",
    }


# ----- مسیرهای نیازمند احراز هویت ----- #

@app.get("/me", response_model=Dict[str, Any])
async def read_users_me(current_user: dict = Depends(get_current_user)):
    """
    دریافت اطلاعات کاربر جاری

    Args:
        current_user: کاربر جاری

    Returns:
        Dict[str, Any]: اطلاعات کاربر
    """
    return current_user


# ----- مدیریت خطا ----- #

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """
    مدیریت خطاهای سراسری

    Args:
        request: درخواست
        exc: خطا

    Returns:
        JSONResponse: پاسخ خطا
    """
    logger.error(f"خطای سراسری: {str(exc)}")
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"message": "خطای سراسری رخ داد", "detail": str(exc)},
    )
