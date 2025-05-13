import React, { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Button } from '../../components/ui/button'
import { useAuthStore } from '../../stores/authStore'
import { useToast } from '../../hooks/use-toast'
import axios from 'axios'

interface LoginFormData {
  username: string
  password: string
}

interface AuthResponse {
  access_token: string
  token_type: string
  expires_in?: number
}

interface UserData {
  id: number
  username: string
  email: string
  full_name?: string
  is_admin: boolean
  role: string
  created_at: string
}

const LoginPage: React.FC = () => {
  const [formData, setFormData] = useState<LoginFormData>({
    username: '',
    password: '',
  })
  const [loading, setLoading] = useState(false)
  const navigate = useNavigate()
  const { login } = useAuthStore()
  const { toast } = useToast()
  
  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { name, value } = e.target
    setFormData((prev) => ({ ...prev, [name]: value }))
  }
  
  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    
    if (!formData.username || !formData.password) {
      toast({
        variant: 'destructive',
        title: 'خطا',
        description: 'نام کاربری و رمز عبور را وارد کنید',
      })
      return
    }
    
    try {
      setLoading(true)
      
      const formDataObj = new FormData()
      formDataObj.append('username', formData.username)
      formDataObj.append('password', formData.password)
      
      const response = await axios.post<AuthResponse>('/api/auth/token', {
        username: formData.username,
        password: formData.password,
      })
      
      const { access_token } = response.data
      
      // دریافت اطلاعات کاربر
      const userResponse = await axios.get<UserData>('/api/users/me', {
        headers: {
          Authorization: `Bearer ${access_token}`,
        },
      })
      
      login(access_token, userResponse.data)
      
      toast({
        variant: 'success',
        title: 'ورود موفق',
        description: 'به پنل مدیریت سلف بات خوش آمدید',
      })
      
      navigate('/dashboard')
    } catch (error: any) {
      toast({
        variant: 'destructive',
        title: 'خطا در ورود',
        description: error.response?.data?.detail || 'نام کاربری یا رمز عبور اشتباه است',
      })
    } finally {
      setLoading(false)
    }
  }
  
  return (
    <div className="p-6">
      <div className="mb-4 text-center">
        <h2 className="text-xl font-bold">ورود به پنل مدیریت</h2>
        <p className="text-sm text-muted-foreground">
          اطلاعات ورود خود را وارد کنید
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
        
        <Button type="submit" className="w-full" disabled={loading}>
          {loading ? 'در حال ورود...' : 'ورود'}
        </Button>
      </form>
    </div>
  )
}

export default LoginPage
