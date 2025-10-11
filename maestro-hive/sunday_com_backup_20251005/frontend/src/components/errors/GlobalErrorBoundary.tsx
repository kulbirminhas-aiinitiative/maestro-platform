import React, { Component, ReactNode } from 'react'
import { ErrorHandler } from '@/lib/error-handler'
import { Button } from '@/components/ui/Button'
import { Card } from '@/components/ui/Card'
import { AlertTriangle, RefreshCw, Home } from 'lucide-react'

interface Props {
  children: ReactNode
  fallback?: ReactNode
  onError?: (error: Error, errorInfo: any) => void
}

interface State {
  hasError: boolean
  error: Error | null
  errorId: string | null
}

export class GlobalErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props)
    this.state = {
      hasError: false,
      error: null,
      errorId: null,
    }
  }

  static getDerivedStateFromError(error: Error): State {
    return {
      hasError: true,
      error,
      errorId: `error-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
    }
  }

  componentDidCatch(error: Error, errorInfo: any) {
    // Handle the error using our error handler
    const errorHandler = ErrorHandler.createErrorBoundaryHandler('GlobalErrorBoundary')
    errorHandler(error, errorInfo)

    // Call custom error handler if provided
    if (this.props.onError) {
      this.props.onError(error, errorInfo)
    }
  }

  handleRetry = () => {
    this.setState({
      hasError: false,
      error: null,
      errorId: null,
    })
  }

  handleGoHome = () => {
    window.location.href = '/'
  }

  handleReload = () => {
    window.location.reload()
  }

  render() {
    if (this.state.hasError) {
      // Use custom fallback if provided
      if (this.props.fallback) {
        return this.props.fallback
      }

      // Default error UI
      return (
        <div className="min-h-screen bg-gray-50 flex items-center justify-center p-4">
          <Card className="max-w-md w-full p-8 text-center">
            <div className="mb-6">
              <AlertTriangle className="h-16 w-16 text-red-500 mx-auto mb-4" />
              <h1 className="text-2xl font-bold text-gray-900 mb-2">
                Something went wrong
              </h1>
              <p className="text-gray-600 mb-4">
                We're sorry, but something unexpected happened. Our team has been notified.
              </p>

              {/* Error details for development */}
              {process.env.NODE_ENV === 'development' && this.state.error && (
                <details className="text-left bg-gray-100 p-4 rounded-lg mb-4">
                  <summary className="cursor-pointer font-medium text-sm text-gray-700 mb-2">
                    Error Details (Development Only)
                  </summary>
                  <pre className="text-xs text-red-600 whitespace-pre-wrap break-words">
                    {this.state.error.message}
                    {'\n\n'}
                    {this.state.error.stack}
                  </pre>
                </details>
              )}

              <div className="text-xs text-gray-400 mb-6">
                Error ID: {this.state.errorId}
              </div>
            </div>

            <div className="space-y-3">
              <Button
                onClick={this.handleRetry}
                className="w-full flex items-center justify-center space-x-2"
              >
                <RefreshCw className="h-4 w-4" />
                <span>Try Again</span>
              </Button>

              <Button
                variant="outline"
                onClick={this.handleReload}
                className="w-full flex items-center justify-center space-x-2"
              >
                <RefreshCw className="h-4 w-4" />
                <span>Reload Page</span>
              </Button>

              <Button
                variant="ghost"
                onClick={this.handleGoHome}
                className="w-full flex items-center justify-center space-x-2"
              >
                <Home className="h-4 w-4" />
                <span>Go Home</span>
              </Button>
            </div>
          </Card>
        </div>
      )
    }

    return this.props.children
  }
}

/**
 * Higher-order component for adding error boundaries to components
 */
export const withErrorBoundary = <P extends object>(
  Component: React.ComponentType<P>,
  fallback?: ReactNode,
  onError?: (error: Error, errorInfo: any) => void
) => {
  const WithErrorBoundaryComponent = (props: P) => (
    <GlobalErrorBoundary fallback={fallback} onError={onError}>
      <Component {...props} />
    </GlobalErrorBoundary>
  )

  WithErrorBoundaryComponent.displayName = `withErrorBoundary(${Component.displayName || Component.name})`

  return WithErrorBoundaryComponent
}

/**
 * Hook for handling errors in functional components
 */
export const useErrorBoundary = () => {
  const [error, setError] = React.useState<Error | null>(null)

  const resetError = React.useCallback(() => {
    setError(null)
  }, [])

  const captureError = React.useCallback((error: Error) => {
    setError(error)
  }, [])

  React.useEffect(() => {
    if (error) {
      throw error
    }
  }, [error])

  return {
    captureError,
    resetError,
  }
}