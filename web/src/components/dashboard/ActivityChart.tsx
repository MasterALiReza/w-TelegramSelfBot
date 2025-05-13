import React from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '../ui/card'

interface ChartData {
  labels: string[]
  datasets: {
    label: string
    data: number[]
    backgroundColor?: string
    borderColor?: string
    borderWidth?: number
  }[]
}

interface ActivityChartProps {
  title: string
  data: ChartData
  type?: 'line' | 'bar' | 'pie'
  height?: number
  loading?: boolean
}

const ActivityChart: React.FC<ActivityChartProps> = ({
  title,
  data,
  // استفاده نمی‌شود اما برای آینده نگه داشته شده است
  // type = 'line',
  // height = 300,
  loading = false
}) => {
  // در اینجا باید از یک کتابخانه نمودار استفاده کرد
  // به عنوان مثال chart.js یا recharts
  // فعلاً یک نمایش موقت نشان می‌دهیم

  return (
    <Card>
      <CardHeader>
        <CardTitle>{title}</CardTitle>
      </CardHeader>
      <CardContent>
        {loading ? (
          <div className="h-[300px] w-full flex items-center justify-center">
            <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-primary"></div>
          </div>
        ) : (
          <div className="h-[300px] w-full border rounded-md p-4 bg-gray-50">
            <div className="h-full w-full flex flex-col">
              <div className="flex justify-between mb-2">
                {data.labels.map((label: string, index: number) => (
                  <div key={index} className="text-xs text-gray-500">{label}</div>
                ))}
              </div>
              <div className="flex-grow relative">
                {data.datasets.map((dataset: any, datasetIndex: number) => (
                  <div key={datasetIndex} className="mb-2">
                    <div className="flex items-center mb-1">
                      <div 
                        className="w-3 h-3 mr-1 rounded-full" 
                        style={{ backgroundColor: dataset.backgroundColor || '#3b82f6' }} 
                      />
                      <span className="text-xs">{dataset.label}</span>
                    </div>
                    <div className="h-8 bg-gray-200 rounded-md w-full overflow-hidden">
                      {dataset.data.map((value: number, index: number) => {
                        const maxValue = Math.max(...dataset.data)
                        const width = maxValue > 0 ? (value / maxValue) * 100 : 0
                        return (
                          <div
                            key={index}
                            className="h-full transition-all duration-500"
                            style={{
                              width: `${width}%`,
                              backgroundColor: dataset.backgroundColor || '#3b82f6',
                              display: 'inline-block'
                            }}
                          />
                        )
                      })}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  )
}

export default ActivityChart
