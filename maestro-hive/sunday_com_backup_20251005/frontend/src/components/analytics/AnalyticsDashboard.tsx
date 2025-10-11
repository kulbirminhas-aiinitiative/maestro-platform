import React, { useEffect, useState } from 'react'
import { useAnalyticsStore } from '@/stores/analytics.store'
import { useAuth } from '@/hooks/useAuth'
import { Card } from '@/components/ui/Card'
import { Button } from '@/components/ui/Button'
import { Badge } from '@/components/ui/Badge'
import { LoadingScreen } from '@/components/ui/LoadingScreen'
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  LineChart,
  Line,
  PieChart,
  Pie,
  Cell,
  Legend,
} from 'recharts'
import {
  TrendingUp,
  TrendingDown,
  Users,
  CheckSquare,
  Clock,
  Target,
  Download,
  Calendar,
  Filter,
} from 'lucide-react'
import { format, subDays, startOfWeek, endOfWeek } from 'date-fns'
import clsx from 'clsx'
import type { AnalyticsData, BoardAnalytics, OrganizationAnalytics } from '@/types'

interface AnalyticsDashboardProps {
  className?: string
  boardId?: string
  workspaceId?: string
  organizationId?: string
  timeRange?: '7d' | '30d' | '90d' | '1y'
}

