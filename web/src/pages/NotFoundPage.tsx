import React from 'react'
import { useNavigate } from 'react-router-dom'
import { Button } from '../components/ui/button'

const NotFoundPage: React.FC = () => {
  const navigate = useNavigate()
  
  return (
    <div className="flex flex-col items-center justify-center h-screen bg-background p-4 text-center">
      <div className="mb-6 text-6xl font-bold text-primary">404</div>
      <h1 className="mb-4 text-2xl font-bold">صفحه مورد نظر یافت نشد</h1>
      <p className="mb-8 text-muted-foreground">
        صفحه‌ای که به دنبال آن بودید وجود ندارد یا حذف شده است.
      </p>
      <div className="flex gap-4">
        <Button
          onClick={() => navigate("-1")}
          variant="outline"
        >
          بازگشت به صفحه قبل
        </Button>
        <Button
          onClick={() => navigate('/')}
          variant="default"
        >
          بازگشت به داشبورد
        </Button>
      </div>
    </div>
  )
}

export default NotFoundPage
