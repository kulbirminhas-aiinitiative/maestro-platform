import { forwardRef } from 'react'
import * as AvatarPrimitive from '@radix-ui/react-avatar'
import { cn, getInitials } from '@/lib/utils'

const Avatar = forwardRef<
  React.ElementRef<typeof AvatarPrimitive.Root>,
  React.ComponentPropsWithoutRef<typeof AvatarPrimitive.Root>
>(({ className, ...props }, ref) => (
  <AvatarPrimitive.Root
    ref={ref}
    className={cn(
      'relative flex h-10 w-10 shrink-0 overflow-hidden rounded-full',
      className
    )}
    {...props}
  />
))
Avatar.displayName = AvatarPrimitive.Root.displayName

const AvatarImage = forwardRef<
  React.ElementRef<typeof AvatarPrimitive.Image>,
  React.ComponentPropsWithoutRef<typeof AvatarPrimitive.Image>
>(({ className, ...props }, ref) => (
  <AvatarPrimitive.Image
    ref={ref}
    className={cn('aspect-square h-full w-full', className)}
    {...props}
  />
))
AvatarImage.displayName = AvatarPrimitive.Image.displayName

const AvatarFallback = forwardRef<
  React.ElementRef<typeof AvatarPrimitive.Fallback>,
  React.ComponentPropsWithoutRef<typeof AvatarPrimitive.Fallback>
>(({ className, ...props }, ref) => (
  <AvatarPrimitive.Fallback
    ref={ref}
    className={cn(
      'flex h-full w-full items-center justify-center rounded-full bg-muted',
      className
    )}
    {...props}
  />
))
AvatarFallback.displayName = AvatarPrimitive.Fallback.displayName

// Enhanced Avatar component with user data
interface UserAvatarProps {
  user?: {
    firstName?: string
    lastName?: string
    fullName?: string
    avatarUrl?: string
    email?: string
  }
  size?: 'sm' | 'md' | 'lg' | 'xl'
  className?: string
  showStatus?: boolean
  status?: 'online' | 'offline' | 'away' | 'busy'
}

const UserAvatar = forwardRef<HTMLDivElement, UserAvatarProps>(
  ({ user, size = 'md', className, showStatus = false, status = 'offline', ...props }, ref) => {
    const sizeClasses = {
      sm: 'h-6 w-6',
      md: 'h-10 w-10',
      lg: 'h-16 w-16',
      xl: 'h-24 w-24',
    }

    const statusClasses = {
      online: 'bg-green-500',
      offline: 'bg-gray-400',
      away: 'bg-yellow-500',
      busy: 'bg-red-500',
    }

    const displayName = user?.fullName || `${user?.firstName || ''} ${user?.lastName || ''}`.trim()
    const initials = getInitials(displayName || user?.email)

    return (
      <div ref={ref} className={cn('relative', className)} {...props}>
        <Avatar className={cn(sizeClasses[size])}>
          <AvatarImage src={user?.avatarUrl} alt={displayName || 'User avatar'} />
          <AvatarFallback className="text-sm font-medium">
            {initials}
          </AvatarFallback>
        </Avatar>
        {showStatus && (
          <div
            className={cn(
              'absolute -bottom-0.5 -right-0.5 h-3 w-3 rounded-full border-2 border-background',
              statusClasses[status]
            )}
          />
        )}
      </div>
    )
  }
)
UserAvatar.displayName = 'UserAvatar'

export { Avatar, AvatarImage, AvatarFallback, UserAvatar }