import React, { useState } from 'react'
import { BoardColumn } from '@/types'
import { Button } from '@/components/ui/Button'
import { Badge } from '@/components/ui/Badge'
import { Plus, MoreHorizontal, Edit2, Trash2 } from 'lucide-react'
import clsx from 'clsx'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@radix-ui/react-dropdown-menu'

interface ColumnHeaderProps {
  column: BoardColumn
  itemCount: number
  onAddItem: () => void
  onEditColumn?: () => void
  onDeleteColumn?: () => void
  className?: string
}

export const ColumnHeader: React.FC<ColumnHeaderProps> = ({
  column,
  itemCount,
  onAddItem,
  onEditColumn,
  onDeleteColumn,
  className,
}) => {
  const [showMenu, setShowMenu] = useState(false)

  const getColumnColor = (columnType: string) => {
    switch (columnType) {
      case 'status':
        return 'bg-blue-100 text-blue-800'
      case 'people':
        return 'bg-green-100 text-green-800'
      case 'date':
        return 'bg-purple-100 text-purple-800'
      case 'number':
        return 'bg-orange-100 text-orange-800'
      default:
        return 'bg-gray-100 text-gray-800'
    }
  }

  return (
    <div className={clsx('flex items-center justify-between p-4 border-b border-gray-200', className)}>
      <div className="flex items-center space-x-3">
        <div className="flex items-center space-x-2">
          <h3 className="font-medium text-gray-900">
            {column.name}
          </h3>
          <Badge
            variant="secondary"
            className={clsx('text-xs', getColumnColor(column.columnType))}
          >
            {column.columnType}
          </Badge>
        </div>

        {itemCount > 0 && (
          <Badge variant="outline" className="text-xs">
            {itemCount}
          </Badge>
        )}
      </div>

      <div className="flex items-center space-x-1">
        <Button
          size="sm"
          variant="ghost"
          onClick={onAddItem}
          className="text-gray-500 hover:text-gray-700"
        >
          <Plus className="h-4 w-4" />
        </Button>

        <DropdownMenu open={showMenu} onOpenChange={setShowMenu}>
          <DropdownMenuTrigger asChild>
            <Button
              size="sm"
              variant="ghost"
              className="text-gray-500 hover:text-gray-700"
            >
              <MoreHorizontal className="h-4 w-4" />
            </Button>
          </DropdownMenuTrigger>

          <DropdownMenuContent
            className="w-48 bg-white rounded-md shadow-lg border border-gray-200 py-1"
            align="end"
          >
            {onEditColumn && (
              <DropdownMenuItem
                className="flex items-center space-x-2 px-3 py-2 text-sm text-gray-700 hover:bg-gray-100 cursor-pointer"
                onClick={() => {
                  onEditColumn()
                  setShowMenu(false)
                }}
              >
                <Edit2 className="h-4 w-4" />
                <span>Edit Column</span>
              </DropdownMenuItem>
            )}

            <DropdownMenuItem
              className="flex items-center space-x-2 px-3 py-2 text-sm text-gray-700 hover:bg-gray-100 cursor-pointer"
              onClick={() => setShowMenu(false)}
            >
              <span>Hide Column</span>
            </DropdownMenuItem>

            <DropdownMenuItem
              className="flex items-center space-x-2 px-3 py-2 text-sm text-gray-700 hover:bg-gray-100 cursor-pointer"
              onClick={() => setShowMenu(false)}
            >
              <span>Sort by...</span>
            </DropdownMenuItem>

            <DropdownMenuItem
              className="flex items-center space-x-2 px-3 py-2 text-sm text-gray-700 hover:bg-gray-100 cursor-pointer"
              onClick={() => setShowMenu(false)}
            >
              <span>Filter...</span>
            </DropdownMenuItem>

            {onDeleteColumn && (
              <>
                <DropdownMenuSeparator className="my-1 border-t border-gray-200" />
                <DropdownMenuItem
                  className="flex items-center space-x-2 px-3 py-2 text-sm text-red-600 hover:bg-red-50 cursor-pointer"
                  onClick={() => {
                    onDeleteColumn()
                    setShowMenu(false)
                  }}
                >
                  <Trash2 className="h-4 w-4" />
                  <span>Delete Column</span>
                </DropdownMenuItem>
              </>
            )}
          </DropdownMenuContent>
        </DropdownMenu>
      </div>
    </div>
  )
}