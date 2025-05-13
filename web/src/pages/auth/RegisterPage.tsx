import React, { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Button } from '@/components/ui/button'
import { useToast } from '@/hooks/use-toast'
import { apiClient } from '@/api/apiClient'

interface RegisterFormData {
  username: string
  email: string
  password: string
  confirmPassword: string
}

const RegisterPage: React.FC = () => {
  const [formData, setFormData] = useState<RegisterFormData>({
    username: '',
    email: '',
    password: '',
    confirmPassword: '',
  })
  const [loading, setLoading] = useState(false)
  const navigate = useNavigate()
  const { toast } = useToast()
  
  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { name, value } = e.target
    setFormData((prev) => ({ ...prev, [name]: value }))
  }
  
  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    
    // اعتبارسنجی فرم
    if (!formData.username || !formData.email || !formData.password || !formData.confirmPassword) {
      toast({
        variant: 'destructive',
        title: 'خطا',
        description: 'لطفاً تمامی فیلدها را پر کنید',
      })
      return
    }
    
    if (formData.password !== formData.confirmPassword) {
      toast({
        variant: 'destructive',
        title: 'خطا',
        description: 'رمز عبور و تکرار آن مطابقت ندارند',
      })
      return
    }
    
    try {
      setLoading(true)
      
      // ارسال درخواست به API
      await apiClient.post('/users', {
        username: formData.username,
        email: formData.email,
        password: formData.password,
        confirm_password: formData.confirmPassword,
      })
      
      toast({
        variant: 'success',
        title: 'ثبت‌نام موفق',
        description: 'حساب کاربری شما با موفقیت ایجاد شد',
      })
      
      // انتقال به صفحه ورود
      navigate('/auth/login')
    } catch (error: any) {
      toast({
        variant: 'destructive',
        title: 'خطا در ثبت‌نام',
        description: error.response?.data?.detail || 'خطایی در ثبت‌نام رخ داده است',
      })
    } finally {
      setLoading(false)
    }
  }
  
  return (
    <div className="p-6">
      <div className="mb-4 text-center">
        <h2 className="text-xl font-bold">ایجاد حساب کاربری</h2>
        <p className="text-sm text-muted-foreground">
          اطلاعات خود را برای ثبت‌نام وارد کنید
        </p>
      </div>
      
      <form onSubmit={handleSubmit} className="space-y-4">
        <div className="space-y-2">
          <label className="text-sm font-medium leading-none peer-disabled:cursor-not-allowed peer-disabled:opacity-70">
            نام کاربری
          </label>
          <input
            className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background file:border-0 file:bg-transparent file:text-sm file:font-medium placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
            name="username"
            value={formData.username}
            onChange={handleChange}
            placeholder="نام کاربری خود را وارد کنید"
          />
        </div>
        
        <div className="space-y-2">
          <label className="text-sm font-medium leading-none peer-disabled:cursor-not-allowed peer-disabled:opacity-70">
            ایمیل
          </label>
          <input
            className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background file:border-0 file:bg-transparent file:text-sm file:font-medium placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
            type="email"
            name="email"
            value={formData.email}
            onChange={handleChange}
            placeholder="ایمیل خود را وارد کنید"
          />
        </div>
        
        <div className="space-y-2">
          <label className="text-sm font-medium leading-none peer-disabled:cursor-not-allowed peer-disabled:opacity-70">
            رمز عبور
          </label>
          <input
            className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background file:border-0 file:bg-transparent file:text-sm file:font-medium placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
            type="password"
            name="password"
            value={formData.password}
            onChange={handleChange}
            placeholder="رمز عبور خود را وارد کنید"
          />
        </div>
        
        <div className="space-y-2">
          <label className="text-sm font-medium leading-none peer-disabled:cursor-not-allowed peer-disabled:opacity-70">
            تکرار رمز عبور
          </label>
          <input
            className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background file:border-0 file:bg-transparent file:text-sm file:font-medium placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
            type="password"
            name="confirmPassword"
            value={formData.confirmPassword}
            onChange={handleChange}
            placeholder="رمز عبور خود را مجدداً وارد کنید"
          />
        </div>
        
        <Button type="submit" className="w-full" disabled={loading}>
          {loading ? 'در حال ثبت‌نام...' : 'ثبت‌نام'}
        </Button>
        
        <div className="text-center text-sm">
          <span className="text-muted-foreground">حساب کاربری دارید؟ </span>
          <a href="/auth/login" className="text-primary hover:underline">
            ورود به حساب
          </a>
        </div>
      </form>
    </div>
  )
}

export default RegisterPage
