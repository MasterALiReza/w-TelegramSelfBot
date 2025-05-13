import React from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '../ui/card'
import { Tabs, TabsList, TabsTrigger } from '../ui/tabs'

interface StatsWidgetProps {
  title: string
  value: string | number
  description?: string
  icon?: React.ReactNode
  loading?: boolean
  trend?: {
    value: number
    direction: 'up' | 'down' | 'neutral'
    label: string
  }
}

export const StatsWidget: React.FC<StatsWidgetProps> = ({
  title,
  value,
  description,
  icon,
  loading = false,
  trend
}) => {
  return (
    <Card className="overflow-hidden">
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
        <CardTitle className="text-sm font-medium text-muted-foreground">{title}</CardTitle>
        {icon && <div className="text-primary">{icon}</div>}
      </CardHeader>
      <CardContent>
        {loading ? (
          <div className="h-9 w-full animate-pulse rounded bg-muted"></div>
        ) : (
          <>
            <div className="text-2xl font-bold">{value}</div>
            {description && (
              <p className="text-xs text-muted-foreground mt-1">{description}</p>
            )}
            {trend && (
              <div className="flex items-center mt-2">
                <span
                  className={`ml-1 rounded-sm px-1 py-0.5 text-xs ${
                    trend.direction === 'up'
                      ? 'bg-green-100 text-green-800'
                      : trend.direction === 'down'
                      ? 'bg-red-100 text-red-800'
                      : 'bg-gray-100 text-gray-800'
                  }`}
                >
                  {trend.direction === 'up' 
                    ? `↑ ${trend.value}%` 
                    : trend.direction === 'down' 
                    ? `↓ ${trend.value}%` 
                    : `${trend.value}%`}
                </span>
                <span className="text-xs text-muted-foreground">{trend.label}</span>
              </div>
            )}
          </>
        )}
      </CardContent>
    </Card>
  )
}

interface TimeRangeProps {
  onRangeChange: (range: 'day' | 'week' | 'month' | 'year') => void
  defaultValue?: 'day' | 'week' | 'month' | 'year'
}

export const TimeRangeSelector: React.FC<TimeRangeProps> = ({ 
  onRangeChange, 
  defaultValue = 'day' 
}) => {
  return (
    <Tabs defaultValue={defaultValue} onValueChange={(value: string) => onRangeChange(value as 'day' | 'week' | 'month' | 'year')}>
      <TabsList className="grid grid-cols-4 w-[400px]">
        <TabsTrigger value="day">امروز</TabsTrigger>
        <TabsTrigger value="week">هفته</TabsTrigger>
        <TabsTrigger value="month">ماه</TabsTrigger>
        <TabsTrigger value="year">سال</TabsTrigger>
      </TabsList>
    </Tabs>
  )
}
