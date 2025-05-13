import React, { useEffect, useState } from 'react'
import axios from 'axios'
import { Card, CardContent, CardHeader, CardTitle } from '../../components/ui/card'
import { Input } from '../../components/ui/input'
import { Label } from '../../components/ui/label'
import { Switch } from '../../components/ui/switch'
import { Button } from '../../components/ui/button'
import { useToast } from '../../hooks/use-toast'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../../components/ui/tabs'

interface Setting {
  key: string
  value: string
  description: string
}

interface SettingsCategory {
  name: string
  settings: Setting[]
}

const SettingsPage: React.FC = () => {
  const [categories, setCategories] = useState<SettingsCategory[]>([])
  const [loading, setLoading] = useState<boolean>(true)
  const [saving, setSaving] = useState<boolean>(false)
  const { toast } = useToast()

  useEffect(() => {
    fetchSettings()
  }, [])

  const fetchSettings = async () => {
    try {
      setLoading(true)
      const { data } = await axios.get<Setting[]>('/api/settings')
      
      // گروه‌بندی تنظیمات بر اساس پیشوند کلید
      const grouped: Record<string, Setting[]> = {}
      
      data.forEach(setting => {
        const keyParts = setting.key.split('_')
        const category = keyParts[0] // استفاده از اولین بخش کلید به عنوان دسته‌بندی
        
        if (!grouped[category]) {
          grouped[category] = []
        }
        
        grouped[category].push(setting)
      })
      
      // تبدیل به فرمت مورد نیاز برای رندرینگ
      const categoryList: SettingsCategory[] = Object.entries(grouped).map(([name, settings]) => ({
        name,
        settings
      }))
      
      setCategories(categoryList)
    } catch (error) {
      toast({
        title: 'خطا',
        description: 'خطا در بارگذاری تنظیمات',
        variant: 'destructive'
      })
    } finally {
      setLoading(false)
    }
  }

  const handleChange = (categoryIndex: number, settingIndex: number, value: string) => {
    const updatedCategories = [...categories]
    updatedCategories[categoryIndex].settings[settingIndex].value = value
    setCategories(updatedCategories)
  }

  const handleToggle = (categoryIndex: number, settingIndex: number) => {
    const updatedCategories = [...categories]
    const currentValue = updatedCategories[categoryIndex].settings[settingIndex].value
    
    // تبدیل مقدار به boolean و سپس برعکس کردن آن
    const newValue = currentValue === 'true' ? 'false' : 'true'
    updatedCategories[categoryIndex].settings[settingIndex].value = newValue
    
    setCategories(updatedCategories)
  }

  const saveSettings = async (categoryName: string) => {
    try {
      setSaving(true)
      const categoryIndex = categories.findIndex(c => c.name === categoryName)
      
      if (categoryIndex === -1) return
      
      const settings = categories[categoryIndex].settings
      
      await axios.patch('/api/settings', { settings })
      
      toast({
        title: 'ذخیره شد',
        description: 'تنظیمات با موفقیت ذخیره شدند'
      })
    } catch (error) {
      toast({
        title: 'خطا',
        description: 'خطا در ذخیره تنظیمات',
        variant: 'destructive'
      })
    } finally {
      setSaving(false)
    }
  }

  const renderSettingInput = (setting: Setting, categoryIndex: number, settingIndex: number) => {
    // بررسی نوع مقدار برای تعیین نوع کنترل مناسب
    if (setting.value === 'true' || setting.value === 'false') {
      return (
        <div className="flex items-center space-x-2 space-x-reverse">
          <Switch 
            checked={setting.value === 'true'}
            onCheckedChange={() => handleToggle(categoryIndex, settingIndex)}
          />
          <Label>{setting.value === 'true' ? 'فعال' : 'غیرفعال'}</Label>
        </div>
      )
    } else if (!isNaN(Number(setting.value))) {
      return (
        <Input 
          type="number"
          value={setting.value}
          onChange={(e: React.ChangeEvent<HTMLInputElement>) => handleChange(categoryIndex, settingIndex, e.target.value)}
          className="max-w-sm"
        />
      )
    } else {
      return (
        <Input 
          type="text"
          value={setting.value}
          onChange={(e: React.ChangeEvent<HTMLInputElement>) => handleChange(categoryIndex, settingIndex, e.target.value)}
          className="max-w-md"
        />
      )
    }
  }

  if (loading) {
    return (
      <div className="container py-8">
        <h1 className="text-3xl font-bold mb-6">تنظیمات</h1>
        <div className="flex justify-center items-center h-64">
          <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-primary"></div>
        </div>
      </div>
    )
  }

  return (
    <div className="container py-8">
      <h1 className="text-3xl font-bold mb-6">تنظیمات</h1>
      
      <Tabs defaultValue={categories[0]?.name}>
        <TabsList className="mb-6">
          {categories.map(category => (
            <TabsTrigger key={category.name} value={category.name}>
              {category.name.charAt(0).toUpperCase() + category.name.slice(1)}
            </TabsTrigger>
          ))}
        </TabsList>
        
        {categories.map((category, categoryIndex) => (
          <TabsContent key={category.name} value={category.name}>
            <Card>
              <CardHeader>
                <CardTitle>تنظیمات {category.name}</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-6">
                  {category.settings.map((setting, settingIndex) => (
                    <div key={setting.key} className="space-y-2">
                      <Label htmlFor={setting.key}>{setting.description || setting.key}</Label>
                      {renderSettingInput(setting, categoryIndex, settingIndex)}
                    </div>
                  ))}
                </div>
                
                <div className="mt-8">
                  <Button 
                    onClick={() => saveSettings(category.name)}
                    disabled={saving}
                  >
                    {saving ? 'در حال ذخیره...' : 'ذخیره تنظیمات'}
                  </Button>
                </div>
              </CardContent>
            </Card>
          </TabsContent>
        ))}
      </Tabs>
    </div>
  )
}

export default SettingsPage
