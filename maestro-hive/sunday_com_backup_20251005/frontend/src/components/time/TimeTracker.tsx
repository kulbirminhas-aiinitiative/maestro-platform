import React, { useEffect, useState } from 'react'
import { useTimeStore } from '@/stores/time.store'
import { useAuth } from '@/hooks/useAuth'
import { Button } from '@/components/ui/Button'
import { Card } from '@/components/ui/Card'
import { Badge } from '@/components/ui/Badge'
import { Input } from '@/components/ui/Input'
import { Play, Pause, Square, Clock, DollarSign } from 'lucide-react'
import { formatDistanceToNow, format } from 'date-fns'
import clsx from 'clsx'
import type { Item } from '@/types'

interface TimeTrackerProps {
  className?: string
  item?: Item
  boardId?: string
  onTimerUpdate?: (isRunning: boolean) => void
}

export const TimeTracker: React.FC<TimeTrackerProps> = ({
  className,
  item,
  boardId,
  onTimerUpdate,
}) => {
  const { user } = useAuth()
  const [description, setDescription] = useState('')
  const [isBillable, setIsBillable] = useState(false)
  const [elapsedTime, setElapsedTime] = useState(0)
  const [showDescription, setShowDescription] = useState(false)

  const {
    activeTimer,
    loading,
    errors,
    startTimer,
    stopTimer,
    getActiveTimer,
    createTimeEntry,
  } = useTimeStore()

  // Fetch active timer on mount
  useEffect(() => {
    getActiveTimer()
  }, [getActiveTimer])

  // Update elapsed time every second when timer is active
  useEffect(() => {
    let interval: NodeJS.Timeout | null = null

    if (activeTimer) {
      const startTime = new Date(activeTimer.startTime).getTime()

      interval = setInterval(() => {
        const now = Date.now()
        const elapsed = Math.floor((now - startTime) / 1000)
        setElapsedTime(elapsed)
      }, 1000)

      // Initial calculation
      const now = Date.now()
      const elapsed = Math.floor((now - startTime) / 1000)
      setElapsedTime(elapsed)
    } else {
      setElapsedTime(0)
    }

    return () => {
      if (interval) {
        clearInterval(interval)
      }
    }
  }, [activeTimer])

  // Notify parent of timer changes
  useEffect(() => {
    onTimerUpdate?.(!!activeTimer)
  }, [activeTimer, onTimerUpdate])

  const handleStartTimer = async () => {
    try {
      await startTimer({
        itemId: item?.id,
        boardId: boardId,
        description: description.trim() || undefined,
        billable: isBillable,
        metadata: {
          itemName: item?.name,
          boardName: item?.board?.name,
          startedBy: user?.id,
        },
      })
      setShowDescription(false)
    } catch (error) {
      console.error('Failed to start timer:', error)
    }
  }

  const handleStopTimer = async () => {
    try {
      await stopTimer()
      setDescription('')
    } catch (error) {
      console.error('Failed to stop timer:', error)
    }
  }

  const handleCreateManualEntry = async () => {
    try {
      await createTimeEntry({
        itemId: item?.id,
        boardId: boardId,
        description: description.trim() || undefined,
        billable: isBillable,
      })
      setDescription('')
      setShowDescription(false)
    } catch (error) {
      console.error('Failed to create time entry:', error)
    }
  }

  const formatElapsedTime = (seconds: number): string => {
    const hours = Math.floor(seconds / 3600)
    const minutes = Math.floor((seconds % 3600) / 60)
    const secs = seconds % 60

    if (hours > 0) {
      return `${hours}:${minutes.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`
    }
    return `${minutes}:${secs.toString().padStart(2, '0')}`
  }

  const isTimerForCurrentItem = activeTimer && (
    (item && activeTimer.itemId === item.id) ||
    (!item && activeTimer.boardId === boardId)
  )

  const isTimerForDifferentItem = activeTimer && !isTimerForCurrentItem

  return (
    <Card className={clsx('p-4 space-y-4', className)}>
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-2">
          <Clock className="h-5 w-5 text-gray-400" />
          <h3 className="font-medium text-gray-900">Time Tracking</h3>
        </div>

        {/* Timer display */}
        {activeTimer && (
          <div className="flex items-center space-x-2">
            <Badge
              variant={isTimerForCurrentItem ? 'default' : 'secondary'}
              className={clsx(
                'font-mono text-lg px-3 py-1',
                isTimerForCurrentItem && 'animate-pulse bg-green-100 text-green-800'
              )}
            >
              {formatElapsedTime(elapsedTime)}
            </Badge>
            {activeTimer.billable && (
              <DollarSign className="h-4 w-4 text-green-600" title="Billable" />
            )}
          </div>
        )}
      </div>

      {/* Timer for different item warning */}
      {isTimerForDifferentItem && (
        <div className="bg-yellow-50 border border-yellow-200 rounded-md p-3">
          <div className="flex items-center space-x-2">
            <Clock className="h-4 w-4 text-yellow-600" />
            <div className="text-sm">
              <p className="text-yellow-800 font-medium">Timer running for another item</p>
              <p className="text-yellow-700">
                {activeTimer.description || 'No description'}
                {activeTimer.itemId && (
                  <span className="ml-1 text-yellow-600">
                    (Item ID: {activeTimer.itemId.slice(0, 8)}...)
                  </span>
                )}
              </p>
            </div>
          </div>
          <div className="mt-2 flex space-x-2">
            <Button
              size="sm"
              variant="outline"
              onClick={handleStopTimer}
              disabled={loading.stopping}
              className="text-yellow-700 border-yellow-300 hover:bg-yellow-100"
            >
              <Square className="h-3 w-3 mr-1" />
              Stop Timer
            </Button>
          </div>
        </div>
      )}

      {/* Description input */}
      {(showDescription || activeTimer) && (
        <div className="space-y-2">
          <Input
            placeholder="What are you working on?"
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            disabled={!!activeTimer}
            className="text-sm"
          />
          <div className="flex items-center space-x-3">
            <label className="flex items-center space-x-2 text-sm">
              <input
                type="checkbox"
                checked={isBillable}
                onChange={(e) => setIsBillable(e.target.checked)}
                disabled={!!activeTimer}
                className="rounded border-gray-300 text-green-600 focus:ring-green-500"
              />
              <span className="text-gray-700">Billable</span>
            </label>
          </div>
        </div>
      )}

      {/* Action buttons */}
      <div className="flex items-center justify-between">
        <div className="flex space-x-2">
          {!activeTimer ? (
            <>
              {showDescription ? (
                <>
                  <Button
                    size="sm"
                    onClick={handleStartTimer}
                    disabled={loading.starting}
                    className="flex items-center space-x-1"
                  >
                    <Play className="h-4 w-4" />
                    <span>{loading.starting ? 'Starting...' : 'Start Timer'}</span>
                  </Button>
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={handleCreateManualEntry}
                    disabled={loading.creating}
                    className="flex items-center space-x-1"
                  >
                    <Clock className="h-4 w-4" />
                    <span>Manual Entry</span>
                  </Button>
                </>
              ) : (
                <Button
                  size="sm"
                  variant="outline"
                  onClick={() => setShowDescription(true)}
                  className="flex items-center space-x-1"
                >
                  <Play className="h-4 w-4" />
                  <span>Track Time</span>
                </Button>
              )}
            </>
          ) : isTimerForCurrentItem ? (
            <Button
              size="sm"
              variant="outline"
              onClick={handleStopTimer}
              disabled={loading.stopping}
              className="flex items-center space-x-1 text-red-600 border-red-300 hover:bg-red-50"
            >
              <Square className="h-4 w-4" />
              <span>{loading.stopping ? 'Stopping...' : 'Stop Timer'}</span>
            </Button>
          ) : null}

          {showDescription && !activeTimer && (
            <Button
              size="sm"
              variant="ghost"
              onClick={() => {
                setShowDescription(false)
                setDescription('')
                setIsBillable(false)
              }}
            >
              Cancel
            </Button>
          )}
        </div>

        {/* Timer info */}
        {activeTimer && isTimerForCurrentItem && (
          <div className="text-xs text-gray-500">
            Started {formatDistanceToNow(new Date(activeTimer.startTime), { addSuffix: true })}
          </div>
        )}
      </div>

      {/* Error display */}
      {(errors.starting || errors.stopping || errors.creating) && (
        <div className="bg-red-50 border border-red-200 rounded-md p-2">
          <p className="text-sm text-red-800">
            {errors.starting || errors.stopping || errors.creating}
          </p>
        </div>
      )}

      {/* Recent time entries for this item */}
      {item?.timeEntries && item.timeEntries.length > 0 && (
        <div className="border-t pt-4 space-y-2">
          <h4 className="text-sm font-medium text-gray-700">Recent Entries</h4>
          <div className="space-y-1">
            {item.timeEntries.slice(0, 3).map((entry) => (
              <div
                key={entry.id}
                className="flex items-center justify-between text-xs text-gray-600"
              >
                <div className="flex items-center space-x-2">
                  <span>{entry.description || 'No description'}</span>
                  {entry.isBillable && (
                    <DollarSign className="h-3 w-3 text-green-600" />
                  )}
                </div>
                <div className="flex items-center space-x-2">
                  <span>
                    {entry.durationSeconds
                      ? formatElapsedTime(entry.durationSeconds)
                      : 'Running...'}
                  </span>
                  <span className="text-gray-400">
                    {format(new Date(entry.startTime), 'MMM d')}
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </Card>
  )
}