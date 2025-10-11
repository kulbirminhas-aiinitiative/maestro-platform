import React, { Component, ReactNode } from 'react'
import { Button } from '@/components/ui/Button'
import { Card } from '@/components/ui/Card'
import { AlertTriangle, RefreshCw, Home, Bug, Send } from 'lucide-react'
import { ServerErrorPage } from '@/pages/errors/ServerErrorPage'

interface Props {
  children: ReactNode
  fallback?: ReactNode
  level?: 'page' | 'component' | 'app'
  onError?: (error: Error, errorInfo: React.ErrorInfo) => void
}

interface State {
  hasError: boolean
  error?: Error
  errorInfo?: React.ErrorInfo
  errorId?: string
}

class ErrorBoundaryEnhanced extends Component<Props, State> {
  private retryCount = 0
  private maxRetries = 3

  constructor(props: Props) {
    super(props)
    this.state = { hasError: false }
  }

  static getDerivedStateFromError(error: Error): State {
    const errorId = `error_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`
    return { hasError: true, error, errorId }
  }

  componentDidCatch(error: Error, errorInfo: React.ErrorInfo) {
    this.setState({ error, errorInfo })

    // Log error details
    const errorDetails = {
      message: error.message,
      stack: error.stack,
      componentStack: errorInfo.componentStack,
      timestamp: new Date().toISOString(),
      level: this.props.level || 'component',
      userAgent: navigator.userAgent,
      url: window.location.href,
      userId: this.getCurrentUserId(),
      errorId: this.state.errorId,
    }

    // Log to console in development
    if (process.env.NODE_ENV === 'development') {
      console.group('🚨 Error Boundary Caught Error')
      console.error('Error:', error)
      console.error('Error Info:', errorInfo)
      console.error('Error Details:', errorDetails)
      console.groupEnd()
    }

    // Send to error tracking service
    this.reportError(errorDetails)

    // Call custom error handler
    if (this.props.onError) {
      this.props.onError(error, errorInfo)
    }
  }

  private getCurrentUserId(): string | null {
    // Try to get current user ID from auth store
    try {
      const authState = JSON.parse(localStorage.getItem('auth-storage') || '{}')
      return authState?.state?.user?.id || null
    } catch {
      return null
    }
  }

