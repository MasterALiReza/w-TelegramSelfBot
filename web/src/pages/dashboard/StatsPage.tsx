import React, { useState, useEffect } from 'react'
import axios from 'axios'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../../components/ui/card'
import { Button } from '../../components/ui/button'
import { useToast } from '../../hooks/use-toast'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../../components/ui/tabs'

interface StatData {
  label: string
  value: number
  change?: number
  changeType?: 'increase' | 'decrease' | 'neutral'
}

interface TimelineData {
  timestamp: string
  value: number
}

interface ChartData {
  title: string
  data: TimelineData[]
}

const StatsPage: React.FC = () => {
  const [summaryStats, setSummaryStats] = useState<StatData[]>([])
  const [charts, setCharts] = useState<ChartData[]>([])
  const [loading, setLoading] = useState<boolean>(true)
  const { toast } = useToast()

  useEffect(() => {
    fetchStats()
  }, [])

  const fetchStats = async () => {
    try {
      setLoading(true)
      
      // دریافت آمار خلاصه
      const { data: summaryData } = await axios.get<StatData[]>('/api/stats/summary')
      setSummaryStats(summaryData)
      
      // دریافت داده‌های نمودار
      const { data: chartData } = await axios.get<ChartData[]>('/api/stats/charts')
      setCharts(chartData)
    } catch (error) {
      toast({
        title: 'خطا',
        description: 'خطا در بارگذاری آمار',
        variant: 'destructive'
      })
    } finally {
      setLoading(false)
    }
  }

  const getChangeIndicator = (changeType?: 'increase' | 'decrease' | 'neutral') => {
    if (changeType === 'increase') {
      return <span className="text-green-500">↑</span>
    } else if (changeType === 'decrease') {
      return <span className="text-red-500">↓</span>
    }
    return null
  }

  const formatChange = (change?: number) => {
    if (change === undefined) return null
    
    const formattedChange = Math.abs(change).toFixed(1)
    return `${formattedChange}%`
  }

  // این تابع در یک محیط واقعی باید با کتابخانه رسم نمودار جایگزین شود
  const renderChart = (data: TimelineData[]) => {
    if (!data || data.length === 0) {
      return <div className="h-48 flex items-center justify-center">داده‌ای برای نمایش وجود ندارد</div>
    }
    
    // نمایش موقت (placeholder) - در پروژه واقعی باید با کتابخانه نمودار مانند Chart.js جایگزین شود
    return (
      <div className="h-48 bg-secondary/20 rounded-md p-4 flex items-end justify-around">
        {data.map((point, index) => {
          // ساخت یک نمودار ستونی ساده
          const height = `${Math.max(10, (point.value / Math.max(...data.map(d => d.value))) * 100)}%`
          
          return (
            <div key={index} className="flex flex-col items-center justify-end h-full">
              <div 
                className="w-8 bg-primary/60 rounded-t-sm" 
                style={{ height }}
                title={`${point.timestamp}: ${point.value}`}
              ></div>
              <div className="text-xs mt-2 text-muted-foreground">
                {new Date(point.timestamp).toLocaleDateString('fa-IR', { month: 'short', day: 'numeric' })}
              </div>
            </div>
          )
        })}
      </div>
    )
  }

  if (loading) {
    return (
      <div className="container py-8">
        <h1 className="text-3xl font-bold mb-6">آمار و تحلیل</h1>
        <div className="flex justify-center items-center h-64">
          <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-primary"></div>
        </div>
      </div>
    )
  }

  return (
    <div className="container py-8">
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-3xl font-bold">آمار و تحلیل</h1>
        <Button onClick={fetchStats}>بارگذاری مجدد</Button>
      </div>
      
      {/* کارت‌های آمار خلاصه */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
        {summaryStats.map((stat, index) => (
          <Card key={index}>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium text-muted-foreground">
                {stat.label}
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">
                {stat.value.toLocaleString('fa-IR')}
                {' '}
                {getChangeIndicator(stat.changeType)}
              </div>
              {stat.change !== undefined && (
                <p className="text-xs text-muted-foreground mt-1">
                  {stat.changeType === 'increase' ? 'افزایش' : stat.changeType === 'decrease' ? 'کاهش' : 'بدون تغییر'}{' '}
                  {formatChange(stat.change)} نسبت به دوره قبل
                </p>
              )}
            </CardContent>
          </Card>
        ))}
      </div>
      
      {/* نمودارها */}
      <h2 className="text-xl font-semibold mb-4">نمودارهای تحلیلی</h2>
      <Tabs defaultValue={charts[0]?.title}>
        <TabsList className="mb-6">
          {charts.map(chart => (
            <TabsTrigger key={chart.title} value={chart.title}>
              {chart.title}
            </TabsTrigger>
          ))}
        </TabsList>
        
        {charts.map(chart => (
          <TabsContent key={chart.title} value={chart.title}>
            <Card>
              <CardHeader>
                <CardTitle>{chart.title}</CardTitle>
                <CardDescription>
                  نمایش داده‌های {chart.title} در بازه زمانی اخیر
                </CardDescription>
              </CardHeader>
              <CardContent>
                {renderChart(chart.data)}
              </CardContent>
            </Card>
          </TabsContent>
        ))}
      </Tabs>
    </div>
  )
}

export default StatsPage
