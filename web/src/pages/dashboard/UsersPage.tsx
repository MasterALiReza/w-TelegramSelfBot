import React, { useEffect, useState } from 'react'
import axios from 'axios'
import { Card, CardContent, CardHeader, CardTitle } from '../../components/ui/card'
import { Button } from '../../components/ui/button'
import { Input } from '../../components/ui/input'
import { Switch } from '../../components/ui/switch'
import { useToast } from '../../hooks/use-toast'
import { Label } from '../../components/ui/label'
import { 
  Dialog, 
  DialogContent, 
  DialogDescription, 
  DialogFooter, 
  DialogHeader, 
  DialogTitle 
} from '../../components/ui/dialog'

interface User {
  id: number
  username: string
  full_name: string
  email: string
  is_admin: boolean
  is_active: boolean
  created_at: string
  last_login: string | null
}

const UsersPage: React.FC = () => {
  const [users, setUsers] = useState<User[]>([])
  const [filteredUsers, setFilteredUsers] = useState<User[]>([])
  const [loading, setLoading] = useState<boolean>(true)
  const [searchTerm, setSearchTerm] = useState<string>('')
  const [isAddModalOpen, setIsAddModalOpen] = useState<boolean>(false)
  const [newUser, setNewUser] = useState({
    username: '',
    full_name: '',
    email: '',
    password: '',
    is_admin: false
  })
  const { toast } = useToast()

  useEffect(() => {
    fetchUsers()
  }, [])

  useEffect(() => {
    // فیلتر کردن کاربران بر اساس عبارت جستجو
    if (searchTerm.trim() === '') {
      setFilteredUsers(users)
    } else {
      const filtered = users.filter(user => 
        user.username.toLowerCase().includes(searchTerm.toLowerCase()) ||
        user.full_name.toLowerCase().includes(searchTerm.toLowerCase()) ||
        user.email.toLowerCase().includes(searchTerm.toLowerCase())
      )
      setFilteredUsers(filtered)
    }
  }, [searchTerm, users])

  const fetchUsers = async () => {
    try {
      setLoading(true)
      const { data } = await axios.get<User[]>('/api/users')
      setUsers(data)
      setFilteredUsers(data)
    } catch (error) {
      toast({
        title: 'خطا',
        description: 'خطا در بارگذاری کاربران',
        variant: 'destructive'
      })
    } finally {
      setLoading(false)
    }
  }

  const handleToggleStatus = async (userId: number, currentStatus: boolean) => {
    try {
      await axios.patch(`/api/users/${userId}`, {
        is_active: !currentStatus
      })
      
      // بروزرسانی وضعیت کاربر در حالت محلی
      const updatedUsers = users.map(user => 
        user.id === userId ? { ...user, is_active: !currentStatus } : user
      )
      
      setUsers(updatedUsers)
      
      toast({
        title: 'انجام شد',
        description: `کاربر ${!currentStatus ? 'فعال' : 'غیرفعال'} شد.`
      })
    } catch (error) {
      toast({
        title: 'خطا',
        description: 'خطا در تغییر وضعیت کاربر',
        variant: 'destructive'
      })
    }
  }

  const handleToggleAdmin = async (userId: number, currentStatus: boolean) => {
    try {
      await axios.patch(`/api/users/${userId}`, {
        is_admin: !currentStatus
      })
      
      // بروزرسانی وضعیت کاربر در حالت محلی
      const updatedUsers = users.map(user => 
        user.id === userId ? { ...user, is_admin: !currentStatus } : user
      )
      
      setUsers(updatedUsers)
      
      toast({
        title: 'انجام شد',
        description: `دسترسی مدیریت ${!currentStatus ? 'داده' : 'گرفته'} شد.`
      })
    } catch (error) {
      toast({
        title: 'خطا',
        description: 'خطا در تغییر وضعیت مدیریت',
        variant: 'destructive'
      })
    }
  }

  const handleAddUser = async () => {
    try {
      // اعتبارسنجی فرم
      if (!newUser.username || !newUser.email || !newUser.password) {
        toast({
          title: 'خطا',
          description: 'لطفاً تمام فیلدهای اجباری را تکمیل کنید',
          variant: 'destructive'
        })
        return
      }
      
      const { data } = await axios.post<User>('/api/users', newUser)
      
      // افزودن کاربر جدید به لیست
      setUsers([...users, data])
      
      // بستن مودال و پاک کردن فرم
      setIsAddModalOpen(false)
      setNewUser({
        username: '',
        full_name: '',
        email: '',
        password: '',
        is_admin: false
      })
      
      toast({
        title: 'انجام شد',
        description: 'کاربر جدید با موفقیت ایجاد شد'
      })
    } catch (error) {
      toast({
        title: 'خطا',
        description: 'خطا در ایجاد کاربر جدید',
        variant: 'destructive'
      })
    }
  }

  const formatDate = (dateString: string | null) => {
    if (!dateString) return 'هرگز'
    
    return new Date(dateString).toLocaleDateString('fa-IR', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    })
  }

  return (
    <div className="container py-8">
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-3xl font-bold">مدیریت کاربران</h1>
        <div className="flex gap-2">
          <Button onClick={() => setIsAddModalOpen(true)} variant="default">افزودن کاربر</Button>
          <Button onClick={() => fetchUsers()} variant="outline">بارگذاری مجدد</Button>
        </div>
      </div>
      
      <div className="mb-6">
        <Input
          placeholder="جستجو کاربر..."
          value={searchTerm}
          onChange={(e: React.ChangeEvent<HTMLInputElement>) => setSearchTerm(e.target.value)}
          className="max-w-md"
        />
      </div>
      
      {loading ? (
        <div className="flex justify-center items-center h-64">
          <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-primary"></div>
        </div>
      ) : (
        <Card>
          <CardHeader>
            <CardTitle>کاربران سیستم</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="border-b">
                    <th className="text-right py-3 px-4 font-medium">نام کاربری</th>
                    <th className="text-right py-3 px-4 font-medium">نام کامل</th>
                    <th className="text-right py-3 px-4 font-medium">ایمیل</th>
                    <th className="text-right py-3 px-4 font-medium">آخرین ورود</th>
                    <th className="text-right py-3 px-4 font-medium">مدیر</th>
                    <th className="text-right py-3 px-4 font-medium">وضعیت</th>
                  </tr>
                </thead>
                <tbody>
                  {filteredUsers.map(user => (
                    <tr key={user.id} className="border-b hover:bg-muted/50">
                      <td className="py-3 px-4">{user.username}</td>
                      <td className="py-3 px-4">{user.full_name || '-'}</td>
                      <td className="py-3 px-4">{user.email}</td>
                      <td className="py-3 px-4">{formatDate(user.last_login)}</td>
                      <td className="py-3 px-4">
                        <Switch 
                          checked={user.is_admin}
                          onCheckedChange={() => handleToggleAdmin(user.id, user.is_admin)}
                        />
                      </td>
                      <td className="py-3 px-4">
                        <Switch 
                          checked={user.is_active}
                          onCheckedChange={() => handleToggleStatus(user.id, user.is_active)}
                        />
                      </td>
                    </tr>
                  ))}
                  
                  {filteredUsers.length === 0 && (
                    <tr>
                      <td colSpan={6} className="text-center py-4 text-muted-foreground">
                        {searchTerm ? 'هیچ کاربری با این مشخصات یافت نشد' : 'هیچ کاربری موجود نیست'}
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </CardContent>
        </Card>
      )}
      
      {/* مودال افزودن کاربر */}
      <Dialog open={isAddModalOpen} onOpenChange={setIsAddModalOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>افزودن کاربر جدید</DialogTitle>
            <DialogDescription>
              اطلاعات کاربر جدید را وارد کنید
            </DialogDescription>
          </DialogHeader>
          
          <div className="space-y-4 py-2">
            <div className="space-y-2">
              <Label htmlFor="username">نام کاربری</Label>
              <Input
                id="username"
                placeholder="نام کاربری"
                value={newUser.username}
                onChange={(e: React.ChangeEvent<HTMLInputElement>) => setNewUser({ ...newUser, username: e.target.value })}
              />
            </div>
            
            <div className="space-y-2">
              <Label htmlFor="full_name">نام کامل</Label>
              <Input
                id="full_name"
                placeholder="نام کامل"
                value={newUser.full_name}
                onChange={(e: React.ChangeEvent<HTMLInputElement>) => setNewUser({ ...newUser, full_name: e.target.value })}
              />
            </div>
            
            <div className="space-y-2">
              <Label htmlFor="email">ایمیل</Label>
              <Input
                id="email"
                type="email"
                placeholder="ایمیل"
                value={newUser.email}
                onChange={(e: React.ChangeEvent<HTMLInputElement>) => setNewUser({ ...newUser, email: e.target.value })}
              />
            </div>
            
            <div className="space-y-2">
              <Label htmlFor="password">گذرواژه</Label>
              <Input
                id="password"
                type="password"
                placeholder="گذرواژه"
                value={newUser.password}
                onChange={(e: React.ChangeEvent<HTMLInputElement>) => setNewUser({ ...newUser, password: e.target.value })}
              />
            </div>
            
            <div className="flex items-center space-x-2 space-x-reverse">
              <Switch
                id="is_admin"
                checked={newUser.is_admin}
                onCheckedChange={(checked: boolean) => setNewUser({ ...newUser, is_admin: checked })}
              />
              <Label htmlFor="is_admin">دسترسی مدیریت</Label>
            </div>
          </div>
          
          <DialogFooter>
            <Button variant="outline" onClick={() => setIsAddModalOpen(false)}>انصراف</Button>
            <Button onClick={handleAddUser}>افزودن</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}

export default UsersPage
