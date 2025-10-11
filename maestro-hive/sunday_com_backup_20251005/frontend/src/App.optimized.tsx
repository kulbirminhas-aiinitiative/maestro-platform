import { useEffect, Suspense, lazy } from 'react'
import { Routes, Route, Navigate } from 'react-router-dom'
import { useUIStore } from '@/store/ui'
import { useInitializeAuth } from '@/hooks/useAuth'
import AuthLayout from '@/components/layout/AuthLayout'
import AppLayout from '@/components/layout/AppLayout'
import LoadingScreen from '@/components/ui/LoadingScreen'
import ErrorBoundary from '@/components/ErrorBoundary'

// Lazy load pages for better performance
const LoginPage = lazy(() => import('@/pages/auth/LoginPage'))
const RegisterPage = lazy(() => import('@/pages/auth/RegisterPage'))
const DashboardPage = lazy(() => import('@/pages/DashboardPage'))
const WorkspacePage = lazy(() => import('@/pages/WorkspacePage'))
const BoardPage = lazy(() => import('@/pages/BoardPage'))
const SettingsPage = lazy(() => import('@/pages/SettingsPage'))

// Lazy load major features
const BoardView = lazy(() => import('@/components/boards/BoardView').then(module => ({ default: module.BoardView })))
const BoardsPage = lazy(() => import('@/pages/BoardsPage').then(module => ({ default: module.BoardsPage })))

// Performance-optimized loading wrapper
interface LazyWrapperProps {
  children: React.ReactNode
  fallback?: React.ReactNode
}

const LazyWrapper: React.FC<LazyWrapperProps> = ({
  children,
  fallback = <LoadingScreen message="Loading page..." />
}) => {
  return (
    <Suspense fallback={fallback}>
      <ErrorBoundary>
        {children}
      </ErrorBoundary>
    </Suspense>
  )
}

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

  // Preload critical routes after initial load
  useEffect(() => {
    if (isAuthenticated) {
      // Preload dashboard and board components
      import('@/pages/DashboardPage')
      import('@/components/boards/BoardView')
    }
  }, [isAuthenticated])

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
                    <Route path="login" element={
                      <LazyWrapper>
                        <LoginPage />
                      </LazyWrapper>
                    } />
                    <Route path="register" element={
                      <LazyWrapper>
                        <RegisterPage />
                      </LazyWrapper>
                    } />
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
                    <Route path="dashboard" element={
                      <LazyWrapper>
                        <DashboardPage />
                      </LazyWrapper>
                    } />
                    <Route path="workspace/:workspaceId" element={
                      <LazyWrapper>
                        <WorkspacePage />
                      </LazyWrapper>
                    } />
                    <Route path="workspace/:workspaceId/boards" element={
                      <LazyWrapper>
                        <BoardsPage />
                      </LazyWrapper>
                    } />
                    <Route path="board/:boardId" element={
                      <LazyWrapper>
                        <BoardPage />
                      </LazyWrapper>
                    } />
                    <Route path="boards/:boardId" element={
                      <LazyWrapper>
                        <BoardView />
                      </LazyWrapper>
                    } />
                    <Route path="settings/*" element={
                      <LazyWrapper>
                        <SettingsPage />
                      </LazyWrapper>
                    } />
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