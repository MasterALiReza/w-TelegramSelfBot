"""
سیستم چندزبانگی و بومی‌سازی (i18n, l10n) برای پشتیبانی از زبان‌های مختلف
"""
import os
import json
import logging
import re
from typing import Any, Dict, List, Optional, Set, Union
import gettext
from pathlib import Path

# تنظیم سیستم لاگینگ
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("data/logs/localization.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class TranslationProvider:
    """
    کلاس پایه برای ارائه‌دهندگان ترجمه
    """
    def get_translation(self, key: str, lang: str, default: Optional[str] = None) -> str:
        """
        دریافت ترجمه

        Args:
            key: کلید ترجمه
            lang: کد زبان
            default: متن پیش‌فرض

        Returns:
            str: متن ترجمه شده
        """
        raise NotImplementedError()


class JSONTranslationProvider(TranslationProvider):
    """
    ارائه‌دهنده ترجمه بر اساس فایل‌های JSON
    """
    def __init__(self, locales_dir: str = "locales"):
        """
        مقداردهی اولیه

        Args:
            locales_dir: مسیر پوشه زبان‌ها
        """
        self.locales_dir = locales_dir
        self.translations: Dict[str, Dict[str, str]] = {}
        self.load_translations()

    def load_translations(self):
        """
        بارگذاری فایل‌های ترجمه
        """
        try:
            if not os.path.exists(self.locales_dir):
                os.makedirs(self.locales_dir, exist_ok=True)
                return

            # بارگذاری فایل‌های JSON
            for lang_file in os.listdir(self.locales_dir):
                if lang_file.endswith('.json'):
                    lang_code = lang_file.replace('.json', '')
                    file_path = os.path.join(self.locales_dir, lang_file)

                    with open(file_path, 'r', encoding='utf-8') as f:
                        self.translations[lang_code] = json.load(f)

            logger.info(f"{len(self.translations)} فایل ترجمه بارگذاری شد")
        except Exception as e:
            logger.error(f"خطا در بارگذاری فایل‌های ترجمه: {str(e)}")

    def save_translation(self, lang: str):
        """
        ذخیره فایل ترجمه

        Args:
            lang: کد زبان
        """
        try:
            if lang not in self.translations:
                return

            file_path = os.path.join(self.locales_dir, f"{lang}.json")

            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(self.translations[lang], f, ensure_ascii=False, indent=2)

            logger.info(f"فایل ترجمه {lang} ذخیره شد")
        except Exception as e:
            logger.error(f"خطا در ذخیره فایل ترجمه {lang}: {str(e)}")

    def get_translation(self, key: str, lang: str, default: Optional[str] = None) -> str:
        """
        دریافت ترجمه

        Args:
            key: کلید ترجمه
            lang: کد زبان
            default: متن پیش‌فرض

        Returns:
            str: متن ترجمه شده
        """
        if lang not in self.translations:
            return default or key

        return self.translations[lang].get(key, default or key)

    def add_translation(self, key: str, lang: str, value: str):
        """
        افزودن ترجمه جدید

        Args:
            key: کلید ترجمه
            lang: کد زبان
            value: متن ترجمه
        """
        if lang not in self.translations:
            self.translations[lang] = {}

        self.translations[lang][key] = value
        self.save_translation(lang)

    def remove_translation(self, key: str, lang: str) -> bool:
        """
        حذف ترجمه

        Args:
            key: کلید ترجمه
            lang: کد زبان

        Returns:
            bool: وضعیت حذف
        """
        if lang not in self.translations or key not in self.translations[lang]:
            return False

        del self.translations[lang][key]
        self.save_translation(lang)
        return True


class GettextTranslationProvider(TranslationProvider):
    """
    ارائه‌دهنده ترجمه بر اساس Gettext
    """
    def __init__(self, locales_dir: str = "locales", domain: str = "messages"):
        """
        مقداردهی اولیه

        Args:
            locales_dir: مسیر پوشه زبان‌ها
            domain: دامنه ترجمه
        """
        self.locales_dir = locales_dir
        self.domain = domain
        self.translations: Dict[str, gettext.NullTranslations] = {}
        self.load_translations()

    def load_translations(self):
        """
        بارگذاری فایل‌های ترجمه
        """
        try:
            if not os.path.exists(self.locales_dir):
                os.makedirs(self.locales_dir, exist_ok=True)
                return

            # بارگذاری فایل‌های MO
            for lang_dir in os.listdir(self.locales_dir):
                lc_dir = os.path.join(self.locales_dir, lang_dir, 'LC_MESSAGES')
                if os.path.isdir(lc_dir):
                    mo_path = os.path.join(lc_dir, f"{self.domain}.mo")
                    if os.path.exists(mo_path):
                        self.translations[lang_dir] = gettext.translation(
                            self.domain,
                            self.locales_dir,
                            languages=[lang_dir]
                        )

            logger.info(f"{len(self.translations)} فایل ترجمه Gettext بارگذاری شد")
        except Exception as e:
            logger.error(f"خطا در بارگذاری فایل‌های ترجمه Gettext: {str(e)}")

    def get_translation(self, key: str, lang: str, default: Optional[str] = None) -> str:
        """
        دریافت ترجمه

        Args:
            key: کلید ترجمه
            lang: کد زبان
            default: متن پیش‌فرض

        Returns:
            str: متن ترجمه شده
        """
        if lang not in self.translations:
            return default or key

        return self.translations[lang].gettext(key) or default or key


class Localization:
    """
    مدیریت چندزبانگی
    """
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(Localization, cls).__new__(cls)
            cls._instance.initialize()
        return cls._instance

    def initialize(self):
        """
        مقداردهی اولیه
        """
        self.default_lang = "en"
        self.current_lang = self.default_lang
        self.available_langs: Dict[str, str] = {
            "en": "English",
            "fa": "فارسی",
            "ar": "العربية",
            "ru": "Русский"
        }

        # ارائه‌دهندگان ترجمه
        self.providers: List[TranslationProvider] = [
            JSONTranslationProvider(),
            GettextTranslationProvider()
        ]

        # ایجاد فایل‌های زبان پیش‌فرض
        self._create_default_lang_files()

    def _create_default_lang_files(self):
        """
        ایجاد فایل‌های زبان پیش‌فرض
        """
        try:
            locales_dir = "locales"
            os.makedirs(locales_dir, exist_ok=True)

            # ایجاد فایل زبان انگلیسی
            en_file = os.path.join(locales_dir, "en.json")
            if not os.path.exists(en_file):
                default_translations = {
                    "hello": "Hello",
                    "welcome": "Welcome to Telegram SelfBot",
                    "help": "Help",
                    "settings": "Settings",
                    "language": "Language",
                    "success": "Success",
                    "error": "Error",
                    "confirm": "Confirm",
                    "cancel": "Cancel",
                    "save": "Save",
                    "delete": "Delete",
                    "edit": "Edit",
                    "add": "Add",
                    "remove": "Remove",
                    "search": "Search",
                    "not_found": "Not found",
                    "loading": "Loading...",
                    "please_wait": "Please wait..."
                }

                with open(en_file, 'w', encoding='utf-8') as f:
                    json.dump(default_translations, f, ensure_ascii=False, indent=2)

            # ایجاد فایل زبان فارسی
            fa_file = os.path.join(locales_dir, "fa.json")
            if not os.path.exists(fa_file):
                default_translations = {
                    "hello": "سلام",
                    "welcome": "به سلف بات تلگرام خوش آمدید",
                    "help": "راهنما",
                    "settings": "تنظیمات",
                    "language": "زبان",
                    "success": "موفقیت",
                    "error": "خطا",
                    "confirm": "تایید",
                    "cancel": "لغو",
                    "save": "ذخیره",
                    "delete": "حذف",
                    "edit": "ویرایش",
                    "add": "افزودن",
                    "remove": "حذف",
                    "search": "جستجو",
                    "not_found": "یافت نشد",
                    "loading": "در حال بارگذاری...",
                    "please_wait": "لطفا صبر کنید..."
                }

                with open(fa_file, 'w', encoding='utf-8') as f:
                    json.dump(default_translations, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"خطا در ایجاد فایل‌های زبان پیش‌فرض: {str(e)}")

    def set_language(self, lang: str):
        """
        تنظیم زبان فعلی

        Args:
            lang: کد زبان
        """
        if lang in self.available_langs:
            self.current_lang = lang
            logger.info(f"زبان به {lang} تغییر کرد")
        else:
            logger.warning(f"زبان {lang} پشتیبانی نمی‌شود، از زبان پیش‌فرض استفاده می‌شود")

    def get_text(self, key: str, lang: Optional[str] = None, default: Optional[str] = None) -> str:
        """
        دریافت متن ترجمه شده

        Args:
            key: کلید ترجمه
            lang: کد زبان (اختیاری)
            default: متن پیش‌فرض

        Returns:
            str: متن ترجمه شده
        """
        lang = lang or self.current_lang

        # بررسی تمام ارائه‌دهندگان
        for provider in self.providers:
            translation = provider.get_translation(key, lang, None)
            if translation and translation != key:
                return translation

        # اگر ترجمه پیدا نشد و زبان فعلی انگلیسی نیست، تلاش برای دریافت ترجمه انگلیسی
        if lang != self.default_lang:
            for provider in self.providers:
                translation = provider.get_translation(key, self.default_lang, None)
                if translation and translation != key:
                    return translation

        # اگر هیچ ترجمه‌ای پیدا نشد، برگرداندن مقدار پیش‌فرض یا خود کلید
        return default or key

    def format_text(self, key: str, lang: Optional[str] = None, default: Optional[str] = None, **kwargs) \
        \ \
        \ \
        -> str: \
        """
        دریافت و قالب‌بندی متن ترجمه شده

        Args:
            key: کلید ترجمه
            lang: کد زبان (اختیاری)
            default: متن پیش‌فرض
            **kwargs: پارامترهای قالب‌بندی

        Returns:
            str: متن ترجمه و قالب‌بندی شده
        """
        text = self.get_text(key, lang, default)

        # قالب‌بندی با پارامترها
        if kwargs:
            try:
                return text.format(**kwargs)
            except KeyError as e:
                logger.warning(f"خطا در قالب‌بندی متن {key}: {str(e)}")
                return text

        return text

    def add_translation(self, key: str, value: str, lang: str):
        """
        افزودن ترجمه جدید

        Args:
            key: کلید ترجمه
            value: متن ترجمه
            lang: کد زبان
        """
        # فقط از ارائه‌دهنده JSON استفاده می‌کنیم
        for provider in self.providers:
            if isinstance(provider, JSONTranslationProvider):
                provider.add_translation(key, lang, value)
                logger.info(f"ترجمه {key} به زبان {lang} افزوده شد")
                break

    def remove_translation(self, key: str, lang: str) -> bool:
        """
        حذف ترجمه

        Args:
            key: کلید ترجمه
            lang: کد زبان

        Returns:
            bool: وضعیت حذف
        """
        result = False

        # فقط از ارائه‌دهنده JSON استفاده می‌کنیم
        for provider in self.providers:
            if isinstance(provider, JSONTranslationProvider):
                result = provider.remove_translation(key, lang)
                if result:
                    logger.info(f"ترجمه {key} از زبان {lang} حذف شد")
                break

        return result

    def get_all_translations(self, lang: str) -> Dict[str, str]:
        """
        دریافت تمام ترجمه‌های یک زبان

        Args:
            lang: کد زبان

        Returns:
            Dict[str, str]: ترجمه‌ها
        """
        result = {}

        # فقط از ارائه‌دهنده JSON استفاده می‌کنیم
        for provider in self.providers:
            if isinstance(provider, JSONTranslationProvider):
                if lang in provider.translations:
                    result = provider.translations[lang]
                break

        return result

    def detect_language(self, text: str) -> str:
        """
        تشخیص زبان متن
        توجه: این پیاده‌سازی ساده است و برای تشخیص دقیق باید از کتابخانه‌های تخصصی استفاده شود

        Args:
            text: متن

        Returns:
            str: کد زبان
        """
        # بررسی الگوهای ساده زبان

        # زبان فارسی (حروف فارسی)
        if re.search(r'[\u0600-\u06FF]', text):
            return "fa"

        # زبان عربی (حروف عربی خاص)
        if re.search(r'[\u0621-\u064A]', text):
            return "ar"

        # زبان روسی (حروف سیریلیک)
        if re.search(r'[\u0400-\u04FF]', text):
            return "ru"

        # پیش‌فرض: انگلیسی
        return "en"


# پیاده‌سازی تابع کمکی جهانی
def _(key: str, **kwargs) -> str:
    """
    تابع کمکی برای دسترسی سریع به ترجمه‌ها

    Args:
        key: کلید ترجمه
        **kwargs: پارامترهای قالب‌بندی

    Returns:
        str: متن ترجمه شده
    """
    localization = Localization()
    return localization.format_text(key, **kwargs)
