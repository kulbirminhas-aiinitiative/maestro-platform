import React, { useEffect, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { useBoardStore } from '@/stores/board.store'
import { useErrorHandler } from '@/lib/error-handler'
import { Board, CreateBoardData } from '@/types'
import { Button } from '@/components/ui/Button'
import { Card } from '@/components/ui/Card'
import { Badge } from '@/components/ui/Badge'
import { Avatar } from '@/components/ui/Avatar'
import { Input } from '@/components/ui/Input'
import { LoadingScreen } from '@/components/ui/LoadingScreen'
import { BoardForm } from '@/components/boards/BoardForm'
import {
  Plus,
  Search,
  Grid,
  List,
  Filter,
  MoreHorizontal,
  Users,
  Calendar,
  Eye,
  EyeOff,
  Star,
  Archive,
} from 'lucide-react'
import { format } from 'date-fns'
import clsx from 'clsx'

interface BoardsPageProps {
  className?: string
}

export const BoardsPage: React.FC<BoardsPageProps> = ({ className }) => {
  const { workspaceId } = useParams<{ workspaceId: string }>()
  const navigate = useNavigate()
  const { handleError, handleSuccess, retryOperation } = useErrorHandler()

  const [viewMode, setViewMode] = useState<'grid' | 'list'>('grid')
  const [searchQuery, setSearchQuery] = useState('')
  const [showBoardForm, setShowBoardForm] = useState(false)
  const [selectedBoard, setSelectedBoard] = useState<Board | null>(null)

  const {
    boards,
    loading,
    errors,
    pagination,
    filters,
    fetchBoards,
    createBoard,
    updateBoard,
    deleteBoard,
    setFilters,
  } = useBoardStore()

  // Fetch boards on mount
  useEffect(() => {
    if (workspaceId) {
      fetchBoards(workspaceId)
    }
  }, [workspaceId, fetchBoards])

  // Filter boards based on search query
  const filteredBoards = boards.filter(board =>
    board.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
    (board.description && board.description.toLowerCase().includes(searchQuery.toLowerCase()))
  )

  const handleCreateBoard = async (data: CreateBoardData) => {
    if (!workspaceId) return

    try {
      const newBoard = await retryOperation(() => createBoard(workspaceId, data))
      if (newBoard) {
        setShowBoardForm(false)
        handleSuccess('Board created')
        // Navigate to the new board
        navigate(`/boards/${newBoard.id}`)
      }
    } catch (error) {
      handleError(error, 'creating board')
    }
  }

  const handleEditBoard = (board: Board) => {
    setSelectedBoard(board)
    setShowBoardForm(true)
  }

  const handleUpdateBoard = async (data: Partial<Board>) => {
    if (!selectedBoard) return

    try {
      const updatedBoard = await retryOperation(() => updateBoard(selectedBoard.id, data))
      if (updatedBoard) {
        setShowBoardForm(false)
        setSelectedBoard(null)
        handleSuccess('Board updated')
      }
    } catch (error) {
      handleError(error, 'updating board')
    }
  }

  const handleDeleteBoard = async (boardId: string) => {
    if (window.confirm('Are you sure you want to delete this board? This action cannot be undone.')) {
      try {
        await retryOperation(() => deleteBoard(boardId))
        handleSuccess('Board deleted')
      } catch (error) {
        handleError(error, 'deleting board')
      }
    }
  }

  if (loading.boards && boards.length === 0) {
    return <LoadingScreen message="Loading boards..." />
  }

  if (errors.boards) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-center">
          <h3 className="text-lg font-medium text-gray-900 mb-2">
            Error loading boards
          </h3>
          <p className="text-gray-500 mb-4">{errors.boards}</p>
          <Button onClick={() => workspaceId && fetchBoards(workspaceId)}>
            Try Again
          </Button>
        </div>
      </div>
    )
  }

  return (
    <div className={clsx('flex flex-col h-full', className)}>
      {/* Header */}
      <div className="bg-white border-b border-gray-200 px-6 py-4">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-gray-900">Boards</h1>
            <p className="text-gray-500 mt-1">
              Manage and organize your work across different boards
            </p>
          </div>

          <div className="flex items-center space-x-3">
            <Button
              onClick={() => setShowBoardForm(true)}
              className="flex items-center space-x-2"
            >
              <Plus className="h-4 w-4" />
              <span>New Board</span>
            </Button>
          </div>
        </div>

        {/* Filters and Search */}
        <div className="flex items-center justify-between mt-6">
          <div className="flex items-center space-x-4">
            {/* Search */}
            <div className="relative">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-400" />
              <Input
                placeholder="Search boards..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="pl-10 w-64"
              />
            </div>

            {/* Filters */}
            <Button variant="outline" size="sm" className="flex items-center space-x-1">
              <Filter className="h-4 w-4" />
              <span>Filter</span>
            </Button>
          </div>

          {/* View Toggle */}
          <div className="flex items-center space-x-2">
            <div className="flex items-center bg-gray-100 rounded-lg p-1">
              <Button
                size="sm"
                variant={viewMode === 'grid' ? 'default' : 'ghost'}
                onClick={() => setViewMode('grid')}
                className="flex items-center space-x-1"
              >
                <Grid className="h-4 w-4" />
                <span>Grid</span>
              </Button>
              <Button
                size="sm"
                variant={viewMode === 'list' ? 'default' : 'ghost'}
                onClick={() => setViewMode('list')}
                className="flex items-center space-x-1"
              >
                <List className="h-4 w-4" />
                <span>List</span>
              </Button>
            </div>
          </div>
        </div>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto p-6">
        {filteredBoards.length === 0 ? (
          <div className="flex items-center justify-center h-64">
            <div className="text-center">
              {searchQuery ? (
                <>
                  <h3 className="text-lg font-medium text-gray-900 mb-2">
                    No boards found
                  </h3>
                  <p className="text-gray-500 mb-4">
                    No boards match your search "{searchQuery}"
                  </p>
                  <Button
                    variant="outline"
                    onClick={() => setSearchQuery('')}
                  >
                    Clear search
                  </Button>
                </>
              ) : (
                <>
                  <h3 className="text-lg font-medium text-gray-900 mb-2">
                    No boards yet
                  </h3>
                  <p className="text-gray-500 mb-4">
                    Create your first board to start organizing your work
                  </p>
                  <Button onClick={() => setShowBoardForm(true)}>
                    <Plus className="h-4 w-4 mr-2" />
                    Create Board
                  </Button>
                </>
              )}
            </div>
          </div>
        ) : (
          <>
            {viewMode === 'grid' ? (
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
                {filteredBoards.map((board) => (
                  <BoardCard
                    key={board.id}
                    board={board}
                    onEdit={() => handleEditBoard(board)}
                    onDelete={() => handleDeleteBoard(board.id)}
                    onClick={() => navigate(`/boards/${board.id}`)}
                  />
                ))}
              </div>
            ) : (
              <div className="space-y-4">
                {filteredBoards.map((board) => (
                  <BoardListItem
                    key={board.id}
                    board={board}
                    onEdit={() => handleEditBoard(board)}
                    onDelete={() => handleDeleteBoard(board.id)}
                    onClick={() => navigate(`/boards/${board.id}`)}
                  />
                ))}
              </div>
            )}

            {/* Pagination */}
            {pagination.totalPages > 1 && (
              <div className="flex items-center justify-center mt-8 space-x-2">
                <Button
                  variant="outline"
                  size="sm"
                  disabled={!pagination.hasPrev}
                  onClick={() => {
                    if (workspaceId) {
                      fetchBoards(workspaceId, { page: pagination.page - 1 })
                    }
                  }}
                >
                  Previous
                </Button>
                <span className="text-sm text-gray-500">
                  Page {pagination.page} of {pagination.totalPages}
                </span>
                <Button
                  variant="outline"
                  size="sm"
                  disabled={!pagination.hasNext}
                  onClick={() => {
                    if (workspaceId) {
                      fetchBoards(workspaceId, { page: pagination.page + 1 })
                    }
                  }}
                >
                  Next
                </Button>
              </div>
            )}
          </>
        )}
      </div>

      {/* Board Form Modal */}
      {showBoardForm && (
        <BoardForm
          isOpen={showBoardForm}
          onClose={() => {
            setShowBoardForm(false)
            setSelectedBoard(null)
          }}
          board={selectedBoard}
          onSubmit={selectedBoard ? handleUpdateBoard : handleCreateBoard}
        />
      )}
    </div>
  )
}

