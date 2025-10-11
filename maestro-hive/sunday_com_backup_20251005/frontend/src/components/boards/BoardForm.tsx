import React, { useEffect } from 'react'
import { useForm, useFieldArray } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { Board, CreateBoardData, BoardColumn, ColumnType } from '@/types'
import { Button } from '@/components/ui/Button'
import { Input } from '@/components/ui/Input'
import { Card } from '@/components/ui/Card'
import { Badge } from '@/components/ui/Badge'
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
} from '@radix-ui/react-select'
import { X, Plus, GripVertical, Trash2 } from 'lucide-react'
import clsx from 'clsx'

const columnSchema = z.object({
  name: z.string().min(1, 'Column name is required'),
  columnType: z.enum(['text', 'number', 'status', 'date', 'people', 'timeline', 'files', 'checkbox', 'rating', 'email', 'phone', 'url']),
  isRequired: z.boolean().default(false),
  isVisible: z.boolean().default(true),
  settings: z.record(z.any()).optional(),
})

const boardSchema = z.object({
  name: z.string().min(1, 'Board name is required').max(255, 'Name is too long'),
  description: z.string().optional(),
  isPrivate: z.boolean().default(false),
  columns: z.array(columnSchema).optional(),
})

type BoardFormData = z.infer<typeof boardSchema>

interface BoardFormProps {
  isOpen: boolean
  onClose: () => void
  board?: Board | null
  onSubmit: (data: CreateBoardData | Partial<Board>) => void
}

const columnTypes: Array<{ value: ColumnType; label: string; description: string }> = [
  { value: 'text', label: 'Text', description: 'Single line text' },
  { value: 'status', label: 'Status', description: 'Track progress' },
  { value: 'people', label: 'People', description: 'Assign team members' },
  { value: 'date', label: 'Date', description: 'Due dates and deadlines' },
  { value: 'number', label: 'Number', description: 'Numeric values' },
  { value: 'checkbox', label: 'Checkbox', description: 'Yes/No values' },
  { value: 'rating', label: 'Rating', description: 'Star ratings' },
  { value: 'email', label: 'Email', description: 'Email addresses' },
  { value: 'phone', label: 'Phone', description: 'Phone numbers' },
  { value: 'url', label: 'URL', description: 'Web links' },
  { value: 'files', label: 'Files', description: 'File attachments' },
  { value: 'timeline', label: 'Timeline', description: 'Date ranges' },
]

const defaultColumns = [
  { name: 'Task', columnType: 'text' as ColumnType, isRequired: true, isVisible: true },
  { name: 'Status', columnType: 'status' as ColumnType, isRequired: false, isVisible: true, settings: { statusOptions: ['Todo', 'In Progress', 'Done'] } },
  { name: 'Assignee', columnType: 'people' as ColumnType, isRequired: false, isVisible: true },
  { name: 'Due Date', columnType: 'date' as ColumnType, isRequired: false, isVisible: true },
]

