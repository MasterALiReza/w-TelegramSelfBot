import React, { useState } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '../ui/card'
import { Switch } from '../ui/switch'
import { Button } from '../ui/button'
import { Input } from '../ui/input'
import { Label } from '../ui/label'

interface Plugin {
  id: string
  name: string
  description: string
  version: string
  author: string
  isActive: boolean
  settings?: Record<string, any>
}

interface PluginManagerProps {
  plugins: Plugin[]
  onTogglePlugin: (id: string, isActive: boolean) => Promise<void>
  onInstallPlugin: (url: string) => Promise<void>
  onUninstallPlugin: (id: string) => Promise<void>
  onSaveSettings: (id: string, settings: Record<string, any>) => Promise<void>
  loading?: boolean
}

export const PluginManager: React.FC<PluginManagerProps> = ({
  plugins,
  onTogglePlugin,
  onInstallPlugin,
  onUninstallPlugin,
  onSaveSettings,
  loading = false
}: PluginManagerProps) => {
  const [newPluginUrl, setNewPluginUrl] = useState('')
  const [installLoading, setInstallLoading] = useState(false)
  const [activeTab, setActiveTab] = useState<string | null>(null)
  const [pluginSettings, setPluginSettings] = useState<Record<string, any>>({})
  
  // نصب پلاگین جدید
  const handleInstall = async () => {
    if (!newPluginUrl.trim()) return
    
    try {
      setInstallLoading(true)
      await onInstallPlugin(newPluginUrl)
      setNewPluginUrl('')
    } catch (error) {
      console.error('Error installing plugin:', error)
    } finally {
      setInstallLoading(false)
    }
  }
  
  // فعال/غیرفعال کردن پلاگین
  const handleToggle = async (id: string, isActive: boolean) => {
    try {
      await onTogglePlugin(id, isActive)
    } catch (error) {
      console.error('Error toggling plugin:', error)
    }
  }
  
  // حذف پلاگین
  const handleUninstall = async (id: string) => {
    if (window.confirm('آیا از حذف این پلاگین اطمینان دارید؟')) {
      try {
        await onUninstallPlugin(id)
      } catch (error) {
        console.error('Error uninstalling plugin:', error)
      }
    }
  }
  
  // باز کردن تنظیمات پلاگین
  const handleOpenSettings = (plugin: Plugin) => {
    setActiveTab(plugin.id)
    setPluginSettings(plugin.settings || {})
  }
  
  // ذخیره تنظیمات پلاگین
  const handleSaveSettings = async (id: string) => {
    try {
      await onSaveSettings(id, pluginSettings)
      setActiveTab(null)
    } catch (error) {
      console.error('Error saving plugin settings:', error)
    }
  }
  
  return (
    <div className="space-y-4">
      {/* فرم نصب پلاگین جدید */}
      <Card>
        <CardHeader>
          <CardTitle>نصب پلاگین جدید</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex gap-2">
            <div className="flex-grow">
              <Input
                placeholder="آدرس گیت یا فایل پلاگین"
                value={newPluginUrl}
                onChange={(e) => setNewPluginUrl(e.target.value)}
              />
            </div>
            <Button onClick={handleInstall} disabled={installLoading || !newPluginUrl.trim()}>
              {installLoading ? 'در حال نصب...' : 'نصب'}
            </Button>
          </div>
        </CardContent>
      </Card>
      
      {/* لیست پلاگین‌ها */}
      <div className="grid gap-4 grid-cols-1 md:grid-cols-2 lg:grid-cols-3">
        {loading ? (
          Array.from({ length: 3 }).map((_, i) => (
            <Card key={i} className="h-60 animate-pulse bg-muted" />
          ))
        ) : plugins.length === 0 ? (
          <Card className="col-span-full p-6">
            <div className="text-center text-muted-foreground">
              هیچ پلاگینی نصب نشده است
            </div>
          </Card>
        ) : (
          plugins.map((plugin) => (
            <Card key={plugin.id} className={activeTab === plugin.id ? 'border-primary' : ''}>
              <CardHeader className="pb-2">
                <div className="flex justify-between items-center">
                  <CardTitle className="text-lg">{plugin.name}</CardTitle>
                  <Switch
                    checked={plugin.isActive}
                    onCheckedChange={(checked) => handleToggle(plugin.id, checked)}
                  />
                </div>
                <div className="text-xs text-muted-foreground">نسخه {plugin.version}</div>
              </CardHeader>
              <CardContent className="space-y-2">
                <p className="text-sm">{plugin.description}</p>
                <div className="text-xs text-muted-foreground">
                  نویسنده: {plugin.author}
                </div>
                <div className="flex justify-between pt-2">
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => handleOpenSettings(plugin)}
                    disabled={!plugin.settings}
                  >
                    تنظیمات
                  </Button>
                  <Button
                    variant="destructive"
                    size="sm"
                    onClick={() => handleUninstall(plugin.id)}
                  >
                    حذف
                  </Button>
                </div>
              </CardContent>
            </Card>
          ))
        )}
      </div>
      
      {/* مودال تنظیمات */}
      {activeTab && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <Card className="w-full max-w-lg">
            <CardHeader>
              <CardTitle>
                تنظیمات {plugins.find(p => p.id === activeTab)?.name}
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              {plugins.find(p => p.id === activeTab)?.settings && 
                Object.entries(plugins.find(p => p.id === activeTab)?.settings || {}).map(([key]) => (
                  <div key={key} className="space-y-2">
                    <Label htmlFor={key}>{key}</Label>
                    <Input
                      id={key}
                      value={pluginSettings[key] || ''}
                      onChange={(e) => 
                        setPluginSettings({
                          ...pluginSettings,
                          [key]: e.target.value
                        })
                      }
                    />
                  </div>
                ))
              }
              <div className="flex justify-end gap-2 pt-4">
                <Button variant="outline" onClick={() => setActiveTab(null)}>
                  انصراف
                </Button>
                <Button onClick={() => handleSaveSettings(activeTab)}>
                  ذخیره
                </Button>
              </div>
            </CardContent>
          </Card>
        </div>
      )}
    </div>
  )
}
