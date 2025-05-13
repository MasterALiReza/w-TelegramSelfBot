import React from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '../ui/card'

interface SystemResource {
  name: string
  usage: number
  limit: number
  unit: string
}

interface SystemStatusProps {
  resources: SystemResource[]
  loading?: boolean
}

const SystemStatus: React.FC<SystemStatusProps> = ({ resources, loading = false }: SystemStatusProps) => {
  const getUsagePercent = (usage: number, limit: number) => {
    return Math.min(100, Math.round((usage / limit) * 100))
  }

  const getProgressColor = (percent: number) => {
    if (percent < 50) return 'bg-green-500'
    if (percent < 80) return 'bg-yellow-500'
    return 'bg-red-500'
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>وضعیت سیستم</CardTitle>
      </CardHeader>
      <CardContent>
        {loading ? (
          <div className="space-y-4">
            {[...Array(3)].map((_, i) => (
              <div key={i} className="space-y-2">
                <div className="h-4 w-32 animate-pulse rounded bg-muted"></div>
                <div className="h-2 w-full animate-pulse rounded bg-muted"></div>
              </div>
            ))}
          </div>
        ) : (
          <div className="space-y-4">
            {resources.map((resource) => {
              const percent = getUsagePercent(resource.usage, resource.limit)
              
              return (
                <div key={resource.name} className="space-y-2">
                  <div className="flex justify-between">
                    <span className="text-sm font-medium">{resource.name}</span>
                    <span className="text-sm text-muted-foreground">
                      {resource.usage} / {resource.limit} {resource.unit}
                    </span>
                  </div>
                  <div className="relative h-2 w-full overflow-hidden rounded-full bg-primary/20">
                    <div 
                      className={`absolute top-0 left-0 h-full ${getProgressColor(percent)}`}
                      style={{ width: `${percent}%` }}
                    ></div>
                  </div>
                </div>
              )
            })}
          </div>
        )}
      </CardContent>
    </Card>
  )
}

export default SystemStatus
