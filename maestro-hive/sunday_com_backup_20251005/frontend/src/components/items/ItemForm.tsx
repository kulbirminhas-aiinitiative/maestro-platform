import React, { useEffect, useState } from 'react'
import { useForm, Controller } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { Item, CreateItemData, UpdateItemData, User } from '@/types'
import { useItemStore } from '@/stores/item.store'
import { useBoardStore } from '@/stores/board.store'
import { Button } from '@/components/ui/Button'
import { Input } from '@/components/ui/Input'
import { Card } from '@/components/ui/Card'
import { Badge } from '@/components/ui/Badge'
import { Avatar } from '@/components/ui/Avatar'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from '@/components/ui/Dialog'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/Select'
import { X, Calendar, User as UserIcon, Flag, Tag } from 'lucide-react'
import { format } from 'date-fns'
import clsx from 'clsx'
import { TimeTracker } from '@/components/time/TimeTracker'

const itemSchema = z.object({
  name: z.string()
    .min(1, 'Name is required')
    .max(255, 'Name must not exceed 255 characters')
    .refine(val => val.trim().length > 0, 'Name cannot be empty'),
  description: z.string()
    .max(5000, 'Description must not exceed 5000 characters')
    .optional(),
  status: z.string().optional(),
  priority: z.enum(['low', 'medium', 'high'], {
    errorMap: () => ({ message: 'Priority must be low, medium, or high' })
  }).optional(),
  dueDate: z.string()
    .optional()
    .refine(val => !val || !isNaN(Date.parse(val)), 'Invalid date format'),
  assigneeIds: z.array(z.string().uuid('Invalid assignee ID')).optional(),
  labels: z.array(z.string().min(1).max(50)).max(10, 'Maximum 10 labels allowed').optional(),
  progress: z.number()
    .min(0, 'Progress cannot be negative')
    .max(100, 'Progress cannot exceed 100%')
    .optional(),
})

type ItemFormData = z.infer<typeof itemSchema>

interface ItemFormProps {
  isOpen: boolean
  onClose: () => void
  boardId: string
  columnId?: string | null
  item?: Item | null
}

