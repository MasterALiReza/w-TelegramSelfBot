import React, { useEffect, useState } from 'react'
import { useToast } from '../../hooks/use-toast'
import axios from 'axios'
import { StatsWidget, TimeRangeSelector } from '../../components/dashboard/StatsWidget'
import ActivityChart from '../../components/dashboard/ActivityChart'
import ActivityList from '../../components/dashboard/ActivityList'
import SystemStatus from '../../components/dashboard/SystemStatus'

interface StatsData {
  total_users: number
  total_plugins: number
  active_plugins: number
  total_messages: number
  daily_messages: number
  bot_status: 'online' | 'offline' | 'error'
  last_activity: string
}

interface RecentActivity {
  id: number
  type: string
  description: string
  timestamp: string
  user_id?: number
  username?: string
}

const DashboardPage: React.FC = () => {
  const [loading, setLoading] = useState(true)
  const [stats, setStats] = useState<StatsData | null>(null)
  const [activities, setActivities] = useState<RecentActivity[]>([])
  const [systemResources, setSystemResources] = useState<SystemResource[]>([])
  const [timeRange, setTimeRange] = useState<'day' | 'week' | 'month' | 'year'>('day')
  const [messageStats, setMessageStats] = useState<any>(null)
  const { toast } = useToast()
  
  // تعریف نوع برای منابع سیستم
  interface SystemResource {
    name: string
    usage: number
    limit: number
    unit: string
  }
  
  useEffect(() => {
    const fetchDashboardData = async () => {
      try {
        setLoading(true)
        
        // دریافت اطلاعات آماری
        const statsResponse = await axios.get<StatsData>('/api/stats/summary')
        setStats(statsResponse.data)
        
        // دریافت فعالیت‌های اخیر
        const activitiesResponse = await axios.get<RecentActivity[]>('/api/activities/recent')
        setActivities(activitiesResponse.data || [])
        
        // دریافت اطلاعات سیستم
        const resourcesResponse = await axios.get('/api/system/resources')
        setSystemResources([
          {
            name: 'CPU',
            usage: resourcesResponse.data?.cpu_usage || 0,
            limit: 100,
            unit: '%'
          },
          {
            name: 'RAM',
            usage: resourcesResponse.data?.memory_usage || 0,
            limit: resourcesResponse.data?.memory_total || 8192,
            unit: 'MB'
          },
          {
            name: 'Disk',
            usage: resourcesResponse.data?.disk_usage || 0,
            limit: resourcesResponse.data?.disk_total || 102400,
            unit: 'MB'
          }
        ])
        
        // دریافت آمار پیام‌ها بر اساس بازه زمانی
        const messageStatsResponse = await axios.get(`/api/stats/messages/${timeRange}`)
        setMessageStats({
          labels: messageStatsResponse.data?.labels || [],
          datasets: [
            {
              label: 'پیام‌های دریافتی',
              data: messageStatsResponse.data?.received || [],
              backgroundColor: '#3b82f6'
            },
            {
              label: 'پیام‌های ارسالی',
              data: messageStatsResponse.data?.sent || [],
              backgroundColor: '#10b981'
            }
          ]
        })
        
      } catch (error: any) {
        toast({
          variant: 'destructive',
          title: 'خطا در بارگیری اطلاعات',
          description: 'دریافت اطلاعات داشبورد با مشکل مواجه شد',
        })
        console.error('Error fetching dashboard data:', error)
      } finally {
        setLoading(false)
      }
    }
    
    fetchDashboardData()
    
    // بروزرسانی خودکار هر 60 ثانیه
    const intervalId = setInterval(fetchDashboardData, 60000)
    
    return () => clearInterval(intervalId)
  }, [toast, timeRange])
  
  // وضعیت ربات با رنگ مناسب
  const getBotStatusColor = (status: string | undefined) => {
    switch (status) {
      case 'online':
        return 'bg-green-500'
      case 'offline':
        return 'bg-red-500'
      case 'error':
        return 'bg-yellow-500'
      default:
        return 'bg-gray-500'
    }
  }
  
  // فرمت تاریخ برای نمایش
  const formatDate = (dateString: string) => {
    if (!dateString) return 'نامشخص'
    
    try {
      const date = new Date(dateString)
      return new Intl.DateTimeFormat('fa-IR', {
        year: 'numeric',
        month: 'long',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
      }).format(date)
    } catch (e) {
      return dateString
    }
  }
  
  if (loading && !stats) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-primary"></div>
      </div>
    )
  }
  
  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <h1 className="text-2xl font-bold tracking-tight">داشبورد</h1>
        <div className="flex items-center gap-2">
          <span className="text-sm">وضعیت سلف بات:</span>
          <span className={`inline-block w-3 h-3 rounded-full ${getBotStatusColor(stats?.bot_status)}`}></span>
          <span>{stats?.bot_status === 'online' ? 'آنلاین' : stats?.bot_status === 'offline' ? 'آفلاین' : 'خطا'}</span>
        </div>
      </div>
      
      {/* کارت‌های آمار */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <StatsWidget 
          title="تعداد کاربران" 
          value={stats?.total_users || 0}
          loading={loading}
          trend={{
            value: 12,
            direction: 'up',
            label: 'نسبت به ماه گذشته'
          }}
        />
        
        <StatsWidget 
          title="پلاگین‌های فعال" 
          value={`${stats?.active_plugins || 0}/${stats?.total_plugins || 0}`}
          loading={loading}
        />
        
        <StatsWidget 
          title="پیام‌های پردازش شده امروز" 
          value={stats?.daily_messages || 0}
          loading={loading}
          trend={{
            value: 8,
            direction: 'up',
            label: 'نسبت به دیروز'
          }}
        />
        
        <StatsWidget 
          title="آخرین فعالیت" 
          value={formatDate(stats?.last_activity || '')}
          loading={loading}
          description="آخرین زمان فعالیت ربات"
        />
      </div>
      
      {/* بخش نمودارها و وضعیت */}
      <div className="grid gap-4 md:grid-cols-2">
        <div className="space-y-4">
          <div className="flex justify-between items-center">
            <h2 className="text-xl font-bold">آمار پیام‌ها</h2>
            <TimeRangeSelector onRangeChange={(range) => setTimeRange(range)} defaultValue={timeRange} />
          </div>
          
          <ActivityChart 
            title="آمار پیام‌ها" 
            data={messageStats || {
              labels: [],
              datasets: []
            }} 
            loading={loading} 
          />
        </div>
        
        <div className="space-y-4">
          <h2 className="text-xl font-bold">وضعیت سیستم</h2>
          <SystemStatus resources={systemResources} loading={loading} />
        </div>
      </div>
      
      {/* فعالیت‌های اخیر */}
      <div className="space-y-4">
        <h2 className="text-xl font-bold">فعالیت‌های اخیر</h2>
        <ActivityList activities={activities} loading={loading} />
      </div>
    </div>
  )
}

export default DashboardPage
