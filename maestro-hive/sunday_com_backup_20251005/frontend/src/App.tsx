import React, { useEffect } from 'react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { ReactQueryDevtools } from '@tanstack/react-query-devtools'
import { Toaster } from 'react-hot-toast'
import { AppRouter } from '@/components/routing/AppRouter'
import { AppErrorBoundary } from '@/components/errors/ErrorBoundaryEnhanced'
import { MobileNavigation, MobileHeaderSpacer, MobileBottomSpacer } from '@/components/mobile/MobileNavigation'
import { useIsMobile } from '@/hooks/useResponsive'
import '@/styles/globals.css'

// Create a client
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 1000 * 60 * 5, // 5 minutes
      cacheTime: 1000 * 60 * 30, // 30 minutes
      retry: (failureCount, error: any) => {
        // Don't retry on 4xx errors
        if (error?.status >= 400 && error?.status < 500) {
          return false
        }
        return failureCount < 3
      },
      refetchOnWindowFocus: false,
    },
    mutations: {
      retry: 1,
    },
  },
})

function App() {
  const isMobile = useIsMobile()

  // Performance monitoring in development
  useEffect(() => {
    if (process.env.NODE_ENV === 'development') {
      console.log('🚀 Sunday.com App initialized')

      // Monitor bundle size
      if ('performance' in window) {
        window.addEventListener('load', () => {
          const perfData = performance.getEntriesByType('navigation')[0] as PerformanceNavigationTiming
          console.log('📊 App load time:', Math.round(perfData.loadEventEnd - perfData.fetchStart), 'ms')
        })
      }
    }
  }, [])

  // Handle offline/online status
  useEffect(() => {
    const handleOnline = () => {
      console.log('📶 Back online')
      // Refetch queries when back online
      queryClient.refetchQueries()
    }

    const handleOffline = () => {
      console.log('📵 Gone offline')
    }

    window.addEventListener('online', handleOnline)
    window.addEventListener('offline', handleOffline)

    return () => {
      window.removeEventListener('online', handleOnline)
      window.removeEventListener('offline', handleOffline)
    }
  }, [])

  return (
    <AppErrorBoundary>
      <QueryClientProvider client={queryClient}>
        <div className="min-h-screen bg-gray-50">
          {/* Mobile Navigation */}
          {isMobile && (
            <>
              <MobileNavigation />
              <MobileHeaderSpacer />
            </>
          )}

          {/* Main App Router */}
          <AppRouter />

          {/* Mobile Bottom Spacer */}
          {isMobile && <MobileBottomSpacer />}

          {/* Toast Notifications */}
          <Toaster
            position="top-right"
            toastOptions={{
              duration: 4000,
              style: {
                background: '#363636',
                color: '#fff',
              },
              success: {
                style: {
                  background: '#10b981',
                },
              },
              error: {
                style: {
                  background: '#ef4444',
                },
              },
            }}
          />

          {/* React Query DevTools (only in development) */}
          {process.env.NODE_ENV === 'development' && (
            <ReactQueryDevtools initialIsOpen={false} />
          )}
        </div>
      </QueryClientProvider>
    </AppErrorBoundary>
  )
}

export default App