export const ItemForm: React.FC<ItemFormProps> = ({
  isOpen,
  onClose,
  boardId,
  columnId,
  item,
}) => {
  const [newLabel, setNewLabel] = useState('')
  const [showLabelInput, setShowLabelInput] = useState(false)
  const [isDirty, setIsDirty] = useState(false)
  const [saveStatus, setSaveStatus] = useState<'idle' | 'saving' | 'saved' | 'error'>('idle')

  const { createItem, updateItem, loading } = useItemStore()
  const { columns, currentBoard } = useBoardStore()

  const isEditing = !!item

  const {
    register,
    handleSubmit,
    control,
    watch,
    setValue,
    reset,
    formState: { errors, isSubmitting },
  } = useForm<ItemFormData>({
    resolver: zodResolver(itemSchema),
    defaultValues: {
      name: '',
      description: '',
      status: 'todo',
      priority: 'medium',
      assigneeIds: [],
      labels: [],
      progress: 0,
    },
  })

  const watchedLabels = watch('labels') || []
  const watchedAssigneeIds = watch('assigneeIds') || []
  const watchedValues = watch()

  // Track form changes for dirty state
  useEffect(() => {
    const subscription = watch((value, { name, type }) => {
      if (type === 'change') {
        setIsDirty(true)
        setSaveStatus('idle')
      }
    })
    return () => subscription.unsubscribe()
  }, [watch])

  // Reset form when item changes
  useEffect(() => {
    if (item) {
      reset({
        name: item.name,
        description: item.description || '',
        status: item.data?.status || 'todo',
        priority: item.data?.priority || 'medium',
        dueDate: item.data?.dueDate ? format(new Date(item.data.dueDate), 'yyyy-MM-dd') : '',
        assigneeIds: item.assignees?.map(a => a.id) || [],
        labels: item.data?.labels || [],
        progress: item.data?.progress || 0,
      })
    } else {
      reset({
        name: '',
        description: '',
        status: getColumnStatus(),
        priority: 'medium',
        assigneeIds: [],
        labels: [],
        progress: 0,
      })
    }
  }, [item, reset])

  const getColumnStatus = () => {
    if (columnId) {
      const column = columns.find(col => col.id === columnId)
      if (column?.columnType === 'status') {
        return column.settings?.statusValue || 'todo'
      }
    }
    return 'todo'
  }

  const onSubmit = async (data: ItemFormData) => {
    try {
      setSaveStatus('saving')

      const itemData = {
        status: data.status,
        priority: data.priority,
        dueDate: data.dueDate || null,
        labels: data.labels,
        progress: data.progress,
      }

      if (isEditing && item) {
        const updateData: UpdateItemData = {
          name: data.name,
          description: data.description,
          itemData,
          assigneeIds: data.assigneeIds,
        }
        await updateItem(item.id, updateData)
      } else {
        const createData: CreateItemData = {
          name: data.name,
          description: data.description,
          boardId,
          itemData,
          assigneeIds: data.assigneeIds,
        }
        await createItem(boardId, createData)
      }

      setSaveStatus('saved')
      setIsDirty(false)

      // Close after a brief delay to show success state
      setTimeout(() => {
        onClose()
      }, 500)
    } catch (error) {
      console.error('Failed to save item:', error)
      setSaveStatus('error')
    }
  }

  // Auto-save for edits (draft functionality)
  useEffect(() => {
    if (!isEditing || !isDirty) return

    const autoSaveTimer = setTimeout(() => {
      if (isDirty && saveStatus === 'idle') {
        handleSubmit(onSubmit)()
      }
    }, 3000) // Auto-save after 3 seconds of inactivity

    return () => clearTimeout(autoSaveTimer)
  }, [isDirty, isEditing, saveStatus, handleSubmit])

  // Warn before closing if there are unsaved changes
  const handleClose = () => {
    if (isDirty && saveStatus !== 'saved') {
      if (window.confirm('You have unsaved changes. Are you sure you want to close?')) {
        onClose()
      }
    } else {
      onClose()
    }
  }

  // Keyboard shortcuts
  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      // Ctrl/Cmd + S to save
      if ((event.ctrlKey || event.metaKey) && event.key === 's') {
        event.preventDefault()
        handleSubmit(onSubmit)()
      }
      // Escape to close
      if (event.key === 'Escape') {
        event.preventDefault()
        handleClose()
      }
    }

    if (isOpen) {
      document.addEventListener('keydown', handleKeyDown)
    }

    return () => {
      document.removeEventListener('keydown', handleKeyDown)
    }
  }, [isOpen, handleSubmit, handleClose])

  const handleAddLabel = () => {
    if (newLabel.trim() && !watchedLabels.includes(newLabel.trim())) {
      setValue('labels', [...watchedLabels, newLabel.trim()])
      setNewLabel('')
      setShowLabelInput(false)
    }
  }

  const handleRemoveLabel = (labelToRemove: string) => {
    setValue('labels', watchedLabels.filter(label => label !== labelToRemove))
  }

  const statusOptions = [
    { value: 'todo', label: 'To Do', color: 'bg-gray-100 text-gray-800' },
    { value: 'in_progress', label: 'In Progress', color: 'bg-blue-100 text-blue-800' },
    { value: 'review', label: 'Review', color: 'bg-yellow-100 text-yellow-800' },
    { value: 'done', label: 'Done', color: 'bg-green-100 text-green-800' },
  ]

  const priorityOptions = [
    { value: 'low', label: 'Low', color: 'text-green-600' },
    { value: 'medium', label: 'Medium', color: 'text-yellow-600' },
    { value: 'high', label: 'High', color: 'text-red-600' },
  ]

  return (
    <Dialog open={isOpen} onOpenChange={onClose}>
      <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-3">
              <DialogTitle>
                {isEditing ? 'Edit Item' : 'Create New Item'}
              </DialogTitle>

              {/* Save Status Indicator */}
              {isEditing && (
                <div className="flex items-center space-x-2 text-sm">
                  {saveStatus === 'saving' && (
                    <div className="flex items-center space-x-1 text-blue-600">
                      <div className="animate-spin rounded-full h-3 w-3 border-b-2 border-blue-600"></div>
                      <span>Saving...</span>
                    </div>
                  )}
                  {saveStatus === 'saved' && (
                    <div className="flex items-center space-x-1 text-green-600">
                      <div className="w-3 h-3 rounded-full bg-green-600"></div>
                      <span>Saved</span>
                    </div>
                  )}
                  {saveStatus === 'error' && (
                    <div className="flex items-center space-x-1 text-red-600">
                      <div className="w-3 h-3 rounded-full bg-red-600"></div>
                      <span>Error saving</span>
                    </div>
                  )}
                  {isDirty && saveStatus === 'idle' && (
                    <div className="flex items-center space-x-1 text-yellow-600">
                      <div className="w-3 h-3 rounded-full bg-yellow-600"></div>
                      <span>Unsaved changes</span>
                    </div>
                  )}
                </div>
              )}
            </div>

            <Button
              variant="ghost"
              size="sm"
              onClick={handleClose}
              className="absolute right-4 top-4"
            >
              <X className="h-4 w-4" />
            </Button>
          </div>
        </DialogHeader>

        <form onSubmit={handleSubmit(onSubmit)} className="space-y-6">
          {/* Name */}
          <div className="space-y-2">
            <label htmlFor="name" className="text-sm font-medium text-gray-900">
              Name *
            </label>
            <Input
              id="name"
              {...register('name')}
              placeholder="Enter item name..."
              className={clsx(errors.name && 'border-red-500')}
            />
            {errors.name && (
              <p className="text-sm text-red-600">{errors.name.message}</p>
            )}
          </div>

          {/* Description */}
          <div className="space-y-2">
            <label htmlFor="description" className="text-sm font-medium text-gray-900">
              Description
            </label>
            <textarea
              id="description"
              {...register('description')}
              rows={3}
              placeholder="Enter item description..."
              className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500"
            />
          </div>

          {/* Status and Priority */}
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <label className="text-sm font-medium text-gray-900">Status</label>
              <Controller
                name="status"
                control={control}
                render={({ field }) => (
                  <Select value={field.value} onValueChange={field.onChange}>
                    <SelectTrigger className="w-full">
                      <SelectValue placeholder="Select status" />
                    </SelectTrigger>
                    <SelectContent>
                      {statusOptions.map((option) => (
                        <SelectItem key={option.value} value={option.value}>
                          <div className="flex items-center space-x-2">
                            <Badge className={clsx('text-xs', option.color)}>
                              {option.label}
                            </Badge>
                          </div>
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                )}
              />
            </div>

            <div className="space-y-2">
              <label className="text-sm font-medium text-gray-900">Priority</label>
              <Controller
                name="priority"
                control={control}
                render={({ field }) => (
                  <Select value={field.value} onValueChange={field.onChange}>
                    <SelectTrigger className="w-full">
                      <SelectValue placeholder="Select priority" />
                    </SelectTrigger>
                    <SelectContent>
                      {priorityOptions.map((option) => (
                        <SelectItem key={option.value} value={option.value}>
                          <div className="flex items-center space-x-2">
                            <Flag className={clsx('h-4 w-4', option.color)} />
                            <span>{option.label}</span>
                          </div>
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                )}
              />
            </div>
          </div>

          {/* Due Date and Progress */}
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <label htmlFor="dueDate" className="text-sm font-medium text-gray-900">
                Due Date
              </label>
              <div className="relative">
                <Input
                  id="dueDate"
                  type="date"
                  {...register('dueDate')}
                  className="pl-10"
                />
                <Calendar className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-400" />
              </div>
            </div>

            <div className="space-y-2">
              <label htmlFor="progress" className="text-sm font-medium text-gray-900">
                Progress (%)
              </label>
              <Input
                id="progress"
                type="number"
                min="0"
                max="100"
                {...register('progress', { valueAsNumber: true })}
                placeholder="0"
              />
            </div>
          </div>

          {/* Labels */}
          <div className="space-y-2">
            <label className="text-sm font-medium text-gray-900">Labels</label>
            <div className="space-y-3">
              {/* Existing labels */}
              {watchedLabels.length > 0 && (
                <div className="flex flex-wrap gap-2">
                  {watchedLabels.map((label, index) => (
                    <Badge
                      key={index}
                      variant="secondary"
                      className="flex items-center space-x-1"
                    >
                      <span>{label}</span>
                      <button
                        type="button"
                        onClick={() => handleRemoveLabel(label)}
                        className="ml-1 text-gray-500 hover:text-gray-700"
                      >
                        <X className="h-3 w-3" />
                      </button>
                    </Badge>
                  ))}
                </div>
              )}

              {/* Add label */}
              {showLabelInput ? (
                <div className="flex items-center space-x-2">
                  <Input
                    value={newLabel}
                    onChange={(e) => setNewLabel(e.target.value)}
                    placeholder="Enter label..."
                    className="flex-1"
                    onKeyPress={(e) => {
                      if (e.key === 'Enter') {
                        e.preventDefault()
                        handleAddLabel()
                      }
                    }}
                  />
                  <Button
                    type="button"
                    size="sm"
                    onClick={handleAddLabel}
                    disabled={!newLabel.trim()}
                  >
                    Add
                  </Button>
                  <Button
                    type="button"
                    size="sm"
                    variant="outline"
                    onClick={() => {
                      setShowLabelInput(false)
                      setNewLabel('')
                    }}
                  >
                    Cancel
                  </Button>
                </div>
              ) : (
                <Button
                  type="button"
                  size="sm"
                  variant="outline"
                  onClick={() => setShowLabelInput(true)}
                  className="flex items-center space-x-1"
                >
                  <Tag className="h-4 w-4" />
                  <span>Add Label</span>
                </Button>
              )}
            </div>
          </div>

          {/* Assignees */}
          <div className="space-y-2">
            <label className="text-sm font-medium text-gray-900">Assignees</label>
            <div className="space-y-3">
              {/* Selected assignees */}
              {watchedAssigneeIds.length > 0 && (
                <div className="flex flex-wrap gap-2">
                  {watchedAssigneeIds.map((assigneeId) => {
                    const member = currentBoard?.members?.find(m => m.user.id === assigneeId)
                    if (!member) return null

                    return (
                      <div
                        key={assigneeId}
                        className="flex items-center space-x-2 bg-gray-100 rounded-full px-3 py-1"
                      >
                        <Avatar
                          src={member.user.avatarUrl}
                          alt={member.user.fullName}
                          size="xs"
                        />
                        <span className="text-sm text-gray-900">
                          {member.user.fullName}
                        </span>
                        <button
                          type="button"
                          onClick={() => {
                            setValue('assigneeIds', watchedAssigneeIds.filter(id => id !== assigneeId))
                          }}
                          className="text-gray-500 hover:text-gray-700"
                        >
                          <X className="h-3 w-3" />
                        </button>
                      </div>
                    )
                  })}
                </div>
              )}

              {/* Available members */}
              {currentBoard?.members && (
                <div className="space-y-2">
                  <p className="text-sm text-gray-600">Available members:</p>
                  <div className="flex flex-wrap gap-2">
                    {currentBoard.members
                      .filter(member => !watchedAssigneeIds.includes(member.user.id))
                      .map((member) => (
                        <button
                          key={member.user.id}
                          type="button"
                          onClick={() => {
                            setValue('assigneeIds', [...watchedAssigneeIds, member.user.id])
                          }}
                          className="flex items-center space-x-2 bg-white border border-gray-300 rounded-full px-3 py-1 hover:bg-gray-50"
                        >
                          <Avatar
                            src={member.user.avatarUrl}
                            alt={member.user.fullName}
                            size="xs"
                          />
                          <span className="text-sm text-gray-900">
                            {member.user.fullName}
                          </span>
                        </button>
                      ))}
                  </div>
                </div>
              )}
            </div>
          </div>

          {/* Time Tracking */}
          {isEditing && item && (
            <div className="space-y-2">
              <label className="text-sm font-medium text-gray-900">Time Tracking</label>
              <TimeTracker
                item={item}
                boardId={boardId}
                className="border-0 shadow-none bg-gray-50"
              />
            </div>
          )}

          <DialogFooter className="flex justify-end space-x-3">
            <Button
              type="button"
              variant="outline"
              onClick={onClose}
              disabled={isSubmitting}
            >
              Cancel
            </Button>
            <Button
              type="submit"
              disabled={isSubmitting || loading.creating || loading.updating}
            >
              {isSubmitting || loading.creating || loading.updating
                ? 'Saving...'
                : isEditing
                ? 'Update Item'
                : 'Create Item'}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )
}