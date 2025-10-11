import React, { Suspense } from 'react'
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { ErrorBoundary } from '@/components/ErrorBoundary'
import { AuthProvider } from '@/contexts/AuthContext'
import { ProtectedRoute, RequireAuth } from './ProtectedRoute'
import { AppLayout } from '@/components/layout/AppLayout'
import { AuthLayout } from '@/components/layout/AuthLayout'
import { LoadingScreen } from '@/components/ui/LoadingScreen'

// Lazy load pages for better performance
const DashboardPage = React.lazy(() => import('@/pages/DashboardPage'))
const WorkspacePage = React.lazy(() => import('@/pages/WorkspacePage'))
const BoardsPage = React.lazy(() => import('@/pages/BoardsPage'))
const BoardPage = React.lazy(() => import('@/pages/BoardPage'))
const SettingsPage = React.lazy(() => import('@/pages/SettingsPage'))
const LoginPage = React.lazy(() => import('@/pages/auth/LoginPage'))
const RegisterPage = React.lazy(() => import('@/pages/auth/RegisterPage'))

// Error pages
const NotFoundPage = React.lazy(() => import('@/pages/errors/NotFoundPage'))
const ServerErrorPage = React.lazy(() => import('@/pages/errors/ServerErrorPage'))

interface AppRouterProps {
  basename?: string
}

export const AppRouter: React.FC<AppRouterProps> = ({ basename }) => {
  return (
    <BrowserRouter basename={basename}>
      <ErrorBoundary>
        <AuthProvider>
          <Suspense fallback={<LoadingScreen message="Loading application..." />}>
            <Routes>
              {/* Public routes */}
              <Route
                path="/auth/*"
                element={
                  <AuthLayout>
                    <Routes>
                      <Route path="login" element={<LoginPage />} />
                      <Route path="register" element={<RegisterPage />} />
                      <Route path="*" element={<Navigate to="/auth/login" replace />} />
                    </Routes>
                  </AuthLayout>
                }
              />

              {/* Protected routes */}
              <Route
                path="/*"
                element={
                  <RequireAuth>
                    <AppLayout>
                      <Routes>
                        {/* Dashboard */}
                        <Route path="/" element={<Navigate to="/dashboard" replace />} />
                        <Route path="/dashboard" element={<DashboardPage />} />

                        {/* Workspace routes */}
                        <Route path="/workspaces/:workspaceId" element={<WorkspacePage />} />
                        <Route
                          path="/workspaces/:workspaceId/boards"
                          element={<BoardsPage />}
                        />

                        {/* Board routes */}
                        <Route path="/boards/:boardId" element={<BoardPage />} />

                        {/* Settings */}
                        <Route path="/settings/*" element={<SettingsPage />} />

                        {/* Error pages */}
                        <Route path="/error/500" element={<ServerErrorPage />} />
                        <Route path="/404" element={<NotFoundPage />} />

                        {/* Catch all */}
                        <Route path="*" element={<NotFoundPage />} />
                      </Routes>
                    </AppLayout>
                  </RequireAuth>
                }
              />
            </Routes>
          </Suspense>
        </AuthProvider>
      </ErrorBoundary>
    </BrowserRouter>
  )
}

// Route configuration for external use
export const routes = {
  auth: {
    login: '/auth/login',
    register: '/auth/register',
  },
  dashboard: '/dashboard',
  workspace: (workspaceId: string) => `/workspaces/${workspaceId}`,
  boards: (workspaceId: string) => `/workspaces/${workspaceId}/boards`,
  board: (boardId: string) => `/boards/${boardId}`,
  settings: '/settings',
  errors: {
    notFound: '/404',
    serverError: '/error/500',
  },
} as const

// Helper function to navigate to routes
export const navigateTo = {
  dashboard: () => '/dashboard',
  workspace: (workspaceId: string) => `/workspaces/${workspaceId}`,
  boards: (workspaceId: string) => `/workspaces/${workspaceId}/boards`,
  board: (boardId: string) => `/boards/${boardId}`,
  settings: (tab?: string) => tab ? `/settings/${tab}` : '/settings',
  auth: {
    login: (returnUrl?: string) =>
      returnUrl ? `/auth/login?returnUrl=${encodeURIComponent(returnUrl)}` : '/auth/login',
    register: () => '/auth/register',
  },
}

export default AppRouter