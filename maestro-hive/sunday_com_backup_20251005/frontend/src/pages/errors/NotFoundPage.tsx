import React from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { Button } from '@/components/ui/Button'
import { Search, Home, ArrowLeft } from 'lucide-react'

export const NotFoundPage: React.FC = () => {
  const navigate = useNavigate()

  const handleGoBack = () => {
    if (window.history.length > 1) {
      navigate(-1)
    } else {
      navigate('/dashboard')
    }
  }

  return (
    <div className="min-h-screen bg-gray-50 flex flex-col justify-center py-12 sm:px-6 lg:px-8">
      <div className="sm:mx-auto sm:w-full sm:max-w-md">
        <div className="text-center">
          {/* 404 Animation */}
          <div className="mb-8">
            <div className="text-6xl font-bold text-gray-300 mb-4">404</div>
            <div className="w-24 h-1 bg-blue-500 mx-auto rounded-full"></div>
          </div>

          {/* Error Icon */}
          <div className="mx-auto flex items-center justify-center h-16 w-16 rounded-full bg-red-100 mb-6">
            <Search className="h-8 w-8 text-red-600" />
          </div>

          {/* Content */}
          <h1 className="text-3xl font-bold text-gray-900 mb-4">
            Page Not Found
          </h1>

          <p className="text-lg text-gray-600 mb-8 max-w-md mx-auto">
            Sorry, we couldn't find the page you're looking for. The page may have been moved,
            deleted, or the URL might be incorrect.
          </p>

          {/* Suggestions */}
          <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6 mb-8 max-w-md mx-auto">
            <h3 className="text-sm font-medium text-gray-900 mb-3">Here are some suggestions:</h3>
            <ul className="text-sm text-gray-600 space-y-2 text-left">
              <li>• Check the URL for typos</li>
              <li>• Use the navigation menu to find what you're looking for</li>
              <li>• Go back to the previous page</li>
              <li>• Visit our dashboard to start fresh</li>
            </ul>
          </div>

          {/* Actions */}
          <div className="space-y-4 sm:space-y-0 sm:space-x-4 sm:flex sm:justify-center">
            <Button
              onClick={handleGoBack}
              variant="outline"
              className="w-full sm:w-auto flex items-center justify-center"
            >
              <ArrowLeft className="h-4 w-4 mr-2" />
              Go Back
            </Button>

            <Link to="/dashboard">
              <Button className="w-full sm:w-auto flex items-center justify-center">
                <Home className="h-4 w-4 mr-2" />
                Go to Dashboard
              </Button>
            </Link>
          </div>

          {/* Help */}
          <div className="mt-8 text-center">
            <p className="text-sm text-gray-500">
              Still need help?{' '}
              <a
                href="mailto:support@sunday.com"
                className="font-medium text-blue-600 hover:text-blue-500"
              >
                Contact support
              </a>
            </p>
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

export default NotFoundPage