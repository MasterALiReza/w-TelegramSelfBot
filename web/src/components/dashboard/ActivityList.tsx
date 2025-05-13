import React from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '../ui/card'

interface Activity {
  id: number
  type: string
  description: string
  timestamp: string
  user_id?: number
  username?: string
}

interface ActivityListProps {
  activities: Activity[]
  loading?: boolean
  maxItems?: number
  showHeader?: boolean
}

export const ActivityList: React.FC<ActivityListProps> = ({
  activities,
  loading = false,
  maxItems = 5,
  showHeader = true
}: ActivityListProps) => {
  // تابع فرمت‌دهی تاریخ
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

  // تعیین کلاس CSS بر اساس نوع فعالیت
  const getActivityBadgeClass = (type: string) => {
    switch (type.toLowerCase()) {
      case 'login':
      case 'signup':
        return 'bg-primary text-primary-foreground'
      case 'message':
        return 'bg-secondary text-secondary-foreground'
      case 'plugin':
        return 'border border-input text-foreground'
      case 'error':
        return 'bg-red-500 text-white'
      case 'warning':
        return 'bg-yellow-100 text-yellow-800'
      case 'success':
        return 'bg-green-100 text-green-800'
      default:
        return 'bg-secondary text-secondary-foreground'
    }
  }

  const displayedActivities = maxItems ? activities.slice(0, maxItems) : activities

  return (
    <Card>
      {showHeader && (
        <CardHeader>
          <CardTitle>آخرین فعالیت‌ها</CardTitle>
        </CardHeader>
      )}
      <CardContent>
        {loading ? (
          <div className="space-y-2">
            {[...Array(3)].map((_, i) => (
              <div key={i} className="flex items-center space-x-4 space-x-reverse">
                <div className="h-4 w-20 animate-pulse rounded bg-muted"></div>
                <div className="h-4 w-full animate-pulse rounded bg-muted"></div>
              </div>
            ))}
          </div>
        ) : displayedActivities.length === 0 ? (
          <div className="py-6 text-center text-muted-foreground">
            فعالیتی یافت نشد
          </div>
        ) : (
          <div className="space-y-4">
            {displayedActivities.map((activity) => (
              <div key={activity.id} className="flex flex-col space-y-1">
                <div className="flex items-center justify-between">
                  <div className="flex items-center space-x-2 space-x-reverse">
                    <span className={`inline-flex items-center rounded-md px-2.5 py-0.5 text-xs font-semibold ${getActivityBadgeClass(activity.type)}`}>
                      {activity.type}
                    </span>
                    <span className="text-sm font-medium">{activity.description}</span>
                  </div>
                  <span className="text-xs text-muted-foreground">
                    {formatDate(activity.timestamp)}
                  </span>
                </div>
                {activity.username && (
                  <span className="text-xs text-muted-foreground">
                    کاربر: {activity.username}
                  </span>
                )}
              </div>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  )
}

export default ActivityList
