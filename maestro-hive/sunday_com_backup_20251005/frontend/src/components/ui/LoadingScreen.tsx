import { motion } from 'framer-motion'
import { APP_NAME } from '@/lib/constants'

interface LoadingScreenProps {
  message?: string
  size?: 'sm' | 'md' | 'lg'
}

export function LoadingScreen({ message = 'Loading...', size = 'md' }: LoadingScreenProps) {
  const sizes = {
    sm: 'h-6 w-6',
    md: 'h-10 w-10',
    lg: 'h-16 w-16',
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-background">
      <div className="flex flex-col items-center space-y-4">
        {/* Logo */}
        <motion.div
          initial={{ opacity: 0, scale: 0.5 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ duration: 0.5 }}
          className="flex items-center space-x-2"
        >
          <div className="h-12 w-12 rounded-lg bg-gradient-to-br from-primary to-primary/70 flex items-center justify-center">
            <span className="text-white font-bold text-xl">S</span>
          </div>
          <span className="text-2xl font-bold text-foreground">{APP_NAME}</span>
        </motion.div>

        {/* Loading spinner */}
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.2, duration: 0.3 }}
          className="flex flex-col items-center space-y-3"
        >
          <div className={`${sizes[size]} relative`}>
            <div className="absolute inset-0 rounded-full border-4 border-muted animate-pulse" />
            <div className="absolute inset-0 rounded-full border-4 border-primary border-t-transparent animate-spin" />
          </div>
          <p className="text-muted-foreground text-sm font-medium">{message}</p>
        </motion.div>
      </div>
    </div>
  )
}

// Inline loading spinner for use within components
export function LoadingSpinner({ size = 'sm', className = '' }: { size?: 'sm' | 'md' | 'lg', className?: string }) {
  const sizes = {
    sm: 'h-4 w-4',
    md: 'h-6 w-6',
    lg: 'h-8 w-8',
  }

  return (
    <div className={`relative ${sizes[size]} ${className}`}>
      <div className="absolute inset-0 rounded-full border-2 border-muted/50" />
      <div className="absolute inset-0 rounded-full border-2 border-primary border-t-transparent animate-spin" />
    </div>
  )
}

// Skeleton loading components
export function SkeletonLoader({ className = '' }: { className?: string }) {
  return (
    <div className={`animate-pulse bg-muted rounded ${className}`} />
  )
}

export function CardSkeleton() {
  return (
    <div className="p-6 space-y-4 border rounded-lg bg-card">
      <div className="space-y-2">
        <SkeletonLoader className="h-4 w-3/4" />
        <SkeletonLoader className="h-4 w-1/2" />
      </div>
      <div className="space-y-2">
        <SkeletonLoader className="h-3 w-full" />
        <SkeletonLoader className="h-3 w-full" />
        <SkeletonLoader className="h-3 w-2/3" />
      </div>
    </div>
  )
}

export function TableSkeleton({ rows = 5, columns = 4 }: { rows?: number, columns?: number }) {
  return (
    <div className="space-y-3">
      {/* Header */}
      <div className="flex space-x-4 p-4 border-b">
        {Array.from({ length: columns }).map((_, i) => (
          <SkeletonLoader key={i} className="h-4 flex-1" />
        ))}
      </div>
      {/* Rows */}
      {Array.from({ length: rows }).map((_, i) => (
        <div key={i} className="flex space-x-4 p-4">
          {Array.from({ length: columns }).map((_, j) => (
            <SkeletonLoader key={j} className="h-4 flex-1" />
          ))}
        </div>
      ))}
    </div>
  )
}

export default LoadingScreen
