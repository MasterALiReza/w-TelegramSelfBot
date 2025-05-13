"""
تست‌های واحد برای ماژول plugin_manager.py
"""
import os
import sys
import json
import yaml
import pytest
from unittest.mock import patch, mock_open, MagicMock, Mock, call

from core.plugin_manager import PluginManager, PluginInfo


class TestPluginManager:
    """تست‌های مربوط به کلاس PluginManager"""

    @pytest.fixture
    def plugin_manager(self):
        """فیکسچر برای ایجاد نمونه PluginManager"""
        # پاک کردن نمونه قبلی برای اطمینان از تست مستقل
        PluginManager._instance = None
        
        # ایجاد یک mock برای فایل‌های config و پوشه پلاگین‌ها
        with patch('os.path.exists', return_value=True), \
             patch('builtins.open', mock_open(read_data='{}')), \
             patch('yaml.safe_load', return_value={}), \
             patch('os.listdir', return_value=[]):
            manager = PluginManager()
            return manager

    def test_singleton_pattern(self, plugin_manager):
        """تست الگوی Singleton در PluginManager"""
        manager1 = plugin_manager
        manager2 = PluginManager()
        assert manager1 is manager2
        assert id(manager1) == id(manager2)

    def test_load_config(self, plugin_manager):
        """تست بارگذاری تنظیمات پلاگین‌ها"""
        # تنظیم mock برای خواندن فایل config
        sample_config = {
            'plugins': {
                'test_plugin': {
                    'enabled': True,
                    'priority': 1,
                    'settings': {'key': 'value'}
                }
            }
        }
        
        with patch('builtins.open', mock_open(read_data=json.dumps(sample_config))), \
             patch('json.load', return_value=sample_config):
            result = plugin_manager.load_config()
            
            # بررسی موفقیت‌آمیز بودن بارگذاری و تنظیم صحیح اطلاعات
            assert result is True
            assert 'test_plugin' in plugin_manager.plugin_settings
            assert plugin_manager.plugin_settings['test_plugin']['enabled'] is True
            assert plugin_manager.plugin_settings['test_plugin']['settings']['key'] == 'value'

    def test_save_config(self, plugin_manager):
        """تست ذخیره تنظیمات پلاگین‌ها"""
        # تنظیم داده‌ها برای ذخیره‌سازی
        plugin_manager.plugin_settings = {
            'test_plugin': {
                'enabled': True,
                'priority': 1,
                'settings': {'key': 'value'}
            }
        }
        
        mock_file = mock_open()
        with patch('builtins.open', mock_file), \
             patch('os.makedirs', return_value=None):
            result = plugin_manager.save_config()
            
            # بررسی فراخوانی متد write با محتوای صحیح
            assert result is True
            mock_file.return_value.write.assert_called_once()
            # بررسی اینکه داده‌های صحیح نوشته شده‌اند
            write_call = mock_file.return_value.write.call_args[0][0]
            assert 'test_plugin' in write_call
            assert 'enabled' in write_call
            assert 'true' in write_call.lower()

    @patch('os.path.isdir', return_value=True)
    @patch('os.listdir')
    @patch('pkgutil.iter_modules')
    @patch('importlib.util.find_spec')
    @patch('importlib.util.module_from_spec')
    @patch('os.path.exists', return_value=True)
    @patch('builtins.open', new_callable=mock_open)
    @patch('yaml.safe_load')
    def test_discover_plugins(self, mock_yaml_load, mock_open_file, mock_exists, 
                              mock_module_from_spec, mock_find_spec, mock_iter_modules, 
                              mock_listdir, mock_isdir, plugin_manager):
        """تست کشف پلاگین‌ها"""
        # تنظیم مقادیر برگشتی برای mockها
        mock_listdir.return_value = ['admin', 'tools']
        mock_iter_modules.return_value = [
            (None, 'plugin1', True),
            (None, 'plugin2', True)
        ]
        
        # تنظیم مقادیر برای metadata.yaml
        plugin_metadata = {
            'name': 'Test Plugin',
            'version': '1.0.0',
            'description': 'A test plugin',
            'author': 'Test Author',
            'category': 'tools',
            'commands': [
                {'name': 'test', 'description': 'A test command'}
            ]
        }
        mock_yaml_load.return_value = plugin_metadata
        
        # شبیه‌سازی ماژول پایتون و مشخصات آن
        mock_spec = MagicMock()
        mock_find_spec.return_value = mock_spec
        
        mock_module = MagicMock()
        mock_module_from_spec.return_value = mock_module
        
        # فراخوانی متد discover_plugins
        plugins = plugin_manager.discover_plugins()
        
        # بررسی‌ها
        assert len(plugins) > 0
        assert any(p.name == 'Test Plugin' for p in plugins)
        assert any(p.category == 'tools' for p in plugins)
        assert any(p.has_commands for p in plugins)

    @patch('importlib.import_module')
    def test_load_plugin(self, mock_import_module, plugin_manager):
        """تست بارگذاری پلاگین"""
        # تنظیم داده‌های پلاگین
        plugin_name = 'test_plugin'
        plugin_manager.plugins = {
            plugin_name: PluginInfo(
                name='Test Plugin',
                module_name=plugin_name,
                version='1.0.0',
                author='Test Author',
                description='A test plugin',
                category='tools',
                path='plugins/tools/test_plugin',
                commands=[{'name': 'test', 'description': 'Test command'}],
                has_commands=True,
                has_handlers=True,
                dependencies=['requests'],
                is_system=False,
                is_enabled=True,
                is_loaded=False
            )
        }
        
        # شبیه‌سازی ماژول پایتون
        mock_module = MagicMock()
        mock_module.setup = MagicMock()
        mock_import_module.return_value = mock_module
        
        # فراخوانی متد load_plugin
        result = plugin_manager.load_plugin(plugin_name)
        
        # بررسی‌ها
        assert result is True
        assert plugin_manager.plugins[plugin_name].is_loaded is True
        mock_import_module.assert_called_once_with(f'plugins.tools.{plugin_name}')
        mock_module.setup.assert_called_once()

    def test_unload_plugin(self, plugin_manager):
        """تست تخلیه پلاگین"""
        # تنظیم داده‌های پلاگین
        plugin_name = 'test_plugin'
        plugin_manager.plugins = {
            plugin_name: PluginInfo(
                name='Test Plugin',
                module_name=plugin_name,
                version='1.0.0',
                author='Test Author',
                description='A test plugin',
                category='tools',
                path='plugins/tools/test_plugin',
                commands=[{'name': 'test', 'description': 'Test command'}],
                has_commands=True,
                has_handlers=True,
                dependencies=['requests'],
                is_system=False,
                is_enabled=True,
                is_loaded=True
            )
        }
        
        # شبیه‌سازی ماژول بارگذاری شده
        mock_module = MagicMock()
        mock_module.cleanup = MagicMock()
        plugin_manager.loaded_modules = {plugin_name: mock_module}
        plugin_manager.command_handlers = {'test': lambda: None}
        
        # فراخوانی متد unload_plugin
        result = plugin_manager.unload_plugin(plugin_name)
        
        # بررسی‌ها
        assert result is True
        assert plugin_manager.plugins[plugin_name].is_loaded is False
        assert plugin_name not in plugin_manager.loaded_modules
        assert 'test' not in plugin_manager.command_handlers
        mock_module.cleanup.assert_called_once()

    def test_enable_disable_plugin(self, plugin_manager):
        """تست فعال و غیرفعال کردن پلاگین"""
        # تنظیم داده‌های پلاگین
        plugin_name = 'test_plugin'
        plugin_manager.plugins = {
            plugin_name: PluginInfo(
                name='Test Plugin',
                module_name=plugin_name,
                version='1.0.0',
                author='Test Author',
                description='A test plugin',
                category='tools',
                path='plugins/tools/test_plugin',
                commands=[],
                has_commands=False,
                has_handlers=False,
                dependencies=[],
                is_system=False,
                is_enabled=False,
                is_loaded=False
            )
        }
        
        plugin_manager.plugin_settings = {
            plugin_name: {'enabled': False}
        }
        
        # فراخوانی متد enable_plugin
        with patch.object(plugin_manager, 'save_config', return_value=True), \
             patch.object(plugin_manager, 'load_plugin', return_value=True):
            result = plugin_manager.enable_plugin(plugin_name)
            
            # بررسی‌ها
            assert result is True
            assert plugin_manager.plugins[plugin_name].is_enabled is True
            assert plugin_manager.plugin_settings[plugin_name]['enabled'] is True
            
            # فراخوانی متد disable_plugin
            result = plugin_manager.disable_plugin(plugin_name)
            
            # بررسی‌ها
            assert result is True
            assert plugin_manager.plugins[plugin_name].is_enabled is False
            assert plugin_manager.plugin_settings[plugin_name]['enabled'] is False

    def test_list_plugins(self, plugin_manager):
        """تست لیست پلاگین‌ها"""
        # تنظیم داده‌های پلاگین
        plugin_manager.plugins = {
            'plugin1': PluginInfo(
                name='Plugin One',
                module_name='plugin1',
                version='1.0.0',
                author='Author 1',
                description='Plugin one description',
                category='admin',
                path='plugins/admin/plugin1',
                commands=[],
                has_commands=False,
                has_handlers=False,
                dependencies=[],
                is_system=False,
                is_enabled=True,
                is_loaded=True
            ),
            'plugin2': PluginInfo(
                name='Plugin Two',
                module_name='plugin2',
                version='1.0.0',
                author='Author 2',
                description='Plugin two description',
                category='tools',
                path='plugins/tools/plugin2',
                commands=[],
                has_commands=False,
                has_handlers=False,
                dependencies=[],
                is_system=False,
                is_enabled=True,
                is_loaded=False
            )
        }
        
        # فراخوانی متد list_plugins بدون فیلتر
        all_plugins = plugin_manager.list_plugins()
        
        # بررسی‌ها
        assert len(all_plugins) == 2
        
        # فراخوانی متد list_plugins با فیلتر دسته‌بندی
        admin_plugins = plugin_manager.list_plugins(category='admin')
        
        # بررسی‌ها
        assert len(admin_plugins) == 1
        assert admin_plugins[0].name == 'Plugin One'
        
        # فراخوانی متد list_plugins با فیلتر دسته‌بندی دیگر
        tools_plugins = plugin_manager.list_plugins(category='tools')
        
        # بررسی‌ها
        assert len(tools_plugins) == 1
        assert tools_plugins[0].name == 'Plugin Two'

    @patch('shutil.copytree')
    @patch('os.path.exists')
    @patch('yaml.safe_load')
    def test_install_plugin(self, mock_yaml_load, mock_path_exists, mock_copytree, plugin_manager):
        """تست نصب پلاگین"""
        # تنظیم مقادیر برگشتی برای mockها
        plugin_path = '/path/to/plugin'
        metadata_path = os.path.join(plugin_path, 'metadata.yaml')
        
        # تنظیم مقادیر برای metadata.yaml
        plugin_metadata = {
            'name': 'New Plugin',
            'version': '1.0.0',
            'description': 'A new plugin',
            'author': 'New Author',
            'category': 'tools',
            'commands': []
        }
        mock_yaml_load.return_value = plugin_metadata
        
        # تنظیم mock برای path.exists
        mock_path_exists.side_effect = lambda p: p == metadata_path
        
        # فراخوانی متد install_plugin
        with patch('builtins.open', mock_open()), \
             patch.object(plugin_manager, 'scan_plugins', return_value=True), \
             patch.object(plugin_manager, 'save_config', return_value=True):
            result = plugin_manager.install_plugin(plugin_path)
            
            # بررسی‌ها
            assert result is True
            mock_copytree.assert_called_once()
            plugin_manager.scan_plugins.assert_called_once()
            plugin_manager.save_config.assert_called_once()

    @patch('shutil.rmtree')
    @patch('os.path.exists', return_value=True)
    def test_uninstall_plugin(self, mock_path_exists, mock_rmtree, plugin_manager):
        """تست حذف نصب پلاگین"""
        # تنظیم داده‌های پلاگین
        plugin_name = 'test_plugin'
        plugin_manager.plugins = {
            plugin_name: PluginInfo(
                name='Test Plugin',
                module_name=plugin_name,
                version='1.0.0',
                author='Test Author',
                description='A test plugin',
                category='tools',
                path='plugins/tools/test_plugin',
                commands=[],
                has_commands=False,
                has_handlers=False,
                dependencies=[],
                is_system=False,
                is_enabled=True,
                is_loaded=True
            )
        }
        
        # شبیه‌سازی ماژول بارگذاری شده
        mock_module = MagicMock()
        plugin_manager.loaded_modules = {plugin_name: mock_module}
        
        # فراخوانی متد uninstall_plugin
        with patch.object(plugin_manager, 'unload_plugin', return_value=True), \
             patch.object(plugin_manager, 'scan_plugins', return_value=True), \
             patch.object(plugin_manager, 'save_config', return_value=True):
            result = plugin_manager.uninstall_plugin(plugin_name)
            
            # بررسی‌ها
            assert result is True
            plugin_manager.unload_plugin.assert_called_once_with(plugin_name)
            mock_rmtree.assert_called_once()
            plugin_manager.scan_plugins.assert_called_once()
            plugin_manager.save_config.assert_called_once()
