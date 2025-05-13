"""
سیستم مدیریت پلاگین با قابلیت نصب، حذف و مدیریت پلاگین‌ها در زمان اجرا
"""
import os
import sys
import importlib
import importlib.util
import logging
import json
import yaml
from typing import Any, Dict, List, Optional, Callable
from dataclasses import dataclass, field, asdict

# تنظیم سیستم لاگینگ
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("data/logs/plugin_manager.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


@dataclass
class PluginInfo:
    """
    اطلاعات یک پلاگین
    """
    name: str
    version: str
    description: str = ""
    author: str = ""
    requires: List[str] = field(default_factory=list)
    category: str = "general"
    is_enabled: bool = True
    path: str = ""
    module_name: str = ""
    config: Dict[str, Any] = field(default_factory=dict)
    commands: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """
        تبدیل به دیکشنری

        Returns:
            Dict[str, Any]: دیکشنری
        """
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'PluginInfo':
        """
        ساخت از دیکشنری

        Args:
            data: دیکشنری

        Returns:
            PluginInfo: شیء اطلاعات پلاگین
        """
        return cls(**data)


class PluginManager:
    """
    مدیریت پلاگین‌ها
    """
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(PluginManager, cls).__new__(cls)
            cls._instance.initialize()
        return cls._instance

    def initialize(self):
        """
        مقداردهی اولیه
        """
        self.plugins: Dict[str, PluginInfo] = {}
        self.loaded_modules: Dict[str, Any] = {}
        self.commands: Dict[str, Dict[str, Any]] = {}
        self.config_file = "config/plugins.yml"
        self.plugin_dirs = [
            "plugins/admin",
            "plugins/fun",
            "plugins/security",
            "plugins/tools",
            "plugins/ai",
            "plugins/analytics",
            "plugins/integration",
            "plugins/utils",
        ]
        self.load_config()

    def load_config(self) -> bool:
        """
        بارگذاری تنظیمات پلاگین‌ها

        Returns:
            bool: وضعیت بارگذاری
        """
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    config = yaml.safe_load(f)
                    if config and 'plugins' in config:
                        for plugin_data in config['plugins']:
                            plugin_info = PluginInfo.from_dict(plugin_data)
                            self.plugins[plugin_info.name] = plugin_info
                logger.info(f"{len(self.plugins)} پلاگین از تنظیمات بارگذاری شد")
            return True
        except Exception as e:
            logger.error(f"خطا در بارگذاری تنظیمات پلاگین‌ها: {str(e)}")
            return False

    def save_config(self) -> bool:
        """
        ذخیره تنظیمات پلاگین‌ها

        Returns:
            bool: وضعیت ذخیره‌سازی
        """
        try:
            os.makedirs(os.path.dirname(self.config_file), exist_ok=True)
            config = {
                'plugins': [plugin.to_dict() for plugin in self.plugins.values()]
            }
            with open(self.config_file, 'w', encoding='utf-8') as f:
                yaml.dump(config, f, default_flow_style=False, allow_unicode=True)
            logger.info(f"{len(self.plugins)} پلاگین در تنظیمات ذخیره شد")
            return True
        except Exception as e:
            logger.error(f"خطا در ذخیره تنظیمات پلاگین‌ها: {str(e)}")
            return False

    def discover_plugins(self) -> List[PluginInfo]:
        """
        کشف پلاگین‌های موجود

        Returns:
            List[PluginInfo]: لیست پلاگین‌ها
        """
        discovered_plugins = []

        for plugin_dir in self.plugin_dirs:
            if not os.path.exists(plugin_dir):
                continue

            for item in os.listdir(plugin_dir):
                plugin_path = os.path.join(plugin_dir, item)

                # فقط پوشه‌ها که حاوی __init__.py هستند بررسی شوند
                if (os.path.isdir(plugin_path) and
                    os.path.exists(os.path.join(plugin_path, "__init__.py"))):
                    try:
                        # استخراج اطلاعات از فایل plugin_info.json یا plugin_info.yml
                        info_json = os.path.join(plugin_path, "plugin_info.json")
                        info_yaml = os.path.join(plugin_path, "plugin_info.yml")

                        plugin_info = None

                        if os.path.exists(info_json):
                            with open(info_json, 'r', encoding='utf-8') as f:
                                info = json.load(f)
                                plugin_info = PluginInfo.from_dict(info)
                        elif os.path.exists(info_yaml):
                            with open(info_yaml, 'r', encoding='utf-8') as f:
                                info = yaml.safe_load(f)
                                plugin_info = PluginInfo.from_dict(info)

                        if plugin_info:
                            # مسیر و نام ماژول
                            plugin_info.path = plugin_path
                            plugin_info.module_name = f"{plugin_dir.replace('/', '.')}.{item}"

                            # کسب اطلاعات وضعیت از تنظیمات فعلی
                            if plugin_info.name in self.plugins:
                                plugin_info.is_enabled = self.plugins[plugin_info.name].is_enabled
                                plugin_info.config = self.plugins[plugin_info.name].config

                            discovered_plugins.append(plugin_info)
                    except Exception as e:
                        logger.error(f"خطا در کشف پلاگین {plugin_path}: {str(e)}")

        return discovered_plugins

    def scan_plugins(self) -> bool:
        """
        اسکن و بروزرسانی لیست پلاگین‌ها

        Returns:
            bool: وضعیت اسکن
        """
        try:
            discovered = self.discover_plugins()

            # بروزرسانی لیست پلاگین‌ها
            for plugin in discovered:
                self.plugins[plugin.name] = plugin

            # ذخیره تنظیمات بروز شده
            self.save_config()

            logger.info(f"{len(discovered)} پلاگین کشف شد")
            return True
        except Exception as e:
            logger.error(f"خطا در اسکن پلاگین‌ها: {str(e)}")
            return False

    def load_plugin(self, plugin_name: str) -> bool:
        """
        بارگذاری یک پلاگین

        Args:
            plugin_name: نام پلاگین

        Returns:
            bool: وضعیت بارگذاری
        """
        try:
            if plugin_name not in self.plugins:
                logger.error(f"پلاگین {plugin_name} یافت نشد")
                return False

            plugin = self.plugins[plugin_name]

            # بررسی وضعیت فعال بودن
            if not plugin.is_enabled:
                logger.info(f"پلاگین {plugin_name} غیرفعال است")
                return False

            # بررسی وابستگی‌ها
            for dependency in plugin.requires:
                if dependency not in self.plugins or not self.plugins[dependency].is_enabled:
                    logger.error(f"وابستگی {dependency} برای پلاگین {plugin_name} یافت نشد یا فعال نیست")
                    return False

            # بارگذاری ماژول
            if plugin.module_name not in self.loaded_modules:
                spec = importlib.util.find_spec(plugin.module_name)
                if spec is None:
                    logger.error(f"ماژول {plugin.module_name} یافت نشد")
                    return False

                module = importlib.util.module_from_spec(spec)
                sys.modules[plugin.module_name] = module
                spec.loader.exec_module(module)
                self.loaded_modules[plugin.module_name] = module

                # بررسی تابع initialize
                if hasattr(module, 'initialize'):
                    module.initialize(plugin.config)

                # ثبت دستورات
                if hasattr(module, 'commands'):
                    for command in module.commands:
                        cmd_name = command['name']
                        self.commands[cmd_name] = {
                            'plugin': plugin_name,
                            'handler': command['handler'],
                            'description': command.get('description', ''),
                            'usage': command.get('usage', ''),
                            'category': plugin.category
                        }
                        # افزودن دستور به اطلاعات پلاگین
                        plugin.commands.append({
                            'name': cmd_name,
                            'description': command.get('description', ''),
                            'usage': command.get('usage', '')
                        })

                logger.info(f"پلاگین {plugin_name} با موفقیت بارگذاری شد")
                return True
            else:
                logger.info(f"پلاگین {plugin_name} قبلاً بارگذاری شده است")
                return True
        except Exception as e:
            logger.error(f"خطا در بارگذاری پلاگین {plugin_name}: {str(e)}")
            return False

    def unload_plugin(self, plugin_name: str) -> bool:
        """
        تخلیه یک پلاگین

        Args:
            plugin_name: نام پلاگین

        Returns:
            bool: وضعیت تخلیه
        """
        try:
            if plugin_name not in self.plugins:
                logger.error(f"پلاگین {plugin_name} یافت نشد")
                return False

            plugin = self.plugins[plugin_name]

            # حذف دستورات مربوط به این پلاگین
            commands_to_remove = []
            for cmd_name, cmd_info in self.commands.items():
                if cmd_info['plugin'] == plugin_name:
                    commands_to_remove.append(cmd_name)

            for cmd_name in commands_to_remove:
                del self.commands[cmd_name]

            # حذف ماژول از لیست بارگذاری شده
            if plugin.module_name in self.loaded_modules:
                # اجرای تابع cleanup اگر وجود داشته باشد
                module = self.loaded_modules[plugin.module_name]
                if hasattr(module, 'cleanup'):
                    module.cleanup()

                # حذف از sys.modules
                if plugin.module_name in sys.modules:
                    del sys.modules[plugin.module_name]

                # حذف از لیست بارگذاری شده
                del self.loaded_modules[plugin.module_name]

            # پاک کردن لیست دستورات پلاگین
            plugin.commands = []

            logger.info(f"پلاگین {plugin_name} با موفقیت تخلیه شد")
            return True
        except Exception as e:
            logger.error(f"خطا در تخلیه پلاگین {plugin_name}: {str(e)}")
            return False

    def reload_plugin(self, plugin_name: str) -> bool:
        """
        بارگذاری مجدد یک پلاگین

        Args:
            plugin_name: نام پلاگین

        Returns:
            bool: وضعیت بارگذاری مجدد
        """
        if self.unload_plugin(plugin_name):
            return self.load_plugin(plugin_name)
        return False

    def enable_plugin(self, plugin_name: str) -> bool:
        """
        فعال کردن یک پلاگین

        Args:
            plugin_name: نام پلاگین

        Returns:
            bool: وضعیت فعال‌سازی
        """
        if plugin_name not in self.plugins:
            logger.error(f"پلاگین {plugin_name} یافت نشد")
            return False

        self.plugins[plugin_name].is_enabled = True
        self.save_config()

        return self.load_plugin(plugin_name)

    def disable_plugin(self, plugin_name: str) -> bool:
        """
        غیرفعال کردن یک پلاگین

        Args:
            plugin_name: نام پلاگین

        Returns:
            bool: وضعیت غیرفعال‌سازی
        """
        if plugin_name not in self.plugins:
            logger.error(f"پلاگین {plugin_name} یافت نشد")
            return False

        self.plugins[plugin_name].is_enabled = False
        self.save_config()

        return self.unload_plugin(plugin_name)

    def get_plugin_info(self, plugin_name: str) -> Optional[PluginInfo]:
        """
        دریافت اطلاعات یک پلاگین

        Args:
            plugin_name: نام پلاگین

        Returns:
            Optional[PluginInfo]: اطلاعات پلاگین یا None
        """
        return self.plugins.get(plugin_name)

    def list_plugins(self, category: Optional[str] = None) -> List[PluginInfo]:
        """
        لیست پلاگین‌ها

        Args:
            category: دسته‌بندی

        Returns:
            List[PluginInfo]: لیست پلاگین‌ها
        """
        if category:
            return [p for p in self.plugins.values() if p.category == category]
        return list(self.plugins.values())

    def load_all_plugins(self) -> bool:
        """
        بارگذاری تمام پلاگین‌های فعال

        Returns:
            bool: وضعیت بارگذاری
        """
        success = True
        for plugin_name, plugin in self.plugins.items():
            if plugin.is_enabled and not self.load_plugin(plugin_name):
                success = False
        return success

    def get_command_handler(self, command_name: str) -> Optional[Callable]:
        """
        دریافت هندلر یک دستور

        Args:
            command_name: نام دستور

        Returns:
            Optional[Callable]: هندلر دستور یا None
        """
        if command_name in self.commands:
            return self.commands[command_name]['handler']
        return None

    def list_commands(self, category: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        لیست دستورات

        Args:
            category: دسته‌بندی

        Returns:
            List[Dict[str, Any]]: لیست دستورات
        """
        commands = []
        for cmd_name, cmd_info in self.commands.items():
            if category is None or cmd_info['category'] == category:
                commands.append({
                    'name': cmd_name,
                    'plugin': cmd_info['plugin'],
                    'description': cmd_info['description'],
                    'usage': cmd_info['usage'],
                    'category': cmd_info['category']
                })
        return commands

    def install_plugin(self, plugin_path: str) -> bool:
        """
        نصب پلاگین از مسیر

        Args:
            plugin_path: مسیر پلاگین

        Returns:
            bool: وضعیت نصب
        """
        try:
            # بررسی وجود فایل plugin_info
            info_json = os.path.join(plugin_path, "plugin_info.json")
            info_yaml = os.path.join(plugin_path, "plugin_info.yml")

            plugin_info = None

            if os.path.exists(info_json):
                with open(info_json, 'r', encoding='utf-8') as f:
                    info = json.load(f)
                    plugin_info = PluginInfo.from_dict(info)
            elif os.path.exists(info_yaml):
                with open(info_yaml, 'r', encoding='utf-8') as f:
                    info = yaml.safe_load(f)
                    plugin_info = PluginInfo.from_dict(info)

            if not plugin_info:
                logger.error(f"اطلاعات پلاگین در مسیر {plugin_path} یافت نشد")
                return False

            # تعیین مسیر نصب
            install_dir = os.path.join("plugins", plugin_info.category, plugin_info.name)

            # ایجاد دایرکتوری نصب
            os.makedirs(os.path.dirname(install_dir), exist_ok=True)

            # کپی فایل‌ها
            import shutil
            if os.path.exists(install_dir):
                shutil.rmtree(install_dir)
            shutil.copytree(plugin_path, install_dir)

            # اسکن مجدد پلاگین‌ها
            self.scan_plugins()

            logger.info(f"پلاگین {plugin_info.name} با موفقیت نصب شد")
            return True
        except Exception as e:
            logger.error(f"خطا در نصب پلاگین: {str(e)}")
            return False

    def uninstall_plugin(self, plugin_name: str) -> bool:
        """
        حذف نصب پلاگین

        Args:
            plugin_name: نام پلاگین

        Returns:
            bool: وضعیت حذف نصب
        """
        try:
            if plugin_name not in self.plugins:
                logger.error(f"پلاگین {plugin_name} یافت نشد")
                return False

            plugin = self.plugins[plugin_name]

            # تخلیه پلاگین
            self.unload_plugin(plugin_name)

            # حذف دایرکتوری پلاگین
            import shutil
            if os.path.exists(plugin.path) and os.path.isdir(plugin.path):
                shutil.rmtree(plugin.path)

            # حذف از لیست پلاگین‌ها
            if plugin_name in self.plugins:
                del self.plugins[plugin_name]

            # ذخیره تنظیمات
            self.save_config()

            logger.info(f"پلاگین {plugin_name} با موفقیت حذف نصب شد")
            return True
        except Exception as e:
            logger.error(f"خطا در حذف نصب پلاگین {plugin_name}: {str(e)}")
            return False
