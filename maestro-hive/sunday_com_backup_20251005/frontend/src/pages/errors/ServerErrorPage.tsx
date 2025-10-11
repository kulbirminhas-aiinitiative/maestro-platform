import React from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { Button } from '@/components/ui/Button'
import { AlertTriangle, RefreshCw, Home, ArrowLeft } from 'lucide-react'

interface ServerErrorPageProps {
  error?: Error | null
  resetError?: () => void
}

export const ServerErrorPage: React.FC<ServerErrorPageProps> = ({
  error,
  resetError,
}) => {
  const navigate = useNavigate()

  const handleGoBack = () => {
    if (window.history.length > 1) {
      navigate(-1)
    } else {
      navigate('/dashboard')
    }
  }

  const handleRetry = () => {
    if (resetError) {
      resetError()
    } else {
      window.location.reload()
    }
  }

  return (
    <div className="min-h-screen bg-gray-50 flex flex-col justify-center py-12 sm:px-6 lg:px-8">
      <div className="sm:mx-auto sm:w-full sm:max-w-md">
        <div className="text-center">
          {/* 500 Animation */}
          <div className="mb-8">
            <div className="text-6xl font-bold text-gray-300 mb-4">500</div>
            <div className="w-24 h-1 bg-red-500 mx-auto rounded-full"></div>
          </div>

          {/* Error Icon */}
          <div className="mx-auto flex items-center justify-center h-16 w-16 rounded-full bg-red-100 mb-6">
            <AlertTriangle className="h-8 w-8 text-red-600" />
          </div>

          {/* Content */}
          <h1 className="text-3xl font-bold text-gray-900 mb-4">
            Something went wrong
          </h1>

          <p className="text-lg text-gray-600 mb-8 max-w-md mx-auto">
            We're experiencing some technical difficulties. Our team has been notified and
            is working to fix the issue.
          </p>

          {/* Error Details (only in development) */}
          {process.env.NODE_ENV === 'development' && error && (
            <div className="bg-red-50 border border-red-200 rounded-lg p-4 mb-8 max-w-lg mx-auto text-left">
              <h3 className="text-sm font-medium text-red-800 mb-2">Error Details:</h3>
              <pre className="text-xs text-red-700 overflow-auto max-h-32">
                {error.message}
                {error.stack && (
                  <>
                    {'\n\n'}
                    {error.stack}
                  </>
                )}
              </pre>
            </div>
          )}

          {/* Suggestions */}
          <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6 mb-8 max-w-md mx-auto">
            <h3 className="text-sm font-medium text-gray-900 mb-3">What you can try:</h3>
            <ul className="text-sm text-gray-600 space-y-2 text-left">
              <li>• Refresh the page</li>
              <li>• Check your internet connection</li>
              <li>• Try again in a few minutes</li>
              <li>• Clear your browser cache</li>
            </ul>
          </div>

          {/* Actions */}
          <div className="space-y-4 sm:space-y-0 sm:space-x-4 sm:flex sm:justify-center">
            <Button
              onClick={handleRetry}
              className="w-full sm:w-auto flex items-center justify-center"
            >
              <RefreshCw className="h-4 w-4 mr-2" />
              Try Again
            </Button>

            <Button
              onClick={handleGoBack}
              variant="outline"
              className="w-full sm:w-auto flex items-center justify-center"
            >
              <ArrowLeft className="h-4 w-4 mr-2" />
              Go Back
            </Button>

            <Link to="/dashboard">
              <Button
                variant="outline"
                className="w-full sm:w-auto flex items-center justify-center"
              >
                <Home className="h-4 w-4 mr-2" />
                Dashboard
              </Button>
            </Link>
          </div>

          {/* Help */}
          <div className="mt-8 text-center">
            <p className="text-sm text-gray-500">
              If the problem persists,{' '}
              <a
                href="mailto:support@sunday.com"
                className="font-medium text-blue-600 hover:text-blue-500"
              >
                contact our support team
              </a>
            </p>
          </div>

          {/* Status Page Link */}
          <div className="mt-4 text-center">
            <a
              href="https://status.sunday.com"
              target="_blank"
              rel="noopener noreferrer"
              className="text-sm text-gray-400 hover:text-gray-600"
            >
              Check our status page
            </a>
          </div>
        </div>
      </div>

      {/* Footer */}
      <div className="mt-16 text-center text-xs text-gray-400">
        <p>&copy; 2024 Sunday.com. All rights reserved.</p>
      </div>
    </div>
  )
}

export default ServerErrorPage