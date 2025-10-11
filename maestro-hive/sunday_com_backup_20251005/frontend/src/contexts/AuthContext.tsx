import React, { createContext, useContext, useEffect, useState, ReactNode } from 'react'
import { useAuthStore } from '@/store/auth'
import { useCurrentUser } from '@/hooks/useAuth'
import { apiClient } from '@/lib/api'
import { webSocketService } from '@/services/websocket.service'
import { LoadingScreen } from '@/components/ui/LoadingScreen'
import type { User } from '@/types'

interface AuthContextType {
  user: User | null
  isAuthenticated: boolean
  isLoading: boolean
  error: string | null
  refreshAuth: () => Promise<void>
  hasPermission: (permission: string, organizationId?: string) => boolean
  hasRole: (role: string, organizationId?: string) => boolean
  getCurrentUserId: () => string | null
}

const AuthContext = createContext<AuthContextType | undefined>(undefined)

interface AuthProviderProps {
  children: ReactNode
}

export const AuthProvider: React.FC<AuthProviderProps> = ({ children }) => {
  const [isInitialized, setIsInitialized] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const {
    user,
    isAuthenticated,
    setUser,
    setTokens,
    logout,
    refreshToken,
  } = useAuthStore()

  // Initialize authentication state
  useEffect(() => {
    const initializeAuth = async () => {
      try {
        // Check if we have a token in localStorage
        const token = apiClient.getToken()
        if (!token) {
          setIsInitialized(true)
          return
        }

        // Try to refresh the token and get user data
        const refreshSuccess = await refreshToken()
        if (refreshSuccess) {
          // Get current user data
          try {
            const response = await apiClient.get<{ data: { user: User } }>('/api/v1/auth/me')
            setUser(response.data.user)
          } catch (userError) {
            console.error('Failed to fetch user data:', userError)
            logout()
          }
        }
      } catch (initError) {
        console.error('Auth initialization failed:', initError)
        logout()
        setError('Authentication initialization failed')
      } finally {
        setIsInitialized(true)
      }
    }

    initializeAuth()
  }, [refreshToken, setUser, logout])

  // Setup token refresh interceptor
  useEffect(() => {
    const setupTokenRefresh = () => {
      // Intercept API responses to handle token expiration
      const originalRequest = apiClient.request.bind(apiClient)

      apiClient.request = async function<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
        try {
          return await originalRequest(endpoint, options)
        } catch (error: any) {
          if (error.status === 401 && isAuthenticated) {
            // Token expired, try to refresh
            const refreshSuccess = await refreshToken()
            if (refreshSuccess) {
              // Retry the original request with new token
              return originalRequest(endpoint, options)
            } else {
              logout()
              throw error
            }
          }
          throw error
        }
      }
    }

    if (isAuthenticated) {
      setupTokenRefresh()
    }
  }, [isAuthenticated, refreshToken, logout])

  // Handle user changes for WebSocket
  useEffect(() => {
    if (user && isAuthenticated) {
      // Reconnect WebSocket with new user context
      webSocketService.disconnect()
      setTimeout(() => {
        // Small delay to ensure clean disconnect
        webSocketService.connect?.()
      }, 100)
    } else if (!isAuthenticated) {
      webSocketService.disconnect()
    }
  }, [user, isAuthenticated])

  const refreshAuth = async () => {
    try {
      setError(null)
      const refreshSuccess = await refreshToken()
      if (refreshSuccess) {
        const response = await apiClient.get<{ data: { user: User } }>('/api/v1/auth/me')
        setUser(response.data.user)
      } else {
        logout()
      }
    } catch (error) {
      console.error('Failed to refresh auth:', error)
      setError('Failed to refresh authentication')
      logout()
    }
  }

  const hasPermission = (permission: string, organizationId?: string): boolean => {
    if (!user || !organizationId) return false

    const organization = user.organizations?.find(org => org.id === organizationId)
    if (!organization) return false

    return organization.permissions?.includes(permission) || false
  }

  const hasRole = (role: string, organizationId?: string): boolean => {
    if (!user || !organizationId) return false

    const organization = user.organizations?.find(org => org.id === organizationId)
    if (!organization) return false

    return organization.role === role
  }

  const getCurrentUserId = (): string | null => {
    return user?.id || null
  }

  const contextValue: AuthContextType = {
    user,
    isAuthenticated,
    isLoading: !isInitialized,
    error,
    refreshAuth,
    hasPermission,
    hasRole,
    getCurrentUserId,
  }

  // Show loading screen while initializing
  if (!isInitialized) {
    return <LoadingScreen message="Initializing authentication..." />
  }

  return (
    <AuthContext.Provider value={contextValue}>
      {children}
    </AuthContext.Provider>
  )
}

export const useAuthContext = (): AuthContextType => {
  const context = useContext(AuthContext)
  if (context === undefined) {
    throw new Error('useAuthContext must be used within an AuthProvider')
  }
  return context
}

// Enhanced hooks that use the context
export const useCurrentUserId = () => {
  const { getCurrentUserId } = useAuthContext()
  return getCurrentUserId()
}

export const usePermissions = (organizationId?: string) => {
  const { hasPermission, hasRole } = useAuthContext()

  return {
    hasPermission: (permission: string) => hasPermission(permission, organizationId),
    hasRole: (role: string) => hasRole(role, organizationId),
  }
}

export const useRequireAuth = () => {
  const { isAuthenticated, isLoading } = useAuthContext()

  useEffect(() => {
    if (!isLoading && !isAuthenticated) {
      // Redirect to login page
      window.location.href = '/auth/login'
    }
  }, [isAuthenticated, isLoading])

  return { isAuthenticated, isLoading }
}