// Board Card Component
interface BoardCardProps {
  board: Board
  onEdit: () => void
  onDelete: () => void
  onClick: () => void
}

const BoardCard: React.FC<BoardCardProps> = ({ board, onEdit, onDelete, onClick }) => {
  const [showMenu, setShowMenu] = useState(false)

  return (
    <Card className="p-6 cursor-pointer hover:shadow-lg transition-shadow group">
      <div className="flex items-start justify-between mb-4">
        <div className="flex-1" onClick={onClick}>
          <h3 className="font-semibold text-gray-900 mb-2 line-clamp-2">
            {board.name}
          </h3>
          {board.description && (
            <p className="text-sm text-gray-600 line-clamp-3">
              {board.description}
            </p>
          )}
        </div>

        <div className="relative">
          <Button
            size="sm"
            variant="ghost"
            onClick={(e) => {
              e.stopPropagation()
              setShowMenu(!showMenu)
            }}
            className="opacity-0 group-hover:opacity-100 transition-opacity"
          >
            <MoreHorizontal className="h-4 w-4" />
          </Button>

          {showMenu && (
            <div className="absolute right-0 top-8 w-48 bg-white rounded-md shadow-lg border border-gray-200 py-1 z-10">
              <button
                className="w-full text-left px-4 py-2 text-sm text-gray-700 hover:bg-gray-100"
                onClick={(e) => {
                  e.stopPropagation()
                  onEdit()
                  setShowMenu(false)
                }}
              >
                Edit
              </button>
              <button
                className="w-full text-left px-4 py-2 text-sm text-gray-700 hover:bg-gray-100"
                onClick={(e) => {
                  e.stopPropagation()
                  setShowMenu(false)
                }}
              >
                {board.isPrivate ? 'Make Public' : 'Make Private'}
              </button>
              <button
                className="w-full text-left px-4 py-2 text-sm text-red-600 hover:bg-red-50"
                onClick={(e) => {
                  e.stopPropagation()
                  onDelete()
                  setShowMenu(false)
                }}
              >
                Delete
              </button>
            </div>
          )}
        </div>
      </div>

      <div className="space-y-3" onClick={onClick}>
        {/* Statistics */}
        <div className="flex items-center justify-between text-sm text-gray-500">
          <div className="flex items-center space-x-4">
            <div className="flex items-center space-x-1">
              <span>📋</span>
              <span>{board._count?.items || 0} items</span>
            </div>
            <div className="flex items-center space-x-1">
              <Users className="h-4 w-4" />
              <span>{board._count?.members || 0} members</span>
            </div>
          </div>

          <div className="flex items-center space-x-2">
            {board.isPrivate && <EyeOff className="h-4 w-4" />}
          </div>
        </div>

        {/* Members */}
        {board.members && board.members.length > 0 && (
          <div className="flex items-center space-x-2">
            <div className="flex -space-x-1">
              {board.members.slice(0, 3).map((member, index) => (
                <Avatar
                  key={member.id}
                  src={member.user.avatarUrl}
                  alt={member.user.fullName}
                  size="sm"
                  className="ring-2 ring-white"
                />
              ))}
              {board.members.length > 3 && (
                <div className="flex items-center justify-center w-8 h-8 bg-gray-100 rounded-full ring-2 ring-white text-xs font-medium text-gray-600">
                  +{board.members.length - 3}
                </div>
              )}
            </div>
          </div>
        )}

        {/* Last updated */}
        <p className="text-xs text-gray-400">
          Updated {format(new Date(board.updatedAt), 'MMM d, yyyy')}
        </p>
      </div>
    </Card>
  )
}

