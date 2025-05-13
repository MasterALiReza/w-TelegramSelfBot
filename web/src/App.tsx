import { Routes, Route, Navigate } from 'react-router-dom'
import { Toaster } from '@/components/ui/toaster'
import { Suspense, lazy, ReactNode } from 'react'
import AuthLayout from '@/components/layout/AuthLayout'
import DashboardLayout from '@/components/layout/DashboardLayout'
import LoadingPage from '@/components/shared/LoadingPage'
import { useAuthStore } from '@/stores/authStore'

// لیزی لودینگ صفحات
const LoginPage = lazy(() => import('./pages/auth/LoginPage'))
const RegisterPage = lazy(() => import('./pages/auth/RegisterPage'))
const DashboardPage = lazy(() => import('./pages/dashboard/DashboardPage'))
const PluginsPage = lazy(() => import('./pages/dashboard/PluginsPage'))
const SettingsPage = lazy(() => import('./pages/dashboard/SettingsPage'))
const StatsPage = lazy(() => import('./pages/dashboard/StatsPage'))
const UsersPage = lazy(() => import('./pages/dashboard/UsersPage'))
const LogsPage = lazy(() => import('./pages/dashboard/LogsPage'))
const NotFoundPage = lazy(() => import('./pages/NotFoundPage'))

// کامپوننت مسیرهای محافظت شده
const ProtectedRoute = ({ children }: { children: ReactNode }) => {
  const { isAuthenticated } = useAuthStore()
  
  if (!isAuthenticated) {
    return <Navigate to="/auth/login" replace />
  }
  
  return <>{children}</>
}

// کامپوننت مسیرهای عمومی
const PublicRoute = ({ children }: { children: ReactNode }) => {
  const { isAuthenticated } = useAuthStore()
  
  if (isAuthenticated) {
    return <Navigate to="/dashboard" replace />
  }
  
  return <>{children}</>
}

function App() {
  return (
    <>
      <Suspense fallback={<LoadingPage />}>
        <Routes>
          {/* مسیرهای احراز هویت */}
          <Route path="/auth/login" element={
            <PublicRoute>
              <AuthLayout>
                <LoginPage />
              </AuthLayout>
            </PublicRoute>
          } />
          <Route path="/auth/register" element={
            <PublicRoute>
              <AuthLayout>
                <RegisterPage />
              </AuthLayout>
            </PublicRoute>
          } />
          
          {/* مسیرهای داشبورد */}
          <Route path="/" element={
            <ProtectedRoute>
              <DashboardLayout>
                <Navigate to="/dashboard" replace />
              </DashboardLayout>
            </ProtectedRoute>
          } />
          <Route path="/dashboard" element={
            <ProtectedRoute>
              <DashboardLayout>
                <DashboardPage />
              </DashboardLayout>
            </ProtectedRoute>
          } />
          <Route path="/plugins" element={
            <ProtectedRoute>
              <DashboardLayout>
                <PluginsPage />
              </DashboardLayout>
            </ProtectedRoute>
          } />
          <Route path="/settings" element={
            <ProtectedRoute>
              <DashboardLayout>
                <SettingsPage />
              </DashboardLayout>
            </ProtectedRoute>
          } />
          <Route path="/stats" element={
            <ProtectedRoute>
              <DashboardLayout>
                <StatsPage />
              </DashboardLayout>
            </ProtectedRoute>
          } />
          <Route path="/users" element={
            <ProtectedRoute>
              <DashboardLayout>
                <UsersPage />
              </DashboardLayout>
            </ProtectedRoute>
          } />
          <Route path="/logs" element={
            <ProtectedRoute>
              <DashboardLayout>
                <LogsPage />
              </DashboardLayout>
            </ProtectedRoute>
          } />
          
          {/* صفحه 404 */}
          <Route path="*" element={<NotFoundPage />} />
        </Routes>
      </Suspense>
      
      {/* سیستم نوتیفیکیشن */}
      <Toaster />
    </>
  )
}

export default App
