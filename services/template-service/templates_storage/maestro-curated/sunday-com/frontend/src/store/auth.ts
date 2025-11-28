import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import { apiClient } from '@/lib/api'
import { TOKEN_STORAGE_KEY, REFRESH_TOKEN_STORAGE_KEY, USER_STORAGE_KEY } from '@/lib/constants'
import type { User, AuthTokens } from '@/types'

interface AuthState {
  user: User | null
  isAuthenticated: boolean
  isLoading: boolean
  error: string | null

  // Actions
  login: (email: string, password: string) => Promise<void>
  register: (data: any) => Promise<void>
  logout: () => void
  setUser: (user: User | null) => void
  setTokens: (tokens: AuthTokens) => void
  clearError: () => void
  refreshToken: () => Promise<boolean>
  updateProfile: (data: any) => Promise<void>
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set, get) => ({
      user: null,
      isAuthenticated: false,
      isLoading: false,
      error: null,

      login: async (email: string, password: string) => {
        set({ isLoading: true, error: null })

        try {
          const response = await apiClient.post<{
            data: { user: User; tokens: AuthTokens }
          }>('/api/v1/auth/login', { email, password })

          const { user, tokens } = response.data

          // Set tokens in API client and storage
          apiClient.setToken(tokens.accessToken)
          localStorage.setItem(REFRESH_TOKEN_STORAGE_KEY, tokens.refreshToken)

          set({
            user,
            isAuthenticated: true,
            isLoading: false,
            error: null,
          })
        } catch (error: any) {
          set({
            isLoading: false,
            error: error.message || 'Login failed',
          })
          throw error
        }
      },

      register: async (data: any) => {
        set({ isLoading: true, error: null })

        try {
          const response = await apiClient.post<{
            data: { user: User; tokens: AuthTokens }
          }>('/api/v1/auth/register', data)

          const { user, tokens } = response.data

          // Set tokens in API client and storage
          apiClient.setToken(tokens.accessToken)
          localStorage.setItem(REFRESH_TOKEN_STORAGE_KEY, tokens.refreshToken)

          set({
            user,
            isAuthenticated: true,
            isLoading: false,
            error: null,
          })
        } catch (error: any) {
          set({
            isLoading: false,
            error: error.message || 'Registration failed',
          })
          throw error
        }
      },

      logout: () => {
        // Clear tokens
        apiClient.setToken(null)
        localStorage.removeItem(REFRESH_TOKEN_STORAGE_KEY)
        localStorage.removeItem(USER_STORAGE_KEY)

        set({
          user: null,
          isAuthenticated: false,
          error: null,
        })
      },

      setUser: (user: User | null) => {
        set({
          user,
          isAuthenticated: !!user,
        })
      },

      setTokens: (tokens: AuthTokens) => {
        apiClient.setToken(tokens.accessToken)
        localStorage.setItem(REFRESH_TOKEN_STORAGE_KEY, tokens.refreshToken)
      },

      clearError: () => {
        set({ error: null })
      },

      refreshToken: async () => {
        const refreshToken = localStorage.getItem(REFRESH_TOKEN_STORAGE_KEY)
        if (!refreshToken) {
          get().logout()
          return false
        }

        try {
          const response = await apiClient.post<{
            data: { tokens: AuthTokens }
          }>('/api/v1/auth/refresh', { refreshToken })

          const { tokens } = response.data
          get().setTokens(tokens)
          return true
        } catch (error) {
          get().logout()
          return false
        }
      },

      updateProfile: async (data: any) => {
        set({ isLoading: true, error: null })

        try {
          const response = await apiClient.put<{
            data: { user: User }
          }>('/api/v1/auth/me', data)

          set({
            user: response.data.user,
            isLoading: false,
            error: null,
          })
        } catch (error: any) {
          set({
            isLoading: false,
            error: error.message || 'Profile update failed',
          })
          throw error
        }
      },
    }),
    {
      name: 'auth-storage',
      partialize: (state) => ({
        user: state.user,
        isAuthenticated: state.isAuthenticated,
      }),
    }
  )
)

// Helper hooks
export const useAuth = () => {
  const {
    user,
    isAuthenticated,
    isLoading,
    error,
    login,
    register,
    logout,
    clearError,
    updateProfile,
  } = useAuthStore()

  return {
    user,
    isAuthenticated,
    isLoading,
    error,
    login,
    register,
    logout,
    clearError,
    updateProfile,
  }
}

export const useUser = () => {
  return useAuthStore((state) => state.user)
}

export const useIsAuthenticated = () => {
  return useAuthStore((state) => state.isAuthenticated)
}