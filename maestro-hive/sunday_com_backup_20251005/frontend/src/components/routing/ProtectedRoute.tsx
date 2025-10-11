import React, { ReactNode } from 'react'
import { Navigate, useLocation } from 'react-router-dom'
import { useAuthContext, usePermissions } from '@/contexts/AuthContext'
import { LoadingScreen } from '@/components/ui/LoadingScreen'
import { Button } from '@/components/ui/Button'
import { AlertTriangle, Lock } from 'lucide-react'

interface ProtectedRouteProps {
  children: ReactNode
  fallback?: ReactNode
  requireAuth?: boolean
  requiredPermission?: string
  requiredRole?: string
  organizationId?: string
  redirectTo?: string
}

export const ProtectedRoute: React.FC<ProtectedRouteProps> = ({
  children,
  fallback,
  requireAuth = true,
  requiredPermission,
  requiredRole,
  organizationId,
  redirectTo = '/auth/login',
}) => {
  const location = useLocation()
  const { isAuthenticated, isLoading, user } = useAuthContext()
  const { hasPermission, hasRole } = usePermissions(organizationId)

  // Show loading while checking authentication
  if (isLoading) {
    return <LoadingScreen message="Checking authentication..." />
  }

  // Check authentication requirement
  if (requireAuth && !isAuthenticated) {
    // Redirect to login with return URL
    return (
      <Navigate
        to={redirectTo}
        state={{ from: location.pathname }}
        replace
      />
    )
  }

  // Check permission requirements
  if (requiredPermission && !hasPermission(requiredPermission)) {
    return (
      fallback || (
        <PermissionDenied
          type="permission"
          requirement={requiredPermission}
          organizationId={organizationId}
        />
      )
    )
  }

  // Check role requirements
  if (requiredRole && !hasRole(requiredRole)) {
    return (
      fallback || (
        <PermissionDenied
          type="role"
          requirement={requiredRole}
          organizationId={organizationId}
        />
      )
    )
  }

  return <>{children}</>
}

interface PermissionDeniedProps {
  type: 'permission' | 'role'
  requirement: string
  organizationId?: string
}

const PermissionDenied: React.FC<PermissionDeniedProps> = ({
  type,
  requirement,
  organizationId,
}) => {
  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50">
      <div className="max-w-md w-full text-center p-6">
        <div className="mx-auto flex items-center justify-center h-12 w-12 rounded-full bg-red-100 mb-4">
          <Lock className="h-6 w-6 text-red-600" />
        </div>

        <h1 className="text-2xl font-bold text-gray-900 mb-2">
          Access Denied
        </h1>

        <p className="text-gray-600 mb-4">
          You don't have the required {type} to access this page.
        </p>

        <div className="bg-red-50 border border-red-200 rounded-lg p-4 mb-6">
          <div className="flex items-center">
            <AlertTriangle className="h-5 w-5 text-red-500 mr-2" />
            <div className="text-sm text-red-700">
              <p className="font-medium">Required {type}:</p>
              <p className="font-mono">{requirement}</p>
              {organizationId && (
                <p className="text-xs mt-1">Organization: {organizationId}</p>
              )}
            </div>
          </div>
        </div>

        <div className="space-y-3">
          <Button
            onClick={() => window.history.back()}
            className="w-full"
          >
            Go Back
          </Button>

          <Button
            variant="outline"
            onClick={() => window.location.href = '/dashboard'}
            className="w-full"
          >
            Go to Dashboard
          </Button>
        </div>

        <p className="text-sm text-gray-500 mt-4">
          If you believe this is an error, please contact your administrator.
        </p>
      </div>
    </div>
  )
}

// Convenience components for common use cases
export const RequireAuth: React.FC<{ children: ReactNode }> = ({ children }) => (
  <ProtectedRoute requireAuth={true}>
    {children}
  </ProtectedRoute>
)

export const RequireRole: React.FC<{
  children: ReactNode
  role: string
  organizationId?: string
}> = ({ children, role, organizationId }) => (
  <ProtectedRoute requiredRole={role} organizationId={organizationId}>
    {children}
  </ProtectedRoute>
)

export const RequirePermission: React.FC<{
  children: ReactNode
  permission: string
  organizationId?: string
}> = ({ children, permission, organizationId }) => (
  <ProtectedRoute requiredPermission={permission} organizationId={organizationId}>
    {children}
  </ProtectedRoute>
)

// Higher-order component for protecting routes
export const withAuth = <P extends object>(
  Component: React.ComponentType<P>,
  options?: Omit<ProtectedRouteProps, 'children'>
) => {
  return (props: P) => (
    <ProtectedRoute {...options}>
      <Component {...props} />
    </ProtectedRoute>
  )
}

// Hook for conditional rendering based on permissions
export const useCanAccess = (
  permission?: string,
  role?: string,
  organizationId?: string
) => {
  const { isAuthenticated } = useAuthContext()
  const { hasPermission, hasRole } = usePermissions(organizationId)

  if (!isAuthenticated) return false

  if (permission && !hasPermission(permission)) return false
  if (role && !hasRole(role)) return false

  return true
}