"""
ماژول مدیریت استثناها و خطاهای سلف بات تلگرام
"""


class SelfBotException(Exception):
    """کلاس پایه برای تمام استثناهای سلف بات"""
    def __init__(self, message="خطای نامشخص در سلف بات"):
        self.message = message
        super().__init__(self.message)


# استثناهای مرتبط با دیتابیس
class DatabaseException(SelfBotException):
    """استثنای مرتبط با دیتابیس"""
    def __init__(self, message="خطا در عملیات دیتابیس"):
        super().__init__(message)


class DatabaseConnectionError(DatabaseException):
    """خطای اتصال به دیتابیس"""
    def __init__(self, message="خطا در اتصال به دیتابیس"):
        super().__init__(message)


class DatabaseQueryError(DatabaseException):
    """خطای اجرای کوئری دیتابیس"""
    def __init__(self, message="خطا در اجرای کوئری دیتابیس"):
        super().__init__(message)


# استثناهای مرتبط با Redis
class RedisException(SelfBotException):
    """استثنای مرتبط با Redis"""
    def __init__(self, message="خطا در عملیات Redis"):
        super().__init__(message)


class RedisConnectionError(RedisException):
    """خطای اتصال به Redis"""
    def __init__(self, message="خطا در اتصال به Redis"):
        super().__init__(message)


class RedisCacheError(RedisException):
    """خطای کش Redis"""
    def __init__(self, message="خطا در عملیات کش Redis"):
        super().__init__(message)


# استثناهای مرتبط با تلگرام
class TelegramException(SelfBotException):
    """استثنای مرتبط با تلگرام"""
    def __init__(self, message="خطا در عملیات تلگرام"):
        super().__init__(message)


class TelegramConnectionError(TelegramException):
    """خطای اتصال به تلگرام"""
    def __init__(self, message="خطا در اتصال به تلگرام"):
        super().__init__(message)


class TelegramAuthError(TelegramException):
    """خطای احراز هویت تلگرام"""
    def __init__(self, message="خطا در احراز هویت تلگرام"):
        super().__init__(message)


class TelegramLimitExceeded(TelegramException):
    """خطای تجاوز از محدودیت تلگرام"""
    def __init__(self, message="محدودیت تلگرام تجاوز شده است"):
        super().__init__(message)


# استثناهای مرتبط با API
class APIException(SelfBotException):
    """استثنای مرتبط با API"""
    def __init__(self, message="خطا در عملیات API"):
        super().__init__(message)


class APIAuthenticationError(APIException):
    """خطای احراز هویت API"""
    def __init__(self, message="خطا در احراز هویت API"):
        super().__init__(message)


class APIRateLimitError(APIException):
    """خطای محدودیت نرخ API"""
    def __init__(self, message="محدودیت نرخ API تجاوز شده است"):
        super().__init__(message)


# استثناهای مرتبط با پلاگین
class PluginException(SelfBotException):
    """استثنای مرتبط با پلاگین"""
    def __init__(self, message="خطا در عملیات پلاگین"):
        super().__init__(message)


class PluginLoadError(PluginException):
    """خطای بارگذاری پلاگین"""
    def __init__(self, message="خطا در بارگذاری پلاگین"):
        super().__init__(message)


class PluginInitError(PluginException):
    """خطای مقداردهی اولیه پلاگین"""
    def __init__(self, message="خطا در مقداردهی اولیه پلاگین"):
        super().__init__(message)


class PluginExecutionError(PluginException):
    """خطای اجرای پلاگین"""
    def __init__(self, message="خطا در اجرای پلاگین"):
        super().__init__(message)


# استثناهای مرتبط با لایسنس
class LicenseException(SelfBotException):
    """استثنای مرتبط با لایسنس"""
    def __init__(self, message="خطا در بررسی لایسنس"):
        super().__init__(message)


class LicenseInvalidError(LicenseException):
    """خطای نامعتبر بودن لایسنس"""
    def __init__(self, message="لایسنس نامعتبر است"):
        super().__init__(message)


class LicenseExpiredError(LicenseException):
    """خطای منقضی شدن لایسنس"""
    def __init__(self, message="لایسنس منقضی شده است"):
        super().__init__(message)


# استثناهای مرتبط با هوش مصنوعی
class AIException(SelfBotException):
    """استثنای مرتبط با هوش مصنوعی"""
    def __init__(self, message="خطا در عملیات هوش مصنوعی"):
        super().__init__(message)


class AIConnectionError(AIException):
    """خطای اتصال به سرویس هوش مصنوعی"""
    def __init__(self, message="خطا در اتصال به سرویس هوش مصنوعی"):
        super().__init__(message)


class AIQuotaExceededError(AIException):
    """خطای تجاوز از سهمیه هوش مصنوعی"""
    def __init__(self, message="سهمیه هوش مصنوعی تجاوز شده است"):
        super().__init__(message)
