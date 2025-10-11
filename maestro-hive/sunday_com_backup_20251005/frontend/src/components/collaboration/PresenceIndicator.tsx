import React from 'react'
import { Avatar } from '@/components/ui/Avatar'
import { Badge } from '@/components/ui/Badge'
import { useBoardPresence } from '@/hooks/useWebSocket'
import { Wifi, WifiOff } from 'lucide-react'
import clsx from 'clsx'

interface PresenceIndicatorProps {
  boardId: string
  className?: string
  presenceUsers?: Array<{
    userId: string
    username: string
    avatarUrl?: string
    lastSeen: string
  }>
}

export const PresenceIndicator: React.FC<PresenceIndicatorProps> = ({
  boardId,
  className,
  presenceUsers: propsPresenceUsers,
}) => {
  const { isConnected, presenceUsers: hookPresenceUsers, cursors } = useBoardPresence(boardId)

  // Use presence users from props if provided, otherwise use from hook
  const presenceUsers = propsPresenceUsers || hookPresenceUsers

  return (
    <div className={clsx('flex items-center space-x-3', className)}>
      {/* Connection Status - Only show if not provided via props */}
      {!propsPresenceUsers && (
        <div className="flex items-center space-x-1">
          {isConnected ? (
            <div className="flex items-center space-x-1 text-green-600">
              <Wifi className="h-4 w-4" />
              <span className="text-xs font-medium">Live</span>
            </div>
          ) : (
            <div className="flex items-center space-x-1 text-red-600">
              <WifiOff className="h-4 w-4" />
              <span className="text-xs font-medium">Offline</span>
            </div>
          )}
        </div>
      )}

      {/* Active Users */}
      {presenceUsers.length > 0 && (
        <div className="flex items-center space-x-2">
          <div className="flex -space-x-1">
            {presenceUsers.slice(0, 5).map((user, index) => (
              <div
                key={user.userId}
                className="relative"
                title={`${user.username} is viewing this board`}
              >
                <Avatar
                  src={user.avatarUrl}
                  alt={user.username}
                  size="sm"
                  className="ring-2 ring-white"
                />
                {/* Online indicator */}
                <div className="absolute -bottom-0.5 -right-0.5 w-3 h-3 bg-green-400 rounded-full ring-2 ring-white" />
              </div>
            ))}
            {presenceUsers.length > 5 && (
              <div className="flex items-center justify-center w-8 h-8 bg-gray-100 rounded-full ring-2 ring-white text-xs font-medium text-gray-600">
                +{presenceUsers.length - 5}
              </div>
            )}
          </div>

          <Badge variant="outline" className="text-xs">
            {presenceUsers.length} viewing
          </Badge>
        </div>
      )}

      {/* Collaborative Cursors */}
      <CollaborativeCursors cursors={cursors} />
    </div>
  )
}

interface CollaborativeCursorsProps {
  cursors: Array<{
    userId: string
    username: string
    x: number
    y: number
    timestamp: string
  }>
}

const CollaborativeCursors: React.FC<CollaborativeCursorsProps> = ({ cursors }) => {
  if (cursors.length === 0) return null

  return (
    <div className="fixed inset-0 pointer-events-none z-50">
      {cursors.map((cursor) => (
        <CollaborativeCursor
          key={cursor.userId}
          cursor={cursor}
        />
      ))}
    </div>
  )
}

interface CollaborativeCursorProps {
  cursor: {
    userId: string
    username: string
    x: number
    y: number
    timestamp: string
  }
}

const CollaborativeCursor: React.FC<CollaborativeCursorProps> = ({ cursor }) => {
  // Generate a consistent color for this user
  const getColorForUser = (userId: string) => {
    const colors = [
      'bg-red-500',
      'bg-blue-500',
      'bg-green-500',
      'bg-yellow-500',
      'bg-purple-500',
      'bg-pink-500',
      'bg-indigo-500',
      'bg-orange-500',
    ]
    const hash = userId.split('').reduce((a, b) => {
      a = ((a << 5) - a) + b.charCodeAt(0)
      return a & a
    }, 0)
    return colors[Math.abs(hash) % colors.length]
  }

  const colorClass = getColorForUser(cursor.userId)

  return (
    <div
      className="absolute transition-all duration-100 ease-out"
      style={{
        left: cursor.x,
        top: cursor.y,
        transform: 'translate(-2px, -2px)',
      }}
    >
      {/* Cursor pointer */}
      <svg
        width="16"
        height="16"
        viewBox="0 0 16 16"
        fill="none"
        className={clsx('drop-shadow-sm', colorClass)}
      >
        <path
          d="M0 0L0 11L4 7L7 7L0 0Z"
          fill="currentColor"
        />
      </svg>

      {/* Username label */}
      <div
        className={clsx(
          'absolute top-4 left-2 px-2 py-1 rounded text-white text-xs font-medium whitespace-nowrap',
          colorClass
        )}
      >
        {cursor.username}
      </div>
    </div>
  )
}