import React, { useState } from 'react'
import { Link, useNavigate, useLocation } from 'react-router-dom'
import { 
  Home, Settings, Users, BarChart2, 
  Package, FileText, LogOut, Menu, X
} from 'lucide-react'
import { Button } from '../ui/button'
import { useAuthStore } from '../../stores/authStore'

interface DashboardLayoutProps {
  children?: React.ReactNode;
}

const DashboardLayout: React.FC<DashboardLayoutProps> = ({ children }) => {
  const location = useLocation()
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const { logout, user } = useAuthStore()
  const navigate = useNavigate()
  
  const handleLogout = () => {
    logout()
    navigate('/auth/login')
  }
  
  // کلاس‌بندی برای لینک فعال
  const getNavItemClasses = (path: string) => {
    const isActive = location.pathname.startsWith(path)
    return `flex items-center p-2 rounded-md transition-colors ${isActive 
      ? 'bg-primary/10 text-primary' 
      : 'text-muted-foreground hover:bg-primary/5 hover:text-primary'}`
  }

  const navItems = [
    { path: '/dashboard', label: 'داشبورد', icon: <Home className="w-5 h-5" /> },
    { path: '/plugins', label: 'پلاگین‌ها', icon: <Package className="w-5 h-5" /> },
    { path: '/stats', label: 'آمار و تحلیل', icon: <BarChart2 className="w-5 h-5" /> },
    { path: '/users', label: 'کاربران', icon: <Users className="w-5 h-5" /> },
    { path: '/logs', label: 'گزارش‌ها', icon: <FileText className="w-5 h-5" /> },
    { path: '/settings', label: 'تنظیمات', icon: <Settings className="w-5 h-5" /> },
  ]
  
  const toggleSidebar = () => setSidebarOpen(!sidebarOpen)
  
  return (
    <div className="flex h-screen overflow-hidden bg-gray-100 dark:bg-gray-900">
      {/* سایدبار موبایل */}
      <div className={`fixed inset-0 z-40 flex lg:hidden ${sidebarOpen ? 'block' : 'hidden'}`}>
        <div className="fixed inset-0 bg-gray-600 bg-opacity-75" onClick={toggleSidebar}></div>
        <aside className="relative flex w-full max-w-xs flex-1 flex-col bg-background pt-5 pb-4">
          <div className="absolute top-0 left-0 -ml-12 pt-2">
            <button
              className="flex h-10 w-10 items-center justify-center rounded-full focus:outline-none focus:ring-2 focus:ring-inset focus:ring-white"
              onClick={toggleSidebar}
            >
              <X className="h-6 w-6 text-white" />
            </button>
          </div>
          
          <div className="flex flex-shrink-0 items-center px-4">
            <img className="h-8 w-auto" src="/logo.svg" alt="تلگرام سلف بات" />
            <h1 className="mr-2 text-xl font-bold text-primary">تلگرام سلف بات</h1>
          </div>
          
          <nav className="mt-8 flex-1 space-y-1 px-2">
            <div className="space-y-1 px-3">
              {navItems.map(item => (
                <Link
                  key={item.path}
                  to={item.path}
                  className={getNavItemClasses(item.path)}
                >
                  {item.icon}
                  <span className="mx-3">{item.label}</span>
                </Link>
              ))}
            </div>
          </nav>
          
          <div className="flex flex-shrink-0 border-t border-gray-200 dark:border-gray-700 p-4">
            <Button
              variant="ghost"
              className="w-full justify-start"
              onClick={handleLogout}
            >
              <LogOut className="h-5 w-5 ml-2" />
              خروج
            </Button>
          </div>
        </aside>
      </div>
      
      {/* سایدبار دسکتاپ */}
      <aside className="hidden lg:flex lg:flex-shrink-0">
        <div className="flex w-64 flex-col">
          <div className="flex min-h-0 flex-1 flex-col border-l border-gray-200 dark:border-gray-700 bg-background">
            <div className="flex flex-1 flex-col overflow-y-auto pt-5 pb-4">
              <div className="flex flex-shrink-0 items-center px-4">
                <img className="h-8 w-auto" src="/logo.svg" alt="تلگرام سلف بات" />
                <h1 className="mr-2 text-xl font-bold text-primary">تلگرام سلف بات</h1>
              </div>
              
              <nav className="mt-8 flex-1 space-y-1 px-2">
                <ul>
                  {navItems.map(item => (
                    <li key={item.path}>
                      <Link
                        to={item.path}
                        className={getNavItemClasses(item.path)}
                      >
                        {item.icon}
                        <span className="mx-3">{item.label}</span>
                      </Link>
                    </li>
                  ))}
                </ul>
              </nav>
            </div>
            
            <div className="flex flex-shrink-0 border-t border-gray-200 dark:border-gray-700 p-4">
              <Button
                variant="ghost"
                className="w-full justify-start"
                onClick={handleLogout}
              >
                <LogOut className="h-5 w-5 ml-2" />
                خروج
              </Button>
            </div>
          </div>
        </div>
      </aside>
      
      {/* محتوای اصلی */}
      <div className="flex flex-1 flex-col overflow-hidden">
        {/* هدر */}
        <header className="bg-white dark:bg-gray-800 shadow-sm z-10 flex h-16 flex-shrink-0 border-b border-gray-200 dark:border-gray-700">
          <button
            className="border-l border-gray-200 dark:border-gray-700 px-4 text-gray-500 focus:outline-none focus:ring-2 focus:ring-inset focus:ring-primary lg:hidden"
            onClick={toggleSidebar}
          >
            <Menu className="h-6 w-6" />
          </button>
          
          <div className="flex flex-1 items-center justify-between px-4">
            <div>
              <div className="text-lg font-semibold text-gray-900 dark:text-white">
                خوش آمدید، {user?.username || 'کاربر'}
              </div>
              <div className="text-sm text-gray-500 dark:text-gray-400">
                {user?.role === 'admin' ? 'مدیر' : 'کاربر'}
              </div>
            </div>
            <div></div>
          </div>
        </header>
        
        {/* محتوای صفحه */}
        <main className="flex-1 p-6 overflow-auto">
          {children}
        </main>
      </div>
    </div>
  )
}

export default DashboardLayout
