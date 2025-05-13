import React from 'react'

const LoadingPage: React.FC = () => {
  return (
    <div className="flex items-center justify-center h-screen w-full bg-background">
      <div className="flex flex-col items-center gap-4">
        <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-primary"></div>
        <p className="text-lg text-muted-foreground">در حال بارگذاری...</p>
      </div>
    </div>
  )
}

export default LoadingPage
