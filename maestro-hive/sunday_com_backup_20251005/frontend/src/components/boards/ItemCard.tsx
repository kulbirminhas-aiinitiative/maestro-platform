import React from 'react'
import { Item } from '@/types'
import { Card } from '@/components/ui/Card'
import { Badge } from '@/components/ui/Badge'
import { Avatar } from '@/components/ui/Avatar'
import { Button } from '@/components/ui/Button'
import {
  Calendar,
  MessageCircle,
  Paperclip,
  Clock,
  Flag,
  MoreHorizontal,
  CheckCircle2,
  Circle,
} from 'lucide-react'
import { format, isToday, isTomorrow, isPast } from 'date-fns'
import clsx from 'clsx'

interface ItemCardProps {
  item: Item
  isSelected?: boolean
  onSelect?: (event: React.MouseEvent) => void
  onEdit?: () => void
  className?: string
}

export const ItemCard: React.FC<ItemCardProps> = ({
  item,
  isSelected = false,
  onSelect,
  onEdit,
  className,
}) => {
  const dueDate = item.data?.dueDate ? new Date(item.data.dueDate) : null
  const priority = item.data?.priority || 'medium'
  const status = item.data?.status || 'todo'
  const progress = item.data?.progress || 0

  const getDueDateColor = (date: Date) => {
    if (isPast(date) && !isToday(date)) {
      return 'text-red-600 bg-red-50'
    }
    if (isToday(date)) {
      return 'text-orange-600 bg-orange-50'
    }
    if (isTomorrow(date)) {
      return 'text-yellow-600 bg-yellow-50'
    }
    return 'text-gray-600 bg-gray-50'
  }

  const formatDueDate = (date: Date) => {
    if (isToday(date)) return 'Today'
    if (isTomorrow(date)) return 'Tomorrow'
    return format(date, 'MMM d')
  }

  const getPriorityColor = (priority: string) => {
    switch (priority) {
      case 'high':
        return 'text-red-600'
      case 'medium':
        return 'text-yellow-600'
      case 'low':
        return 'text-green-600'
      default:
        return 'text-gray-600'
    }
  }

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'done':
        return <CheckCircle2 className="h-4 w-4 text-green-600" />
      case 'in_progress':
        return <Clock className="h-4 w-4 text-blue-600" />
      default:
        return <Circle className="h-4 w-4 text-gray-400" />
    }
  }

  return (
    <Card
      className={clsx(
        'p-4 cursor-pointer transition-all duration-200 hover:shadow-md group',
        isSelected && 'ring-2 ring-blue-500 shadow-md',
        className
      )}
      onClick={onSelect}
    >
      <div className="space-y-3">
        {/* Header */}
        <div className="flex items-start justify-between">
          <div className="flex items-center space-x-2">
            {getStatusIcon(status)}
            <h4 className="font-medium text-gray-900 line-clamp-2 flex-1">
              {item.name}
            </h4>
          </div>

          <div className="flex items-center space-x-1 opacity-0 group-hover:opacity-100 transition-opacity">
            {priority === 'high' && (
              <Flag className={clsx('h-4 w-4', getPriorityColor(priority))} />
            )}
            <Button
              size="sm"
              variant="ghost"
              onClick={(e) => {
                e.stopPropagation()
                onEdit?.()
              }}
              className="h-6 w-6 p-0"
            >
              <MoreHorizontal className="h-3 w-3" />
            </Button>
          </div>
        </div>

        {/* Description */}
        {item.description && (
          <p className="text-sm text-gray-600 line-clamp-3">
            {item.description}
          </p>
        )}

        {/* Progress Bar */}
        {progress > 0 && (
          <div className="space-y-1">
            <div className="flex items-center justify-between text-xs text-gray-500">
              <span>Progress</span>
              <span>{progress}%</span>
            </div>
            <div className="h-1.5 bg-gray-200 rounded-full overflow-hidden">
              <div
                className="h-full bg-blue-500 transition-all duration-300"
                style={{ width: `${progress}%` }}
              />
            </div>
          </div>
        )}

        {/* Tags/Labels */}
        {item.data?.labels && item.data.labels.length > 0 && (
          <div className="flex flex-wrap gap-1">
            {item.data.labels.slice(0, 3).map((label: string, index: number) => (
              <Badge
                key={index}
                variant="secondary"
                className="text-xs px-2 py-0.5"
              >
                {label}
              </Badge>
            ))}
            {item.data.labels.length > 3 && (
              <Badge variant="outline" className="text-xs px-2 py-0.5">
                +{item.data.labels.length - 3}
              </Badge>
            )}
          </div>
        )}

        {/* Footer */}
        <div className="flex items-center justify-between text-xs text-gray-500">
          <div className="flex items-center space-x-3">
            {/* Comments count */}
            {(item._count?.comments || 0) > 0 && (
              <div className="flex items-center space-x-1">
                <MessageCircle className="h-3 w-3" />
                <span>{item._count?.comments}</span>
              </div>
            )}

            {/* Attachments count */}
            {(item.attachments?.length || 0) > 0 && (
              <div className="flex items-center space-x-1">
                <Paperclip className="h-3 w-3" />
                <span>{item.attachments?.length}</span>
              </div>
            )}

            {/* Subtasks count */}
            {(item._count?.children || 0) > 0 && (
              <div className="flex items-center space-x-1">
                <span>📋</span>
                <span>{item._count?.children}</span>
              </div>
            )}

            {/* Time tracking */}
            {(item.timeEntries?.length || 0) > 0 && (
              <div className="flex items-center space-x-1">
                <Clock className="h-3 w-3" />
                <span>{item.timeEntries?.length}</span>
              </div>
            )}
          </div>

          <div className="flex items-center space-x-2">
            {/* Due date */}
            {dueDate && (
              <div className={clsx(
                'flex items-center space-x-1 px-2 py-1 rounded text-xs',
                getDueDateColor(dueDate)
              )}>
                <Calendar className="h-3 w-3" />
                <span>{formatDueDate(dueDate)}</span>
              </div>
            )}

            {/* Assignees */}
            {item.assignees && item.assignees.length > 0 && (
              <div className="flex -space-x-1">
                {item.assignees.slice(0, 3).map((assignee, index) => (
                  <Avatar
                    key={assignee.id}
                    src={assignee.avatarUrl}
                    alt={assignee.fullName}
                    size="xs"
                    className="ring-1 ring-white"
                  />
                ))}
                {item.assignees.length > 3 && (
                  <div className="flex items-center justify-center w-5 h-5 bg-gray-100 rounded-full ring-1 ring-white text-xs font-medium text-gray-600">
                    +{item.assignees.length - 3}
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      </div>
    </Card>
  )
}