// Board List Item Component
interface BoardListItemProps {
  board: Board
  onEdit: () => void
  onDelete: () => void
  onClick: () => void
}

const BoardListItem: React.FC<BoardListItemProps> = ({ board, onEdit, onDelete, onClick }) => {
  return (
    <Card className="p-4 cursor-pointer hover:shadow-md transition-shadow">
      <div className="flex items-center justify-between" onClick={onClick}>
        <div className="flex items-center space-x-4 flex-1">
          <div className="flex-1">
            <div className="flex items-center space-x-3">
              <h3 className="font-medium text-gray-900">{board.name}</h3>
              {board.isPrivate && (
                <Badge variant="outline" className="text-xs">
                  <EyeOff className="h-3 w-3 mr-1" />
                  Private
                </Badge>
              )}
            </div>
            {board.description && (
              <p className="text-sm text-gray-600 mt-1 line-clamp-1">
                {board.description}
              </p>
            )}
          </div>

          <div className="flex items-center space-x-6 text-sm text-gray-500">
            <div className="flex items-center space-x-1">
              <span>📋</span>
              <span>{board._count?.items || 0}</span>
            </div>
            <div className="flex items-center space-x-1">
              <Users className="h-4 w-4" />
              <span>{board._count?.members || 0}</span>
            </div>
            <div className="flex items-center space-x-1">
              <Calendar className="h-4 w-4" />
              <span>{format(new Date(board.updatedAt), 'MMM d')}</span>
            </div>
          </div>

          <div className="flex items-center space-x-2">
            {board.members && board.members.length > 0 && (
              <div className="flex -space-x-1">
                {board.members.slice(0, 3).map((member, index) => (
                  <Avatar
                    key={member.id}
                    src={member.user.avatarUrl}
                    alt={member.user.fullName}
                    size="sm"
                    className="ring-2 ring-white"
                  />
                ))}
              </div>
            )}
          </div>
        </div>

        <div className="flex items-center space-x-2">
          <Button
            size="sm"
            variant="ghost"
            onClick={(e) => {
              e.stopPropagation()
              onEdit()
            }}
          >
            Edit
          </Button>
          <Button
            size="sm"
            variant="ghost"
            onClick={(e) => {
              e.stopPropagation()
              onDelete()
            }}
            className="text-red-600 hover:text-red-700"
          >
            Delete
          </Button>
        </div>
      </div>
    </Card>
  )
}