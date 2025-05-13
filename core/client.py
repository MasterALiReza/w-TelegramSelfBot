"""
کلاس اصلی اتصال به تلگرام
پشتیبانی از Pyrogram و Telethon با قابلیت مدیریت چندین سشن
"""
import asyncio
import os
import json
from typing import Any, Dict, List, Optional, Union, Callable
import logging
from functools import wraps
from datetime import datetime

from dotenv import load_dotenv
import pyrogram
from pyrogram import Client as PyrogramClient
from pyrogram.types import Message as PyrogramMessage
from telethon import TelegramClient
from telethon.sessions import StringSession

# بارگذاری متغیرهای محیطی
load_dotenv()

# تنظیم سیستم لاگینگ
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("data/logs/telegram_client.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class ClientType:
    """
    انواع کلاینت‌های پشتیبانی شده
    """
    PYROGRAM = "pyrogram"
    TELETHON = "telethon"


class TelegramSessionManager:
    """
    مدیریت جلسات تلگرام
    """
    def __init__(self, sessions_dir: str = "data/sessions"):
        self.sessions_dir = sessions_dir
        self.active_sessions = {}
        self.ensure_sessions_dir()

    def ensure_sessions_dir(self):
        """
        اطمینان از وجود دایرکتوری جلسات
        """
        os.makedirs(self.sessions_dir, exist_ok=True)

    def get_session_path(self, phone_number: str, client_type: str) -> str:
        """
        دریافت مسیر فایل جلسه

        Args:
            phone_number: شماره تلفن
            client_type: نوع کلاینت

        Returns:
            str: مسیر فایل جلسه
        """
        file_extension = ".session" if client_type == ClientType.TELETHON else ".session"
        return os.path.join(self.sessions_dir, f"{phone_number}_{client_type}{file_extension}")

    def save_session(self, phone_number: str, client_type: str, session_string: str) -> bool:
        """
        ذخیره اطلاعات جلسه

        Args:
            phone_number: شماره تلفن
            client_type: نوع کلاینت
            session_string: رشته جلسه

        Returns:
            bool: وضعیت ذخیره‌سازی
        """
        try:
            session_file = self.get_session_path(phone_number, client_type)
            with open(session_file, 'w') as f:
                f.write(session_string)
            return True
        except Exception as e:
            logger.error(f"خطا در ذخیره جلسه: {str(e)}")
            return False

    def load_session(self, phone_number: str, client_type: str) -> Optional[str]:
        """
        بارگذاری اطلاعات جلسه

        Args:
            phone_number: شماره تلفن
            client_type: نوع کلاینت

        Returns:
            Optional[str]: رشته جلسه یا None
        """
        try:
            session_file = self.get_session_path(phone_number, client_type)
            if os.path.exists(session_file):
                with open(session_file, 'r') as f:
                    return f.read()
            return None
        except Exception as e:
            logger.error(f"خطا در بارگذاری جلسه: {str(e)}")
            return None

    def delete_session(self, phone_number: str, client_type: str) -> bool:
        """
        حذف اطلاعات جلسه

        Args:
            phone_number: شماره تلفن
            client_type: نوع کلاینت

        Returns:
            bool: وضعیت حذف
        """
        try:
            session_file = self.get_session_path(phone_number, client_type)
            if os.path.exists(session_file):
                os.remove(session_file)
            return True
        except Exception as e:
            logger.error(f"خطا در حذف جلسه: {str(e)}")
            return False

    def list_sessions(self) -> List[Dict[str, str]]:
        """
        لیست تمام جلسات ذخیره شده

        Returns:
            List[Dict[str, str]]: لیست جلسات
        """
        try:
            sessions = []
            for file in os.listdir(self.sessions_dir):
                if file.endswith(".session"):
                    parts = file.replace(".session", "").split("_")
                    if len(parts) >= 2:
                        phone = parts[0]
                        client_type = parts[1]
                        sessions.append({
                            "phone": phone,
                            "client_type": client_type,
                            "file": file
                        })
            return sessions
        except Exception as e:
            logger.error(f"خطا در لیست کردن جلسات: {str(e)}")
            return []


class TelegramClient:
    """
    کلاس اصلی برای ارتباط با تلگرام
    """
    def __init__(self, client_type: str = ClientType.PYROGRAM, session_manager: Optional[TelegramSessionManager] = None) \
        \ \
        \ \
        : \
        """
        مقداردهی اولیه

        Args:
            client_type: نوع کلاینت (pyrogram یا telethon)
            session_manager: مدیریت جلسات
        """
        self.api_id = os.getenv("TELEGRAM_API_ID")
        self.api_hash = os.getenv("TELEGRAM_API_HASH")
        self.phone_number = os.getenv("TELEGRAM_PHONE_NUMBER")
        self.client_type = client_type
        self.session_manager = session_manager or TelegramSessionManager()
        self.client = None
        self.event_handlers = {}
        self.is_connected = False

    async def connect(self) -> bool:
        """
        اتصال به تلگرام

        Returns:
            bool: وضعیت اتصال
        """
        try:
            # بررسی API ID و API Hash
            if not self.api_id or not self.api_hash:
                logger.error("API ID یا API Hash تنظیم نشده است")
                return False

            # ایجاد کلاینت مناسب
            if self.client_type == ClientType.PYROGRAM:
                session_string = self.session_manager.load_session(self.phone_number, self.client_type)
                if session_string:
                    self.client = PyrogramClient(
                        session_string,
                        api_id=self.api_id,
                        api_hash=self.api_hash,
                        in_memory=True
                    )
                else:
                    self.client = PyrogramClient(
                        self.phone_number,
                        api_id=self.api_id,
                        api_hash=self.api_hash,
                        workdir=self.session_manager.sessions_dir
                    )
            elif self.client_type == ClientType.TELETHON:
                session_string = self.session_manager.load_session(self.phone_number, self.client_type)
                if session_string:
                    self.client = TelegramClient(
                        StringSession(session_string),
                        self.api_id,
                        self.api_hash
                    )
                else:
                    session_path = self.session_manager.get_session_path(self.phone_number, self.client_type)
                    self.client = TelegramClient(
                        session_path,
                        self.api_id,
                        self.api_hash
                    )
            else:
                logger.error(f"نوع کلاینت نامعتبر: {self.client_type}")
                return False

            # اتصال به تلگرام
            await self.client.start()
            self.is_connected = True
            logger.info(f"اتصال به تلگرام با کلاینت {self.client_type} برقرار شد")

            # ذخیره اطلاعات جلسه
            if self.client_type == ClientType.PYROGRAM:
                await self.client.export_session_string()
                session_string = self.client.session_string
                self.session_manager.save_session(self.phone_number, self.client_type, session_string)
            elif self.client_type == ClientType.TELETHON:
                session_string = StringSession.save(self.client.session)
                self.session_manager.save_session(self.phone_number, self.client_type, session_string)

            return True
        except Exception as e:
            logger.error(f"خطا در اتصال به تلگرام: {str(e)}")
            return False

    async def disconnect(self) -> bool:
        """
        قطع اتصال از تلگرام

        Returns:
            bool: وضعیت قطع اتصال
        """
        try:
            if self.client:
                await self.client.stop()
                self.is_connected = False
                logger.info("اتصال از تلگرام قطع شد")
            return True
        except Exception as e:
            logger.error(f"خطا در قطع اتصال از تلگرام: {str(e)}")
            return False

    def on_message(self, filters=None):
        """
        دکوراتور برای ثبت هندلر پیام

        Args:
            filters: فیلترهای پیام

        Returns:
            Callable: دکوراتور
        """
        def decorator(func):
            @wraps(func)
            async def wrapper(client, message):
                return await func(client, message)

            # ثبت هندلر بر اساس نوع کلاینت
            if self.client_type == ClientType.PYROGRAM:
                if self.client:
                    self.client.on_message(filters)(wrapper)
            elif self.client_type == ClientType.TELETHON:
                from telethon import events
                if self.client:
                    self.client.add_event_handler(wrapper, events.NewMessage(incoming=True, outgoing=True))

            # ذخیره هندلر برای استفاده بعدی
            self.event_handlers["message"] = self.event_handlers.get("message", []) + [
                {"func": func, "filters": filters}
            ]

            return wrapper
        return decorator

    def register_handlers(self):
        """
        ثبت مجدد تمام هندلرها
        """
        # ثبت هندلرهای پیام
        for handler in self.event_handlers.get("message", []):
            if self.client_type == ClientType.PYROGRAM:
                self.client.on_message(handler["filters"])(handler["func"])
            elif self.client_type == ClientType.TELETHON:
                from telethon import events
                self.client.add_event_handler(handler["func"], events.NewMessage())

    async def send_message(self, chat_id: Union[int, str], text: str, **kwargs) -> Any:
        """
        ارسال پیام متنی

        Args:
            chat_id: شناسه چت
            text: متن پیام
            **kwargs: پارامترهای اضافی

        Returns:
            Any: پیام ارسال شده
        """
        try:
            if not self.is_connected:
                await self.connect()

            if self.client_type == ClientType.PYROGRAM:
                return await self.client.send_message(chat_id, text, **kwargs)
            elif self.client_type == ClientType.TELETHON:
                return await self.client.send_message(chat_id, text, **kwargs)
        except Exception as e:
            logger.error(f"خطا در ارسال پیام: {str(e)}")
            return None

    async def get_me(self) -> Dict[str, Any]:
        """
        دریافت اطلاعات کاربر

        Returns:
            Dict[str, Any]: اطلاعات کاربر
        """
        try:
            if not self.is_connected:
                await self.connect()

            if self.client_type == ClientType.PYROGRAM:
                me = await self.client.get_me()
                return {
                    "id": me.id,
                    "first_name": me.first_name,
                    "last_name": me.last_name,
                    "username": me.username,
                    "phone_number": me.phone_number
                }
            elif self.client_type == ClientType.TELETHON:
                me = await self.client.get_me()
                return {
                    "id": me.id,
                    "first_name": me.first_name,
                    "last_name": me.last_name,
                    "username": me.username,
                    "phone": me.phone
                }
        except Exception as e:
            logger.error(f"خطا در دریافت اطلاعات کاربر: {str(e)}")
            return {}


class TelegramClientManager:
    """
    مدیریت چندین کلاینت تلگرام
    """
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(TelegramClientManager, cls).__new__(cls)
            cls._instance.initialize()
        return cls._instance

    def initialize(self):
        """
        مقداردهی اولیه
        """
        self.clients = {}
        self.session_manager = TelegramSessionManager()

    def create_client(self, phone_number: str, client_type: str = ClientType.PYROGRAM, api_id: Optional[str] = None, api_hash: Optional[str] = None) \
        \ \
        \ \
        -> TelegramClient: \
        """
        ایجاد کلاینت جدید

        Args:
            phone_number: شماره تلفن
            client_type: نوع کلاینت
            api_id: API ID
            api_hash: API Hash

        Returns:
            TelegramClient: کلاینت تلگرام
        """
        # ساخت کلید منحصر به فرد برای این کلاینت
        client_key = f"{phone_number}_{client_type}"

        # بررسی وجود قبلی
        if client_key in self.clients:
            return self.clients[client_key]

        # ساخت کلاینت جدید
        client = TelegramClient(client_type, self.session_manager)
        client.phone_number = phone_number
        if api_id:
            client.api_id = api_id
        if api_hash:
            client.api_hash = api_hash

        # ذخیره کلاینت
        self.clients[client_key] = client
        return client

    def get_client(self, phone_number: str, client_type: str = ClientType.PYROGRAM) \
        -> Optional[TelegramClient]: \
        """
        دریافت کلاینت موجود

        Args:
            phone_number: شماره تلفن
            client_type: نوع کلاینت

        Returns:
            Optional[TelegramClient]: کلاینت تلگرام یا None
        """
        client_key = f"{phone_number}_{client_type}"
        return self.clients.get(client_key)

    def remove_client(self, phone_number: str, client_type: str = ClientType.PYROGRAM) -> bool:
        """
        حذف کلاینت

        Args:
            phone_number: شماره تلفن
            client_type: نوع کلاینت

        Returns:
            bool: وضعیت حذف
        """
        client_key = f"{phone_number}_{client_type}"
        if client_key in self.clients:
            del self.clients[client_key]
            return True
        return False

    def list_clients(self) -> List[Dict[str, str]]:
        """
        لیست تمام کلاینت‌ها

        Returns:
            List[Dict[str, str]]: لیست کلاینت‌ها
        """
        return [
            {
                "phone_number": phone_number,
                "client_type": client_type
            }
            for phone_number, client_type in [
                key.split("_") for key in self.clients.keys()
            ]
        ]

    async def disconnect_all(self) -> bool:
        """
        قطع اتصال تمام کلاینت‌ها

        Returns:
            bool: وضعیت قطع اتصال
        """
        for client in self.clients.values():
            await client.disconnect()
        return True
