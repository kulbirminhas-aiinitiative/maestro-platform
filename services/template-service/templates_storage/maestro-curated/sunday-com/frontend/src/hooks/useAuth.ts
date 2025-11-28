import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { api } from '@/lib/api'
import { useAuthStore } from '@/store/auth'
import { QUERY_KEYS } from '@/lib/constants'
import type { User, LoginCredentials, RegisterData } from '@/types'

// Get current user
export const useCurrentUser = () => {
  const { isAuthenticated } = useAuthStore()

  return useQuery({
    queryKey: QUERY_KEYS.CURRENT_USER,
    queryFn: async () => {
      const response = await api.auth.me()
      return response.data.user as User
    },
    enabled: isAuthenticated,
    staleTime: 5 * 60 * 1000, // 5 minutes
    retry: (failureCount, error: any) => {
      // Don't retry on 401 errors
      if (error?.status === 401) {
        useAuthStore.getState().logout()
        return false
      }
      return failureCount < 3
    },
  })
}

// Login mutation
export const useLogin = () => {
  const queryClient = useQueryClient()
  const { setUser, setTokens } = useAuthStore()

  return useMutation({
    mutationFn: async (credentials: LoginCredentials) => {
      const response = await api.auth.login(credentials)
      return response.data
    },
    onSuccess: (data) => {
      setUser(data.user)
      setTokens(data.tokens)

      // Set user data in React Query cache
      queryClient.setQueryData(QUERY_KEYS.CURRENT_USER, data.user)

      // Invalidate and refetch user data
      queryClient.invalidateQueries({ queryKey: QUERY_KEYS.CURRENT_USER })
    },
  })
}

// Register mutation
export const useRegister = () => {
  const queryClient = useQueryClient()
  const { setUser, setTokens } = useAuthStore()

  return useMutation({
    mutationFn: async (userData: RegisterData) => {
      const response = await api.auth.register(userData)
      return response.data
    },
    onSuccess: (data) => {
      setUser(data.user)
      setTokens(data.tokens)

      // Set user data in React Query cache
      queryClient.setQueryData(QUERY_KEYS.CURRENT_USER, data.user)

      // Invalidate and refetch user data
      queryClient.invalidateQueries({ queryKey: QUERY_KEYS.CURRENT_USER })
    },
  })
}

// Update profile mutation
export const useUpdateProfile = () => {
  const queryClient = useQueryClient()
  const { setUser } = useAuthStore()

  return useMutation({
    mutationFn: async (userData: Partial<User>) => {
      const response = await api.auth.updateProfile(userData)
      return response.data.user
    },
    onSuccess: (updatedUser) => {
      setUser(updatedUser)

      // Update user data in React Query cache
      queryClient.setQueryData(QUERY_KEYS.CURRENT_USER, updatedUser)

      // Invalidate related queries
      queryClient.invalidateQueries({ queryKey: QUERY_KEYS.CURRENT_USER })
    },
  })
}

// Logout function
export const useLogout = () => {
  const queryClient = useQueryClient()
  const { logout } = useAuthStore()

  return () => {
    logout()

    // Clear all queries from cache
    queryClient.clear()
  }
}

// Check if user has permission
export const useHasPermission = (permission: string, organizationId?: string) => {
  const { user } = useAuthStore()

  if (!user || !organizationId) return false

  const organization = user.organizations?.find(org => org.id === organizationId)
  if (!organization) return false

  return organization.permissions.includes(permission)
}

// Check if user has role
export const useHasRole = (role: string, organizationId?: string) => {
  const { user } = useAuthStore()

  if (!user || !organizationId) return false

  const organization = user.organizations?.find(org => org.id === organizationId)
  if (!organization) return false

  return organization.role === role
}

// Hook to initialize auth state on app start
export const useInitializeAuth = () => {
  const { isAuthenticated, setUser } = useAuthStore()
  const { data: user, isLoading, error } = useCurrentUser()

  // Update user in store when query succeeds
  if (user && !error) {
    setUser(user)
  }

  // Handle auth errors
  if (error && isAuthenticated) {
    useAuthStore.getState().logout()
  }

  return {
    isLoading,
    isAuthenticated: isAuthenticated && !error,
    user,
  }
}