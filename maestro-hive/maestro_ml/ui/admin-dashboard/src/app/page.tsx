"use client"

import { useState, useEffect } from 'react'
import { useQuery } from '@tanstack/react-query'
import {
  BarChart3,
  Users,
  Folder,
  Activity,
  TrendingUp,
  AlertCircle,
  CheckCircle
} from 'lucide-react'
import { Line, Bar } from 'recharts'

// API client
import { apiClient } from '@/lib/api'

// Components
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card'
import { MetricCard } from '@/components/dashboard/metric-card'
import { ProjectsTable } from '@/components/dashboard/projects-table'
import { RecentActivity } from '@/components/dashboard/recent-activity'
import { SystemHealth } from '@/components/dashboard/system-health'

export default function DashboardPage() {
  const [timeRange, setTimeRange] = useState('7d')

  // Fetch dashboard metrics
  const { data: metrics, isLoading: metricsLoading } = useQuery({
    queryKey: ['dashboard-metrics', timeRange],
    queryFn: () => apiClient.getDashboardMetrics(timeRange)
  })

  // Fetch projects
  const { data: projects, isLoading: projectsLoading } = useQuery({
    queryKey: ['projects'],
    queryFn: () => apiClient.getProjects({ limit: 10 })
  })

  // Fetch system health
  const { data: health, isLoading: healthLoading } = useQuery({
    queryKey: ['system-health'],
    queryFn: () => apiClient.getSystemHealth(),
    refetchInterval: 30000 // Refresh every 30 seconds
  })

  // Fetch activity feed
  const { data: activity, isLoading: activityLoading } = useQuery({
    queryKey: ['activity-feed'],
    queryFn: () => apiClient.getActivityFeed({ limit: 20 })
  })

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white border-b border-gray-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
          <div className="flex justify-between items-center">
            <div>
              <h1 className="text-2xl font-bold text-gray-900">
                Maestro ML Platform
              </h1>
              <p className="text-sm text-gray-600 mt-1">
                Admin Dashboard
              </p>
            </div>
            <div className="flex gap-3">
              <select
                value={timeRange}
                onChange={(e) => setTimeRange(e.target.value)}
                className="px-3 py-2 border border-gray-300 rounded-lg text-sm"
              >
                <option value="24h">Last 24 hours</option>
                <option value="7d">Last 7 days</option>
                <option value="30d">Last 30 days</option>
                <option value="90d">Last 90 days</option>
              </select>
            </div>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Metrics Overview */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
          <MetricCard
            title="Total Projects"
            value={metrics?.total_projects || 0}
            change={metrics?.projects_change || 0}
            icon={Folder}
            loading={metricsLoading}
          />
          <MetricCard
            title="Active Models"
            value={metrics?.active_models || 0}
            change={metrics?.models_change || 0}
            icon={BarChart3}
            loading={metricsLoading}
          />
          <MetricCard
            title="Total Users"
            value={metrics?.total_users || 0}
            change={metrics?.users_change || 0}
            icon={Users}
            loading={metricsLoading}
          />
          <MetricCard
            title="API Requests"
            value={metrics?.api_requests || 0}
            change={metrics?.requests_change || 0}
            icon={Activity}
            loading={metricsLoading}
          />
        </div>

        {/* Charts Row */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
          {/* Projects Over Time */}
          <Card>
            <CardHeader>
              <CardTitle>Projects Created</CardTitle>
            </CardHeader>
            <CardContent>
              {metricsLoading ? (
                <div className="h-64 flex items-center justify-center">
                  <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
                </div>
              ) : (
                <div className="h-64">
                  {/* Chart implementation would go here */}
                  <p className="text-sm text-gray-500">Chart: Projects over time</p>
                </div>
              )}
            </CardContent>
          </Card>

          {/* Model Performance */}
          <Card>
            <CardHeader>
              <CardTitle>Model Training Success Rate</CardTitle>
            </CardHeader>
            <CardContent>
              {metricsLoading ? (
                <div className="h-64 flex items-center justify-center">
                  <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
                </div>
              ) : (
                <div className="h-64">
                  {/* Chart implementation would go here */}
                  <p className="text-sm text-gray-500">Chart: Success rate over time</p>
                </div>
              )}
            </CardContent>
          </Card>
        </div>

        {/* System Health */}
        <div className="mb-8">
          <SystemHealth health={health} loading={healthLoading} />
        </div>

        {/* Tables Row */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Recent Projects */}
          <Card>
            <CardHeader>
              <CardTitle>Recent Projects</CardTitle>
            </CardHeader>
            <CardContent>
              <ProjectsTable
                projects={projects?.data || []}
                loading={projectsLoading}
              />
            </CardContent>
          </Card>

          {/* Recent Activity */}
          <Card>
            <CardHeader>
              <CardTitle>Recent Activity</CardTitle>
            </CardHeader>
            <CardContent>
              <RecentActivity
                activities={activity?.data || []}
                loading={activityLoading}
              />
            </CardContent>
          </Card>
        </div>
      </main>
    </div>
  )
}
