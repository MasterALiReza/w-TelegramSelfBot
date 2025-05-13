import React, { useEffect, useState } from 'react'
import axios from 'axios'
import { Card, CardContent, CardHeader, CardTitle } from '../../components/ui/card'
import { Button } from '../../components/ui/button'
import { Input } from '../../components/ui/input'
import { useToast } from '../../hooks/use-toast'
import { DownloadIcon, SearchIcon, XIcon } from 'lucide-react'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../../components/ui/select'

interface LogEntry {
  id: number
  timestamp: string
  level: 'INFO' | 'WARNING' | 'ERROR' | 'DEBUG'
  source: string
  message: string
  details?: string
}

const LogsPage: React.FC = () => {
  const [logs, setLogs] = useState<LogEntry[]>([])
  const [filteredLogs, setFilteredLogs] = useState<LogEntry[]>([])
  const [loading, setLoading] = useState<boolean>(true)
  const [searchTerm, setSearchTerm] = useState<string>('')
  const [selectedLevel, setSelectedLevel] = useState<string>('all')
  const [selectedSource, setSelectedSource] = useState<string>('all')
  const [availableSources, setAvailableSources] = useState<string[]>([])
  const [page, setPage] = useState<number>(1)
  const [hasMore, setHasMore] = useState<boolean>(true)
  const { toast } = useToast()
  
  const PAGE_SIZE = 50

  useEffect(() => {
    fetchLogs()
  }, [])

  useEffect(() => {
    applyFilters()
  }, [searchTerm, selectedLevel, selectedSource, logs])

  const fetchLogs = async (loadMore = false) => {
    try {
      setLoading(true)
      const currentPage = loadMore ? page + 1 : 1
      
      const { data } = await axios.get<{ logs: LogEntry[], has_more: boolean }>('/api/logs', {
        params: {
          page: currentPage,
          page_size: PAGE_SIZE
        }
      })
      
      // استخراج منابع منحصر به فرد لاگ
      const uniqueSources = Array.from(
        new Set([...availableSources, ...data.logs.map(log => log.source)])
      )
      setAvailableSources(uniqueSources)
      
      if (loadMore) {
        setLogs([...logs, ...data.logs])
        setPage(currentPage)
      } else {
        setLogs(data.logs)
        setPage(1)
      }
      
      setHasMore(data.has_more)
    } catch (error) {
      toast({
        title: 'خطا',
        description: 'خطا در بارگذاری لاگ‌ها',
        variant: 'destructive'
      })
    } finally {
      setLoading(false)
    }
  }

  const applyFilters = () => {
    let filtered = [...logs]
    
    // فیلتر بر اساس سطح
    if (selectedLevel !== 'all') {
      filtered = filtered.filter(log => log.level === selectedLevel)
    }
    
    // فیلتر بر اساس منبع
    if (selectedSource !== 'all') {
      filtered = filtered.filter(log => log.source === selectedSource)
    }
    
    // فیلتر بر اساس متن جستجو
    if (searchTerm.trim() !== '') {
      filtered = filtered.filter(log => 
        log.message.toLowerCase().includes(searchTerm.toLowerCase()) ||
        (log.details && log.details.toLowerCase().includes(searchTerm.toLowerCase()))
      )
    }
    
    setFilteredLogs(filtered)
  }

  const handleClearFilters = () => {
    setSearchTerm('')
    setSelectedLevel('all')
    setSelectedSource('all')
  }

  const handleLoadMore = () => {
    fetchLogs(true)
  }

  const exportLogs = () => {
    const logsToExport = filteredLogs.length > 0 ? filteredLogs : logs
    const content = logsToExport.map(log => `[${log.timestamp}] [${log.level}] [${log.source}] ${log.message}${log.details ? `\nDetails: ${log.details}` : ''}`).join('\n\n')
    
    const blob = new Blob([content], { type: 'text/plain' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `selfbot_logs_${new Date().toISOString().split('T')[0]}.txt`
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    URL.revokeObjectURL(url)
  }

  const getLevelBadgeClass = (level: string) => {
    const classes = {
      'INFO': 'bg-blue-100 text-blue-800',
      'WARNING': 'bg-yellow-100 text-yellow-800',
      'ERROR': 'bg-red-100 text-red-800',
      'DEBUG': 'bg-gray-100 text-gray-800'
    }
    
    return classes[level as keyof typeof classes] || 'bg-gray-100 text-gray-800'
  }

  const formatTimestamp = (timestamp: string) => {
    return new Date(timestamp).toLocaleString('fa-IR', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit'
    })
  }

  return (
    <div className="container py-8">
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-3xl font-bold">لاگ‌های سیستم</h1>
        <div className="flex gap-2">
          <Button onClick={exportLogs} variant="outline">
            <DownloadIcon className="ml-2 h-4 w-4" />
            خروجی
          </Button>
          <Button onClick={() => fetchLogs(false)}>بارگذاری مجدد</Button>
        </div>
      </div>
      
      {/* فیلترها */}
      <div className="flex flex-wrap gap-3 mb-6">
        <div className="flex items-center rounded-md border-border border px-3 flex-1">
          <SearchIcon className="h-4 w-4 text-muted-foreground" />
          <Input
            placeholder="جستجو در لاگ‌ها..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="border-0 focus-visible:ring-0 focus-visible:ring-offset-0"
          />
          {searchTerm && (
            <Button variant="ghost" size="sm" onClick={() => setSearchTerm('')} className="h-8 w-8 p-0">
              <XIcon className="h-4 w-4" />
            </Button>
          )}
        </div>
        
        <Select value={selectedLevel} onValueChange={setSelectedLevel}>
          <SelectTrigger className="w-32">
            <SelectValue placeholder="سطح لاگ" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">همه</SelectItem>
            <SelectItem value="INFO">اطلاعات</SelectItem>
            <SelectItem value="WARNING">هشدار</SelectItem>
            <SelectItem value="ERROR">خطا</SelectItem>
            <SelectItem value="DEBUG">دیباگ</SelectItem>
          </SelectContent>
        </Select>
        
        <Select value={selectedSource} onValueChange={setSelectedSource}>
          <SelectTrigger className="w-40">
            <SelectValue placeholder="منبع لاگ" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">همه منابع</SelectItem>
            {availableSources.map(source => (
              <SelectItem key={source} value={source}>{source}</SelectItem>
            ))}
          </SelectContent>
        </Select>
        
        <Button 
          variant="outline" 
          onClick={handleClearFilters}
          disabled={searchTerm === '' && selectedLevel === 'all' && selectedSource === 'all'}
        >
          پاک کردن فیلترها
        </Button>
      </div>
      
      {loading && page === 1 ? (
        <div className="flex justify-center items-center h-64">
          <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-primary"></div>
        </div>
      ) : (
        <Card>
          <CardHeader>
            <CardTitle>
              لاگ‌های سیستم
              {filteredLogs.length !== logs.length && (
                <span className="text-sm font-normal mr-2 text-muted-foreground">
                  (نمایش {filteredLogs.length} از {logs.length} رکورد)
                </span>
              )}
            </CardTitle>
          </CardHeader>
          <CardContent>
            {filteredLogs.length === 0 ? (
              <div className="text-center py-8 text-muted-foreground">
                هیچ لاگی با معیارهای فیلتر یافت نشد
              </div>
            ) : (
              <div className="space-y-4">
                {filteredLogs.map(log => (
                  <div key={log.id} className="p-4 border rounded-md">
                    <div className="flex justify-between items-start mb-2">
                      <div className="flex items-center gap-2">
                        <span className={`text-xs px-2 py-1 rounded-full ${getLevelBadgeClass(log.level)}`}>
                          {log.level}
                        </span>
                        <span className="text-sm font-medium">{log.source}</span>
                      </div>
                      <div className="text-xs text-muted-foreground">
                        {formatTimestamp(log.timestamp)}
                      </div>
                    </div>
                    <div className="text-sm">{log.message}</div>
                    {log.details && (
                      <div className="mt-2 bg-secondary/20 p-2 rounded text-xs font-mono whitespace-pre-wrap">
                        {log.details}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}
            
            {hasMore && (
              <div className="flex justify-center mt-6">
                <Button 
                  onClick={handleLoadMore} 
                  variant="outline"
                  disabled={loading}
                >
                  {loading ? 'در حال بارگذاری...' : 'بارگذاری بیشتر'}
                </Button>
              </div>
            )}
          </CardContent>
        </Card>
      )}
    </div>
  )
}

export default LogsPage
