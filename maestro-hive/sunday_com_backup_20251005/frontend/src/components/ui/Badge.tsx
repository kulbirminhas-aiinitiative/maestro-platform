import { HTMLAttributes } from 'react'
import { cva, type VariantProps } from 'class-variance-authority'
import { cn } from '@/lib/utils'

const badgeVariants = cva(
  'inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-semibold transition-colors focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2',
  {
    variants: {
      variant: {
        default:
          'border-transparent bg-primary text-primary-foreground hover:bg-primary/80',
        secondary:
          'border-transparent bg-secondary text-secondary-foreground hover:bg-secondary/80',
        destructive:
          'border-transparent bg-destructive text-destructive-foreground hover:bg-destructive/80',
        outline: 'text-foreground',
        success:
          'border-transparent bg-success-100 text-success-800 hover:bg-success-200',
        warning:
          'border-transparent bg-warning-100 text-warning-800 hover:bg-warning-200',
        danger:
          'border-transparent bg-danger-100 text-danger-800 hover:bg-danger-200',
        info:
          'border-transparent bg-blue-100 text-blue-800 hover:bg-blue-200',
      },
      size: {
        default: 'px-2.5 py-0.5 text-xs',
        sm: 'px-2 py-0.5 text-xs',
        lg: 'px-3 py-1 text-sm',
      },
    },
    defaultVariants: {
      variant: 'default',
      size: 'default',
    },
  }
)

export interface BadgeProps
  extends HTMLAttributes<HTMLDivElement>,
    VariantProps<typeof badgeVariants> {
  icon?: React.ReactNode
}

function Badge({ className, variant, size, icon, children, ...props }: BadgeProps) {
  return (
    <div className={cn(badgeVariants({ variant, size }), className)} {...props}>
      {icon && <span className="mr-1">{icon}</span>}
      {children}
    </div>
  )
}

// Status Badge component for common status values
interface StatusBadgeProps {
  status: string
  variant?: 'default' | 'dot'
  className?: string
}

function StatusBadge({ status, variant = 'default', className }: StatusBadgeProps) {
  const getStatusVariant = (status: string) => {
    const lowerStatus = status.toLowerCase()
    if (lowerStatus.includes('done') || lowerStatus.includes('complete') || lowerStatus.includes('success')) {
      return 'success'
    }
    if (lowerStatus.includes('progress') || lowerStatus.includes('working') || lowerStatus.includes('active')) {
      return 'info'
    }
    if (lowerStatus.includes('blocked') || lowerStatus.includes('error') || lowerStatus.includes('failed')) {
      return 'danger'
    }
    if (lowerStatus.includes('pending') || lowerStatus.includes('waiting') || lowerStatus.includes('review')) {
      return 'warning'
    }
    return 'secondary'
  }

  const statusVariant = getStatusVariant(status)

  if (variant === 'dot') {
    const dotColors = {
      success: 'bg-success-500',
      info: 'bg-blue-500',
      danger: 'bg-danger-500',
      warning: 'bg-warning-500',
      secondary: 'bg-gray-500',
      default: 'bg-primary',
      destructive: 'bg-destructive',
      outline: 'bg-gray-500',
    }

    return (
      <div className={cn('flex items-center gap-2', className)}>
        <div className={cn('h-2 w-2 rounded-full', dotColors[statusVariant])} />
        <span className="text-sm text-foreground">{status}</span>
      </div>
    )
  }

  return (
    <Badge variant={statusVariant} className={className}>
      {status}
    </Badge>
  )
}

// Priority Badge component
interface PriorityBadgeProps {
  priority: 'low' | 'medium' | 'high' | 'urgent'
  className?: string
}

function PriorityBadge({ priority, className }: PriorityBadgeProps) {
  const priorityConfig = {
    low: { variant: 'success' as const, label: 'Low' },
    medium: { variant: 'warning' as const, label: 'Medium' },
    high: { variant: 'danger' as const, label: 'High' },
    urgent: { variant: 'destructive' as const, label: 'Urgent' },
  }

  const config = priorityConfig[priority]

  return (
    <Badge variant={config.variant} className={className}>
      {config.label}
    </Badge>
  )
}

export { Badge, StatusBadge, PriorityBadge, badgeVariants }