export const BoardForm: React.FC<BoardFormProps> = ({
  isOpen,
  onClose,
  board,
  onSubmit,
}) => {
  const isEditing = !!board

  const {
    register,
    handleSubmit,
    control,
    watch,
    setValue,
    reset,
    formState: { errors, isSubmitting },
  } = useForm<BoardFormData>({
    resolver: zodResolver(boardSchema),
    defaultValues: {
      name: '',
      description: '',
      isPrivate: false,
      columns: defaultColumns,
    },
  })

  const { fields, append, remove, move } = useFieldArray({
    control,
    name: 'columns',
  })

  // Reset form when board changes
  useEffect(() => {
    if (board) {
      reset({
        name: board.name,
        description: board.description || '',
        isPrivate: board.isPrivate,
        columns: board.columns?.map(col => ({
          name: col.name,
          columnType: col.columnType,
          isRequired: col.isRequired,
          isVisible: col.isVisible,
          settings: col.settings,
        })) || defaultColumns,
      })
    } else {
      reset({
        name: '',
        description: '',
        isPrivate: false,
        columns: defaultColumns,
      })
    }
  }, [board, reset])

  const handleFormSubmit = async (data: BoardFormData) => {
    const submitData = {
      name: data.name,
      description: data.description,
      isPrivate: data.isPrivate,
      ...(data.columns && { columns: data.columns }),
    }

    onSubmit(submitData)
  }

  const addColumn = () => {
    append({
      name: 'New Column',
      columnType: 'text',
      isRequired: false,
      isVisible: true,
    })
  }

  const getColumnTypeIcon = (type: ColumnType) => {
    switch (type) {
      case 'text': return '📝'
      case 'status': return '🚦'
      case 'people': return '👥'
      case 'date': return '📅'
      case 'number': return '🔢'
      case 'checkbox': return '☑️'
      case 'rating': return '⭐'
      case 'email': return '📧'
      case 'phone': return '📞'
      case 'url': return '🔗'
      case 'files': return '📎'
      case 'timeline': return '📊'
      default: return '📝'
    }
  }

  return (
    <Dialog open={isOpen} onOpenChange={onClose}>
      <DialogContent className="max-w-4xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>
            {isEditing ? 'Edit Board' : 'Create New Board'}
          </DialogTitle>
          <Button
            variant="ghost"
            size="sm"
            onClick={onClose}
            className="absolute right-4 top-4"
          >
            <X className="h-4 w-4" />
          </Button>
        </DialogHeader>

        <form onSubmit={handleSubmit(handleFormSubmit)} className="space-y-6">
          {/* Basic Information */}
          <div className="space-y-4">
            <h3 className="text-lg font-medium text-gray-900">Basic Information</h3>

            {/* Name */}
            <div className="space-y-2">
              <label htmlFor="name" className="text-sm font-medium text-gray-900">
                Board Name *
              </label>
              <Input
                id="name"
                {...register('name')}
                placeholder="Enter board name..."
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
                placeholder="Enter board description..."
                className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500"
              />
            </div>

            {/* Privacy */}
            <div className="flex items-center space-x-2">
              <input
                type="checkbox"
                id="isPrivate"
                {...register('isPrivate')}
                className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
              />
              <label htmlFor="isPrivate" className="text-sm text-gray-900">
                Make this board private
              </label>
            </div>
          </div>

          {/* Columns Configuration */}
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <h3 className="text-lg font-medium text-gray-900">Columns</h3>
              <Button
                type="button"
                variant="outline"
                size="sm"
                onClick={addColumn}
                className="flex items-center space-x-1"
              >
                <Plus className="h-4 w-4" />
                <span>Add Column</span>
              </Button>
            </div>

            <div className="space-y-3">
              {fields.map((field, index) => (
                <Card key={field.id} className="p-4">
                  <div className="flex items-start space-x-4">
                    {/* Drag Handle */}
                    <div className="flex items-center pt-2">
                      <GripVertical className="h-4 w-4 text-gray-400" />
                    </div>

                    {/* Column Configuration */}
                    <div className="flex-1 space-y-3">
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                        {/* Column Name */}
                        <div className="space-y-1">
                          <label className="text-sm font-medium text-gray-900">
                            Column Name
                          </label>
                          <Input
                            {...register(`columns.${index}.name`)}
                            placeholder="Column name..."
                          />
                        </div>

                        {/* Column Type */}
                        <div className="space-y-1">
                          <label className="text-sm font-medium text-gray-900">
                            Column Type
                          </label>
                          <Select
                            value={watch(`columns.${index}.columnType`)}
                            onValueChange={(value) => setValue(`columns.${index}.columnType`, value as ColumnType)}
                          >
                            <SelectTrigger className="w-full">
                              <SelectValue placeholder="Select type" />
                            </SelectTrigger>
                            <SelectContent>
                              {columnTypes.map((type) => (
                                <SelectItem key={type.value} value={type.value}>
                                  <div className="flex items-center space-x-2">
                                    <span>{getColumnTypeIcon(type.value)}</span>
                                    <div>
                                      <div className="font-medium">{type.label}</div>
                                      <div className="text-xs text-gray-500">{type.description}</div>
                                    </div>
                                  </div>
                                </SelectItem>
                              ))}
                            </SelectContent>
                          </Select>
                        </div>
                      </div>

                      {/* Column Options */}
                      <div className="flex items-center space-x-4">
                        <label className="flex items-center space-x-2">
                          <input
                            type="checkbox"
                            {...register(`columns.${index}.isRequired`)}
                            className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
                          />
                          <span className="text-sm text-gray-900">Required</span>
                        </label>

                        <label className="flex items-center space-x-2">
                          <input
                            type="checkbox"
                            {...register(`columns.${index}.isVisible`)}
                            className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
                          />
                          <span className="text-sm text-gray-900">Visible</span>
                        </label>

                        <div className="flex items-center space-x-1">
                          <Badge variant="outline" className="text-xs">
                            {getColumnTypeIcon(watch(`columns.${index}.columnType`))}
                            {columnTypes.find(t => t.value === watch(`columns.${index}.columnType`))?.label}
                          </Badge>
                        </div>
                      </div>

                      {/* Status Column Options */}
                      {watch(`columns.${index}.columnType`) === 'status' && (
                        <div className="space-y-2">
                          <label className="text-sm font-medium text-gray-900">
                            Status Options
                          </label>
                          <div className="flex flex-wrap gap-2">
                            <Badge variant="secondary">Todo</Badge>
                            <Badge variant="secondary">In Progress</Badge>
                            <Badge variant="secondary">Review</Badge>
                            <Badge variant="secondary">Done</Badge>
                          </div>
                          <p className="text-xs text-gray-500">
                            Default status options will be used. You can customize these after creating the board.
                          </p>
                        </div>
                      )}
                    </div>

                    {/* Delete Button */}
                    <div className="flex items-center pt-2">
                      <Button
                        type="button"
                        variant="ghost"
                        size="sm"
                        onClick={() => remove(index)}
                        disabled={fields.length <= 1}
                        className="text-red-600 hover:text-red-700"
                      >
                        <Trash2 className="h-4 w-4" />
                      </Button>
                    </div>
                  </div>
                </Card>
              ))}
            </div>

            {fields.length === 0 && (
              <div className="text-center py-8 text-gray-500">
                <p className="mb-4">No columns configured</p>
                <Button
                  type="button"
                  variant="outline"
                  onClick={addColumn}
                  className="flex items-center space-x-1"
                >
                  <Plus className="h-4 w-4" />
                  <span>Add First Column</span>
                </Button>
              </div>
            )}
          </div>

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
              disabled={isSubmitting}
            >
              {isSubmitting
                ? 'Saving...'
                : isEditing
                ? 'Update Board'
                : 'Create Board'}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )
}