import React, { useEffect, useState } from 'react'
import axios from 'axios'
import { useToast } from '../../hooks/use-toast'
import { PluginManager } from '../../components/plugins/PluginManager'

interface ApiPlugin {
  id: number
  name: string
  version: string
  description: string
  author: string
  category: string
  is_enabled: boolean
  config: string
}

interface PluginData {
  id: string
  name: string
  version: string
  description: string
  author: string
  isActive: boolean
  settings?: Record<string, any>
}

const PluginsPage: React.FC = () => {
  const [plugins, setPlugins] = useState<PluginData[]>([])
  const [loading, setLoading] = useState<boolean>(true)
  const { toast } = useToast()

  useEffect(() => {
    fetchPlugins()
  }, [])

  // دریافت لیست پلاگین‌ها از API
  const fetchPlugins = async () => {
    try {
      setLoading(true)
      const { data } = await axios.get<ApiPlugin[]>('/api/plugins')
      // تبدیل فرمت داده‌های API به فرمت مورد نیاز کامپوننت
      const formattedPlugins = data.map(plugin => ({
        id: plugin.id.toString(),
        name: plugin.name,
        version: plugin.version,
        description: plugin.description,
        author: plugin.author,
        isActive: plugin.is_enabled,
        settings: plugin.config ? JSON.parse(plugin.config) : undefined
      }));
      setPlugins(formattedPlugins)
    } catch (error) {
      toast({
        title: 'خطا',
        description: 'خطا در بارگذاری پلاگین‌ها',
        variant: 'destructive'
      })
    } finally {
      setLoading(false)
    }
  }

  // فعال/غیرفعال کردن پلاگین
  const handleTogglePlugin = async (id: string, isActive: boolean) => {
    try {
      await axios.patch(`/api/plugins/${id}`, {
        is_enabled: isActive
      })
      
      setPlugins(plugins.map(plugin => 
        plugin.id === id ? { ...plugin, isActive } : plugin
      ))
      
      toast({
        title: 'موفق',
        description: `پلاگین با موفقیت ${isActive ? 'فعال' : 'غیرفعال'} شد`,
        variant: 'default'
      })
    } catch (error) {
      toast({
        title: 'خطا',
        description: 'خطا در تغییر وضعیت پلاگین',
        variant: 'destructive'
      })
    }
  }

  // نصب پلاگین جدید
  const handleInstallPlugin = async (url: string) => {
    try {
      await axios.post('/api/plugins/install', { url })
      toast({
        title: 'موفق',
        description: 'پلاگین با موفقیت نصب شد',
        variant: 'default'
      })
      fetchPlugins() // بارگذاری مجدد لیست پلاگین‌ها
    } catch (error) {
      toast({
        title: 'خطا',
        description: 'خطا در نصب پلاگین',
        variant: 'destructive'
      })
    }
    return Promise.resolve();
  }

  // حذف پلاگین
  const handleUninstallPlugin = async (id: string) => {
    try {
      await axios.delete(`/api/plugins/${id}`)
      setPlugins(plugins.filter(plugin => plugin.id !== id))
      toast({
        title: 'موفق',
        description: 'پلاگین با موفقیت حذف شد',
        variant: 'default'
      })
    } catch (error) {
      toast({
        title: 'خطا',
        description: 'خطا در حذف پلاگین',
        variant: 'destructive'
      })
    }
    return Promise.resolve();
  }

  // ذخیره تنظیمات پلاگین
  const handleSaveSettings = async (id: string, settings: Record<string, any>) => {
    try {
      await axios.patch(`/api/plugins/${id}/settings`, { config: JSON.stringify(settings) })
      toast({
        title: 'موفق',
        description: 'تنظیمات با موفقیت ذخیره شد',
        variant: 'default'
      })
    } catch (error) {
      toast({
        title: 'خطا',
        description: 'خطا در ذخیره تنظیمات',
        variant: 'destructive'
      })
    }
    return Promise.resolve();
  }

  return (
    <div>
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-2xl font-bold tracking-tight">مدیریت پلاگین‌ها</h1>
        <button
          onClick={() => fetchPlugins()}
          className="text-sm underline text-muted-foreground"
          disabled={loading}
        >
          بارگذاری مجدد
        </button>
      </div>

      <PluginManager 
        plugins={plugins}
        loading={loading}
        onTogglePlugin={handleTogglePlugin}
        onInstallPlugin={handleInstallPlugin}
        onUninstallPlugin={handleUninstallPlugin}
        onSaveSettings={handleSaveSettings}
      />
    </div>
  )
}

export default PluginsPage