  private async reportError(errorDetails: any) {
    try {
      // In production, send to error tracking service
      if (process.env.NODE_ENV === 'production' && process.env.VITE_ERROR_TRACKING_URL) {
        await fetch(process.env.VITE_ERROR_TRACKING_URL, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify(errorDetails),
        })
      }
    } catch (reportingError) {
      console.error('Failed to report error:', reportingError)
    }
  }

  handleReset = () => {
    this.retryCount++
    this.setState({ hasError: false, error: undefined, errorInfo: undefined })
  }

  handleReload = () => {
    window.location.reload()
  }

  handleGoHome = () => {
    window.location.href = '/dashboard'
  }

  handleReportError = async () => {
    const errorReport = {
      errorId: this.state.errorId,
      message: this.state.error?.message,
      timestamp: new Date().toISOString(),
      userFeedback: 'User reported this error',
    }

    try {
      // Send error report
      await this.reportError(errorReport)
      alert('Error report sent. Thank you for helping us improve!')
    } catch {
      alert('Failed to send error report. Please try again later.')
    }
  }

  renderComponentError() {
    return (
      <Card className="p-6 border-red-200 bg-red-50">
        <div className="flex items-start space-x-3">
          <AlertTriangle className="h-5 w-5 text-red-600 mt-0.5" />
          <div className="flex-1">
            <h3 className="text-sm font-medium text-red-900 mb-1">
              Component Error
            </h3>
            <p className="text-sm text-red-700 mb-3">
              This component encountered an error and couldn't render properly.
            </p>
            <div className="flex space-x-2">
              <Button
                size="sm"
                variant="outline"
                onClick={this.handleReset}
                disabled={this.retryCount >= this.maxRetries}
              >
                <RefreshCw className="h-3 w-3 mr-1" />
                Retry ({this.maxRetries - this.retryCount} left)
              </Button>
              <Button
                size="sm"
                variant="outline"
                onClick={this.handleReportError}
              >
                <Bug className="h-3 w-3 mr-1" />
                Report
              </Button>
            </div>
          </div>
        </div>

        {/* Development details */}
        {process.env.NODE_ENV === 'development' && this.state.error && (
          <details className="mt-4 p-3 bg-white rounded border">
            <summary className="cursor-pointer text-sm font-medium text-red-900">
              Error Details (Development)
            </summary>
            <pre className="mt-2 text-xs text-red-800 overflow-auto max-h-40">
              {this.state.error.message}
              {this.state.error.stack && (
                <>
                  {'\n\n'}
                  {this.state.error.stack}
                </>
              )}
            </pre>
          </details>
        )}
      </Card>
    )
  }

  renderPageError() {
    return (
      <div className="min-h-screen bg-gray-50 flex flex-col justify-center py-12 sm:px-6 lg:px-8">
        <div className="sm:mx-auto sm:w-full sm:max-w-md">
          <div className="text-center">
            {/* Error Icon */}
            <div className="mx-auto flex items-center justify-center h-16 w-16 rounded-full bg-red-100 mb-6">
              <AlertTriangle className="h-8 w-8 text-red-600" />
            </div>

            {/* Content */}
            <h1 className="text-3xl font-bold text-gray-900 mb-4">
              Page Error
            </h1>

            <p className="text-lg text-gray-600 mb-8 max-w-md mx-auto">
              This page encountered an error while loading. Our team has been notified.
            </p>

            {/* Error ID */}
            {this.state.errorId && (
              <div className="bg-gray-100 rounded-lg p-3 mb-6 max-w-sm mx-auto">
                <p className="text-xs text-gray-600 mb-1">Error ID:</p>
                <code className="text-sm font-mono text-gray-900">{this.state.errorId}</code>
              </div>
            )}

            {/* Actions */}
            <div className="space-y-4 sm:space-y-0 sm:space-x-4 sm:flex sm:justify-center">
              <Button
                onClick={this.handleReset}
                variant="outline"
                disabled={this.retryCount >= this.maxRetries}
                className="w-full sm:w-auto flex items-center justify-center"
              >
                <RefreshCw className="h-4 w-4 mr-2" />
                Retry ({this.maxRetries - this.retryCount} left)
              </Button>

              <Button
                onClick={this.handleGoHome}
                className="w-full sm:w-auto flex items-center justify-center"
              >
                <Home className="h-4 w-4 mr-2" />
                Go to Dashboard
              </Button>

              <Button
                onClick={this.handleReportError}
                variant="outline"
                className="w-full sm:w-auto flex items-center justify-center"
              >
                <Send className="h-4 w-4 mr-2" />
                Report Error
              </Button>
            </div>
          </div>
        </div>
      </div>
    )
  }

  render() {
    if (this.state.hasError) {
      // Use custom fallback if provided
      if (this.props.fallback) {
        return this.props.fallback
      }

      // App level errors use server error page
      if (this.props.level === 'app') {
        return <ServerErrorPage error={this.state.error} resetError={this.handleReset} />
      }

      // Page level errors
      if (this.props.level === 'page') {
        return this.renderPageError()
      }

      // Component level errors (default)
      return this.renderComponentError()
    }

    return this.props.children
  }
}

export default ErrorBoundaryEnhanced

// Helper component for different error boundary levels
export const AppErrorBoundary: React.FC<{ children: ReactNode }> = ({ children }) => (
  <ErrorBoundaryEnhanced level="app">
    {children}
  </ErrorBoundaryEnhanced>
)

export const PageErrorBoundary: React.FC<{ children: ReactNode }> = ({ children }) => (
  <ErrorBoundaryEnhanced level="page">
    {children}
  </ErrorBoundaryEnhanced>
)

export const ComponentErrorBoundary: React.FC<{ children: ReactNode }> = ({ children }) => (
  <ErrorBoundaryEnhanced level="component">
    {children}
  </ErrorBoundaryEnhanced>
)

// Enhanced hook with error recovery
export const useErrorHandler = () => {
  const [error, setError] = React.useState<Error | null>(null)

  const captureError = React.useCallback((error: Error) => {
    setError(error)
  }, [])

  const resetError = React.useCallback(() => {
    setError(null)
  }, [])

  const handleAsyncError = React.useCallback((asyncFn: () => Promise<any>) => {
    return async (...args: any[]) => {
      try {
        return await asyncFn.apply(null, args)
      } catch (error) {
        captureError(error as Error)
      }
    }
  }, [captureError])

  React.useEffect(() => {
    if (error) {
      throw error
    }
  }, [error])

  return { captureError, resetError, handleAsyncError }
}