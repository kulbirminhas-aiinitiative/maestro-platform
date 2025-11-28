import { useEffect } from 'react'
import { Routes, Route, Navigate } from 'react-router-dom'
import { useUIStore } from '@/store/ui'
import { useInitializeAuth } from '@/hooks/useAuth'
import AuthLayout from '@/components/layout/AuthLayout'
import AppLayout from '@/components/layout/AppLayout'
import LoginPage from '@/pages/auth/LoginPage'
import RegisterPage from '@/pages/auth/RegisterPage'
import DashboardPage from '@/pages/DashboardPage'
import WorkspacePage from '@/pages/WorkspacePage'
import BoardPage from '@/pages/BoardPage'
import SettingsPage from '@/pages/SettingsPage'
import LoadingScreen from '@/components/ui/LoadingScreen'
import ErrorBoundary from '@/components/ErrorBoundary'

function App() {
  const { theme, setTheme } = useUIStore()
  const { isLoading, isAuthenticated } = useInitializeAuth()

  // Initialize theme on app start
  useEffect(() => {
    setTheme(theme)
  }, [theme, setTheme])

  // Handle system theme changes
  useEffect(() => {
    if (theme === 'system') {
      const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)')
      const handleChange = () => setTheme('system')

      mediaQuery.addEventListener('change', handleChange)
      return () => mediaQuery.removeEventListener('change', handleChange)
    }
  }, [theme, setTheme])

  // Show loading screen while initializing auth
  if (isLoading) {
    return <LoadingScreen />
  }

  return (
    <ErrorBoundary>
      <div className="min-h-screen bg-background text-foreground">
        <Routes>
          {/* Public routes */}
          {!isAuthenticated ? (
            <>
              <Route path="/auth/*" element={
                <AuthLayout>
                  <Routes>
                    <Route path="login" element={<LoginPage />} />
                    <Route path="register" element={<RegisterPage />} />
                    <Route path="*" element={<Navigate to="/auth/login" replace />} />
                  </Routes>
                </AuthLayout>
              } />
              <Route path="*" element={<Navigate to="/auth/login" replace />} />
            </>
          ) : (
            /* Protected routes */
            <>
              <Route path="/app/*" element={
                <AppLayout>
                  <Routes>
                    <Route path="dashboard" element={<DashboardPage />} />
                    <Route path="workspace/:workspaceId" element={<WorkspacePage />} />
                    <Route path="board/:boardId" element={<BoardPage />} />
                    <Route path="settings/*" element={<SettingsPage />} />
                    <Route path="*" element={<Navigate to="/app/dashboard" replace />} />
                  </Routes>
                </AppLayout>
              } />
              <Route path="*" element={<Navigate to="/app/dashboard" replace />} />
            </>
          )}
        </Routes>
      </div>
    </ErrorBoundary>
  )
}

export default App