export const AnalyticsDashboard: React.FC<AnalyticsDashboardProps> = ({
  className,
  boardId,
  workspaceId,
  organizationId,
  timeRange = '30d',
}) => {
  const { user } = useAuth()
  const [selectedMetric, setSelectedMetric] = useState<string>('overview')
  const [dateRange, setDateRange] = useState({
    start: subDays(new Date(), 30),
    end: new Date(),
  })

  const {
    dashboardOverview,
    boardAnalytics,
    organizationAnalytics,
    loading,
    errors,
    fetchDashboardOverview,
    fetchBoardAnalytics,
    fetchOrganizationAnalytics,
    exportData,
  } = useAnalyticsStore()

  // Fetch data on mount and when dependencies change
  useEffect(() => {
    if (boardId) {
      fetchBoardAnalytics(boardId, {
        startDate: dateRange.start.toISOString(),
        endDate: dateRange.end.toISOString(),
      })
    } else if (organizationId) {
      fetchOrganizationAnalytics(organizationId, {
        startDate: dateRange.start.toISOString(),
        endDate: dateRange.end.toISOString(),
      })
    } else {
      fetchDashboardOverview({
        startDate: dateRange.start.toISOString(),
        endDate: dateRange.end.toISOString(),
      })
    }
  }, [
    boardId,
    organizationId,
    dateRange,
    fetchDashboardOverview,
    fetchBoardAnalytics,
    fetchOrganizationAnalytics,
  ])

  const handleExport = async (format: 'json' | 'csv') => {
    try {
      await exportData({
        format,
        boardId,
        organizationId,
        startDate: dateRange.start.toISOString(),
        endDate: dateRange.end.toISOString(),
      })
    } catch (error) {
      console.error('Failed to export data:', error)
    }
  }

  const getMainData = (): AnalyticsData | BoardAnalytics | OrganizationAnalytics | null => {
    if (boardId) {
      return boardAnalytics[boardId] || null
    }
    if (organizationId) {
      return organizationAnalytics[organizationId] || null
    }
    return dashboardOverview
  }

  const mainData = getMainData()
  const isLoading = boardId
    ? loading.boardAnalytics[boardId]
    : organizationId
    ? loading.organizationAnalytics[organizationId]
    : loading.dashboardOverview

  const error = boardId
    ? errors.boardAnalytics[boardId]
    : organizationId
    ? errors.organizationAnalytics[organizationId]
    : errors.dashboardOverview

  if (isLoading) {
    return <LoadingScreen message="Loading analytics..." />
  }

  if (error) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-center">
          <h3 className="text-lg font-medium text-gray-900 mb-2">
            Error loading analytics
          </h3>
          <p className="text-gray-500 mb-4">{error}</p>
          <Button onClick={() => window.location.reload()}>
            Try Again
          </Button>
        </div>
      </div>
    )
  }

  if (!mainData) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-center">
          <h3 className="text-lg font-medium text-gray-900 mb-2">
            No data available
          </h3>
          <p className="text-gray-500">
            Analytics data will appear here once you have some activity.
          </p>
        </div>
      </div>
    )
  }

  // Common chart colors
  const colors = ['#3B82F6', '#10B981', '#F59E0B', '#EF4444', '#8B5CF6']

  return (
    <div className={clsx('space-y-6', className)}>
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-gray-900">Analytics</h2>
          <p className="text-gray-500">
            {format(dateRange.start, 'MMM d')} - {format(dateRange.end, 'MMM d, yyyy')}
          </p>
        </div>

        <div className="flex items-center space-x-3">
          {/* Time range selector */}
          <div className="flex space-x-1">
            {[
              { value: '7d', label: '7 days' },
              { value: '30d', label: '30 days' },
              { value: '90d', label: '90 days' },
              { value: '1y', label: '1 year' },
            ].map((range) => (
              <Button
                key={range.value}
                size="sm"
                variant={timeRange === range.value ? 'default' : 'outline'}
                onClick={() => {
                  const days = range.value === '7d' ? 7 : range.value === '30d' ? 30 : range.value === '90d' ? 90 : 365
                  setDateRange({
                    start: subDays(new Date(), days),
                    end: new Date(),
                  })
                }}
              >
                {range.label}
              </Button>
            ))}
          </div>

          {/* Export button */}
          <Button
            size="sm"
            variant="outline"
            onClick={() => handleExport('csv')}
            disabled={loading.export}
            className="flex items-center space-x-1"
          >
            <Download className="h-4 w-4" />
            <span>Export</span>
          </Button>
        </div>
      </div>

      {/* Key Metrics */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <MetricCard
          title="Total Items"
          value={mainData.totalItems || 0}
          icon={<Target className="h-6 w-6" />}
          trend={{
            value: 12,
            isPositive: true,
            label: 'vs last period',
          }}
        />
        <MetricCard
          title="Completed Items"
          value={mainData.completedItems || 0}
          icon={<CheckSquare className="h-6 w-6" />}
          trend={{
            value: 8,
            isPositive: true,
            label: 'vs last period',
          }}
        />
        <MetricCard
          title="Completion Rate"
          value={`${Math.round(((mainData.completedItems || 0) / (mainData.totalItems || 1)) * 100)}%`}
          icon={<TrendingUp className="h-6 w-6" />}
          trend={{
            value: 5,
            isPositive: true,
            label: 'percentage points',
          }}
        />
        <MetricCard
          title="Active Users"
          value={mainData.activeUsers || 0}
          icon={<Users className="h-6 w-6" />}
          trend={{
            value: 3,
            isPositive: false,
            label: 'vs last period',
          }}
        />
      </div>

      {/* Charts Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Trends Chart */}
        <Card className="p-6">
          <h3 className="text-lg font-medium text-gray-900 mb-4">Activity Trends</h3>
          <div className="h-80">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={mainData.trends || []}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis
                  dataKey="date"
                  tickFormatter={(date) => format(new Date(date), 'MMM d')}
                />
                <YAxis />
                <Tooltip
                  labelFormatter={(date) => format(new Date(date), 'MMM d, yyyy')}
                />
                <Line
                  type="monotone"
                  dataKey="value"
                  stroke="#3B82F6"
                  strokeWidth={2}
                  dot={{ fill: '#3B82F6' }}
                />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </Card>

        {/* Status Distribution */}
        {boardId && (boardAnalytics[boardId] as BoardAnalytics)?.itemDistribution && (
          <Card className="p-6">
            <h3 className="text-lg font-medium text-gray-900 mb-4">Item Status Distribution</h3>
            <div className="h-80">
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={(boardAnalytics[boardId] as BoardAnalytics).itemDistribution}
                    cx="50%"
                    cy="50%"
                    labelLine={false}
                    label={({ status, percentage }) => `${status} (${percentage}%)`}
                    outerRadius={80}
                    fill="#8884d8"
                    dataKey="count"
                  >
                    {(boardAnalytics[boardId] as BoardAnalytics).itemDistribution.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={colors[index % colors.length]} />
                    ))}
                  </Pie>
                  <Tooltip />
                  <Legend />
                </PieChart>
              </ResponsiveContainer>
            </div>
          </Card>
        )}

        {/* Member Activity */}
        {boardId && (boardAnalytics[boardId] as BoardAnalytics)?.memberActivity && (
          <Card className="p-6">
            <h3 className="text-lg font-medium text-gray-900 mb-4">Member Activity</h3>
            <div className="h-80">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={(boardAnalytics[boardId] as BoardAnalytics).memberActivity}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="userName" />
                  <YAxis />
                  <Tooltip />
                  <Bar dataKey="itemsCompleted" fill="#10B981" name="Completed Items" />
                  <Bar dataKey="itemsCreated" fill="#3B82F6" name="Created Items" />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </Card>
        )}

        {/* Velocity Chart */}
        {boardId && (boardAnalytics[boardId] as BoardAnalytics)?.velocity && (
          <Card className="p-6">
            <h3 className="text-lg font-medium text-gray-900 mb-4">Velocity</h3>
            <div className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div className="text-center">
                  <div className="text-2xl font-bold text-blue-600">
                    {(boardAnalytics[boardId] as BoardAnalytics).velocity.itemsCompletedThisWeek}
                  </div>
                  <div className="text-sm text-gray-500">This Week</div>
                </div>
                <div className="text-center">
                  <div className="text-2xl font-bold text-gray-600">
                    {(boardAnalytics[boardId] as BoardAnalytics).velocity.itemsCompletedLastWeek}
                  </div>
                  <div className="text-sm text-gray-500">Last Week</div>
                </div>
              </div>
              <div className="text-center">
                <div className="text-lg font-medium text-gray-900">
                  Average Completion Time
                </div>
                <div className="text-2xl font-bold text-green-600">
                  {Math.round((boardAnalytics[boardId] as BoardAnalytics).velocity.averageCompletionTime / 3600)}h
                </div>
              </div>
            </div>
          </Card>
        )}
      </div>

      {/* Detailed Tables */}
      <div className="grid grid-cols-1 gap-6">
        {/* Recent Activity */}
        <Card className="p-6">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-lg font-medium text-gray-900">Recent Activity</h3>
            <Badge variant="secondary">Live Data</Badge>
          </div>
          <div className="space-y-3">
            <div className="text-sm text-gray-500">
              Activity data will be displayed here as users interact with items.
            </div>
          </div>
        </Card>
      </div>
    </div>
  )
}

interface MetricCardProps {
  title: string
  value: string | number
  icon: React.ReactNode
  trend?: {
    value: number
    isPositive: boolean
    label: string
  }
}

const MetricCard: React.FC<MetricCardProps> = ({ title, value, icon, trend }) => {
  return (
    <Card className="p-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-3">
          <div className="p-2 bg-blue-50 rounded-lg">
            <div className="text-blue-600">{icon}</div>
          </div>
          <div>
            <p className="text-sm font-medium text-gray-600">{title}</p>
            <p className="text-2xl font-bold text-gray-900">{value}</p>
          </div>
        </div>
      </div>
      {trend && (
        <div className="mt-4 flex items-center space-x-2">
          <div
            className={clsx(
              'flex items-center space-x-1 text-sm',
              trend.isPositive ? 'text-green-600' : 'text-red-600'
            )}
          >
            {trend.isPositive ? (
              <TrendingUp className="h-4 w-4" />
            ) : (
              <TrendingDown className="h-4 w-4" />
            )}
            <span>{trend.isPositive ? '+' : '-'}{Math.abs(trend.value)}</span>
          </div>
          <span className="text-sm text-gray-500">{trend.label}</span>
        </div>
      )}
    </Card>
  )
}