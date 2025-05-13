"""
سیستم پردازش رویدادهای تلگرام با پشتیبانی از میان‌افزارها
"""
import asyncio
import inspect
import logging
from typing import Any, Callable, Dict, List, Optional, Set, Tuple, Union
from functools import wraps

from core.client import TelegramClient, ClientType

# تنظیم سیستم لاگینگ
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("data/logs/event_handler.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class EventType:
    """
    انواع رویدادهای پشتیبانی شده
    """
    MESSAGE = "message"
    EDITED_MESSAGE = "edited_message"
    CALLBACK_QUERY = "callback_query"
    INLINE_QUERY = "inline_query"
    NEW_CHAT_MEMBER = "new_chat_member"
    LEFT_CHAT_MEMBER = "left_chat_member"
    NEW_CHAT_TITLE = "new_chat_title"
    NEW_CHAT_PHOTO = "new_chat_photo"
    DELETE_CHAT_PHOTO = "delete_chat_photo"
    GROUP_CHAT_CREATED = "group_chat_created"
    RAW = "raw"  # برای رویدادهای خام


class EventFilter:
    """
    فیلترهای رویداد
    """
    @staticmethod
    def create_filter(client_type: str, **kwargs) -> Callable:
        """
        ساخت فیلتر مناسب برای نوع کلاینت

        Args:
            client_type: نوع کلاینت
            **kwargs: پارامترهای فیلتر

        Returns:
            Callable: فیلتر
        """
        if client_type == ClientType.PYROGRAM:
            from pyrogram import filters

            # ساخت فیلتر ترکیبی
            combined_filter = None

            if 'text' in kwargs:
                text_filter = filters.text & filters.regex(kwargs['text'])
                combined_filter = text_filter if combined_filter is None else combined_filter & text_filter

            if 'chat_type' in kwargs:
                chat_type = kwargs['chat_type']
                if chat_type == 'private':
                    chat_filter = filters.private
                elif chat_type == 'group':
                    chat_filter = filters.group
                elif chat_type == 'supergroup':
                    chat_filter = filters.supergroup
                elif chat_type == 'channel':
                    chat_filter = filters.channel
                else:
                    chat_filter = None

                if chat_filter:
                    combined_filter = chat_filter if combined_filter is None else combined_filter & chat_filter

            if 'user_id' in kwargs:
                user_filter = filters.user(kwargs['user_id'])
                combined_filter = user_filter if combined_filter is None else combined_filter & user_filter

            if 'chat_id' in kwargs:
                chat_filter = filters.chat(kwargs['chat_id'])
                combined_filter = chat_filter if combined_filter is None else combined_filter & chat_filter

            if 'incoming' in kwargs and kwargs['incoming']:
                combined_filter = filters.incoming if combined_filter is None else combined_filter & filters.incoming

            if 'outgoing' in kwargs and kwargs['outgoing']:
                combined_filter = filters.outgoing if combined_filter is None else combined_filter & filters.outgoing

            return combined_filter or filters.all

        elif client_type == ClientType.TELETHON:
            # برای تلتون از پارامترها برای فیلتر در زمان فراخوانی استفاده می‌کنیم
            return kwargs

        return lambda *args, **kwargs: True


class Middleware:
    """
    کلاس پایه برای میان‌افزارها
    """
    async def before_event(self, client: Any, event: Any, event_type: str) -> bool:
        """
        پردازش قبل از رویداد

        Args:
            client: کلاینت تلگرام
            event: رویداد
            event_type: نوع رویداد

        Returns:
            bool: ادامه پردازش
        """
        return True

    async def after_event(self, client: Any, event: Any, event_type: str, result: Any) -> Any:
        """
        پردازش بعد از رویداد

        Args:
            client: کلاینت تلگرام
            event: رویداد
            event_type: نوع رویداد
            result: نتیجه پردازش هندلر

        Returns:
            Any: نتیجه نهایی
        """
        return result


class EventHandler:
    """
    مدیریت رویدادهای تلگرام
    """
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(EventHandler, cls).__new__(cls)
            cls._instance.initialize()
        return cls._instance

    def initialize(self):
        """
        مقداردهی اولیه
        """
        self.handlers: Dict[str, List[Dict[str, Any]]] = {}
        self.middlewares: List[Middleware] = []
        self.telegram_client: Optional[TelegramClient] = None

    def set_client(self, client: TelegramClient):
        """
        تنظیم کلاینت تلگرام

        Args:
            client: کلاینت تلگرام
        """
        self.telegram_client = client

    def register_middleware(self, middleware: Middleware):
        """
        ثبت میان‌افزار

        Args:
            middleware: میان‌افزار
        """
        self.middlewares.append(middleware)

    def remove_middleware(self, middleware: Middleware):
        """
        حذف میان‌افزار

        Args:
            middleware: میان‌افزار
        """
        if middleware in self.middlewares:
            self.middlewares.remove(middleware)

    def register_handler(self, event_type: str, handler: Callable, filters: Optional[Dict[str, Any]] = None) \
        \ \
        \ \
        : \
        """
        ثبت هندلر برای رویداد

        Args:
            event_type: نوع رویداد
            handler: تابع پردازش
            filters: فیلترها
        """
        if event_type not in self.handlers:
            self.handlers[event_type] = []

        handler_config = {
            'handler': handler,
            'filters': filters or {}
        }

        self.handlers[event_type].append(handler_config)

        # اگر کلاینت تلگرام ست شده باشد، هندلر را به آن اضافه می‌کنیم
        if self.telegram_client:
            client_type = self.telegram_client.client_type

            if client_type == ClientType.PYROGRAM:
                if event_type == EventType.MESSAGE:
                    filter_obj = EventFilter.create_filter(client_type, **filters) \
                        if filters else None \
                    self.telegram_client.client.on_message(filter_obj) \
                        (self._create_pyrogram_wrapper(handler)) \
                elif event_type == EventType.EDITED_MESSAGE:
                    filter_obj = EventFilter.create_filter(client_type, **filters) \
                        if filters else None \
                    self.telegram_client.client.on_edited_message(filter_obj) \
                        (self._create_pyrogram_wrapper(handler)) \
                elif event_type == EventType.CALLBACK_QUERY:
                    filter_obj = EventFilter.create_filter(client_type, **filters) \
                        if filters else None \
                    self.telegram_client.client.on_callback_query(filter_obj) \
                        (self._create_pyrogram_wrapper(handler)) \
                elif event_type == EventType.INLINE_QUERY:
                    filter_obj = EventFilter.create_filter(client_type, **filters) \
                        if filters else None \
                    self.telegram_client.client.on_inline_query(filter_obj) \
                        (self._create_pyrogram_wrapper(handler)) \
                elif event_type == EventType.RAW:
                    self.telegram_client.client.on_raw_update() \
                        (self._create_pyrogram_wrapper(handler)) \

            elif client_type == ClientType.TELETHON:
                from telethon import events
                if event_type == EventType.MESSAGE:
                    self.telegram_client.client.add_event_handler(
                        self._create_telethon_wrapper(handler),
                        events.NewMessage(**filters) if filters else events.NewMessage()
                    )
                elif event_type == EventType.EDITED_MESSAGE:
                    self.telegram_client.client.add_event_handler(
                        self._create_telethon_wrapper(handler),
                        events.MessageEdited(**filters) if filters else events.MessageEdited()
                    )
                elif event_type == EventType.CALLBACK_QUERY:
                    self.telegram_client.client.add_event_handler(
                        self._create_telethon_wrapper(handler),
                        events.CallbackQuery(**filters) if filters else events.CallbackQuery()
                    )
                elif event_type == EventType.INLINE_QUERY:
                    self.telegram_client.client.add_event_handler(
                        self._create_telethon_wrapper(handler),
                        events.InlineQuery(**filters) if filters else events.InlineQuery()
                    )
                elif event_type == EventType.RAW:
                    self.telegram_client.client.add_event_handler(
                        self._create_telethon_wrapper(handler),
                        events.Raw()
                    )

    def _create_pyrogram_wrapper(self, handler: Callable) -> Callable:
        """
        ساخت wrapper برای هندلر Pyrogram

        Args:
            handler: تابع پردازش

        Returns:
            Callable: wrapper
        """
        middlewares = self.middlewares

        @wraps(handler)
        async def wrapper(client, update):
            # تعیین نوع رویداد
            event_type = EventType.MESSAGE
            if hasattr(update, 'callback_query'):
                event_type = EventType.CALLBACK_QUERY
            elif hasattr(update, 'inline_query'):
                event_type = EventType.INLINE_QUERY

            # اجرای میان‌افزارهای قبل از رویداد
            for middleware in middlewares:
                try:
                    result = await middleware.before_event(client, update, event_type)
                    if not result:
                        logger.info(f"رویداد توسط میان‌افزار {middleware.__class__.__name__} رد شد")
                        return None
                except Exception as e:
                    logger.error(f"خطا در اجرای میان‌افزار {middleware.__class__.__name__}: {str(e)}")

            # اجرای هندلر
            try:
                result = await handler(client, update)
            except Exception as e:
                logger.error(f"خطا در اجرای هندلر: {str(e)}")
                result = None

            # اجرای میان‌افزارهای بعد از رویداد
            for middleware in reversed(middlewares):
                try:
                    result = await middleware.after_event(client, update, event_type, result)
                except Exception as e:
                    logger.error(f"خطا در اجرای میان‌افزار {middleware.__class__.__name__}: {str(e)}")

            return result

        return wrapper

    def _create_telethon_wrapper(self, handler: Callable) -> Callable:
        """
        ساخت wrapper برای هندلر Telethon

        Args:
            handler: تابع پردازش

        Returns:
            Callable: wrapper
        """
        middlewares = self.middlewares

        @wraps(handler)
        async def wrapper(event):
            # تعیین نوع رویداد
            event_type = EventType.MESSAGE
            if hasattr(event, 'query'):
                event_type = EventType.CALLBACK_QUERY
            elif hasattr(event, 'query_id'):
                event_type = EventType.INLINE_QUERY

            # اجرای میان‌افزارهای قبل از رویداد
            for middleware in middlewares:
                try:
                    result = await middleware.before_event(event.client, event, event_type)
                    if not result:
                        logger.info(f"رویداد توسط میان‌افزار {middleware.__class__.__name__} رد شد")
                        return None
                except Exception as e:
                    logger.error(f"خطا در اجرای میان‌افزار {middleware.__class__.__name__}: {str(e)}")

            # اجرای هندلر
            try:
                result = await handler(event)
            except Exception as e:
                logger.error(f"خطا در اجرای هندلر: {str(e)}")
                result = None

            # اجرای میان‌افزارهای بعد از رویداد
            for middleware in reversed(middlewares):
                try:
                    result = await middleware.after_event(event.client, event, event_type, result)
                except Exception as e:
                    logger.error(f"خطا در اجرای میان‌افزار {middleware.__class__.__name__}: {str(e)}")

            return result

        return wrapper

    def on_message(self, filters: Optional[Dict[str, Any]] = None):
        """
        دکوراتور برای ثبت هندلر پیام

        Args:
            filters: فیلترها

        Returns:
            Callable: دکوراتور
        """
        def decorator(func):
            self.register_handler(EventType.MESSAGE, func, filters)
            return func
        return decorator

    def on_edited_message(self, filters: Optional[Dict[str, Any]] = None):
        """
        دکوراتور برای ثبت هندلر پیام ویرایش شده

        Args:
            filters: فیلترها

        Returns:
            Callable: دکوراتور
        """
        def decorator(func):
            self.register_handler(EventType.EDITED_MESSAGE, func, filters)
            return func
        return decorator

    def on_callback_query(self, filters: Optional[Dict[str, Any]] = None):
        """
        دکوراتور برای ثبت هندلر callback query

        Args:
            filters: فیلترها

        Returns:
            Callable: دکوراتور
        """
        def decorator(func):
            self.register_handler(EventType.CALLBACK_QUERY, func, filters)
            return func
        return decorator

    def on_inline_query(self, filters: Optional[Dict[str, Any]] = None):
        """
        دکوراتور برای ثبت هندلر inline query

        Args:
            filters: فیلترها

        Returns:
            Callable: دکوراتور
        """
        def decorator(func):
            self.register_handler(EventType.INLINE_QUERY, func, filters)
            return func
        return decorator

    def on_raw_update(self):
        """
        دکوراتور برای ثبت هندلر بروزرسانی خام

        Returns:
            Callable: دکوراتور
        """
        def decorator(func):
            self.register_handler(EventType.RAW, func)
            return func
        return decorator


# میان‌افزار‌های پیش‌فرض

class RateLimitMiddleware(Middleware):
    """
    میان‌افزار محدودیت نرخ درخواست
    """
    def __init__(self, rate_limit: int = 5, per_seconds: int = 3):
        """
        مقداردهی اولیه

        Args:
            rate_limit: تعداد درخواست
            per_seconds: در چند ثانیه
        """
        self.rate_limit = rate_limit
        self.per_seconds = per_seconds
        self.user_requests = {}

    async def before_event(self, client: Any, event: Any, event_type: str) -> bool:
        """
        پردازش قبل از رویداد

        Args:
            client: کلاینت تلگرام
            event: رویداد
            event_type: نوع رویداد

        Returns:
            bool: ادامه پردازش
        """
        # تنها برای پیام‌ها و کوئری‌ها
        if event_type not in [EventType.MESSAGE, EventType.CALLBACK_QUERY, EventType.INLINE_QUERY]:
            return True

        # دریافت شناسه کاربر
        import time
        user_id = None

        try:
            # پردازش برای پیروگرام
            if hasattr(event, 'from_user') and event.from_user:
                user_id = event.from_user.id
            # پردازش برای تلتون
            elif hasattr(event, 'sender_id'):
                user_id = event.sender_id
        except:
            return True

        if user_id:
            current_time = time.time()

            if user_id not in self.user_requests:
                self.user_requests[user_id] = []

            # پاک کردن درخواست‌های قدیمی
            self.user_requests[user_id] = [t for t in self.user_requests[user_id] if current_time - t < self.per_seconds]

            # بررسی تعداد درخواست‌ها
            if len(self.user_requests[user_id]) >= self.rate_limit:
                logger.warning(f"درخواست کاربر {user_id} به دلیل محدودیت نرخ رد شد")
                return False

            # افزودن زمان درخواست جدید
            self.user_requests[user_id].append(current_time)

        return True


class LoggingMiddleware(Middleware):
    """
    میان‌افزار ثبت وقایع
    """
    async def before_event(self, client: Any, event: Any, event_type: str) -> bool:
        """
        پردازش قبل از رویداد

        Args:
            client: کلاینت تلگرام
            event: رویداد
            event_type: نوع رویداد

        Returns:
            bool: ادامه پردازش
        """
        user_id = None
        chat_id = None

        try:
            # پردازش برای پیروگرام
            if hasattr(event, 'from_user') and event.from_user:
                user_id = event.from_user.id
            elif hasattr(event, 'sender_id'):
                user_id = event.sender_id

            if hasattr(event, 'chat') and event.chat:
                chat_id = event.chat.id
            elif hasattr(event, 'chat_id'):
                chat_id = event.chat_id
        except:
            pass

        logger.info(f"رویداد {event_type} دریافت شد - کاربر: {user_id}, چت: {chat_id}")
        return True

    async def after_event(self, client: Any, event: Any, event_type: str, result: Any) -> Any:
        """
        پردازش بعد از رویداد

        Args:
            client: کلاینت تلگرام
            event: رویداد
            event_type: نوع رویداد
            result: نتیجه پردازش هندلر

        Returns:
            Any: نتیجه نهایی
        """
        logger.info(f"رویداد {event_type} با موفقیت پردازش شد")
        return result
