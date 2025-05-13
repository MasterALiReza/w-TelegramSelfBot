import React, { ReactNode } from 'react'

interface AuthLayoutProps {
  children?: ReactNode;
}

const AuthLayout: React.FC<AuthLayoutProps> = ({ children }) => {
  return (
    <div className="flex min-h-screen flex-col items-center justify-center bg-gray-100 dark:bg-gray-900 p-4">
      <div className="w-full max-w-md">
        <div className="mb-6 flex justify-center">
          <div className="flex flex-col items-center justify-center text-center">
            <img 
              src="/logo.svg" 
              alt="تلگرام سلف بات" 
              className="h-16 w-16 mb-2" 
            />
            <h1 className="text-2xl font-bold text-primary">
              تلگرام سلف بات
            </h1>
            <p className="text-sm text-muted-foreground mt-1">
              پنل مدیریت حرفه‌ای سلف بات تلگرام
            </p>
          </div>
        </div>
        
        <div className="rounded-lg border bg-card text-card-foreground shadow-sm">
          {children}
        </div>
        
        <p className="mt-4 text-center text-sm text-muted-foreground">
          © {new Date().getFullYear()} تلگرام سلف بات - تمامی حقوق محفوظ است
        </p>
      </div>
    </div>
  )
}

export default AuthLayout
