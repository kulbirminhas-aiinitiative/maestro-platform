import React from 'react'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { AnalyticsDashboard } from '../AnalyticsDashboard'
import { useAnalyticsStore } from '@/stores/analytics.store'
import { useAuth } from '@/hooks/useAuth'
import type { BoardAnalytics, OrganizationAnalytics, AnalyticsData } from '@/types'

// Mock the stores and hooks
jest.mock('@/stores/analytics.store')
jest.mock('@/hooks/useAuth')

// Mock recharts
jest.mock('recharts', () => ({
  ResponsiveContainer: ({ children }: any) => <div data-testid="responsive-container">{children}</div>,
  LineChart: ({ children }: any) => <div data-testid="line-chart">{children}</div>,
  Line: () => <div data-testid="line" />,
  XAxis: () => <div data-testid="x-axis" />,
  YAxis: () => <div data-testid="y-axis" />,
  CartesianGrid: () => <div data-testid="cartesian-grid" />,
  Tooltip: () => <div data-testid="tooltip" />,
  BarChart: ({ children }: any) => <div data-testid="bar-chart">{children}</div>,
  Bar: () => <div data-testid="bar" />,
  PieChart: ({ children }: any) => <div data-testid="pie-chart">{children}</div>,
  Pie: () => <div data-testid="pie" />,
  Cell: () => <div data-testid="cell" />,
  Legend: () => <div data-testid="legend" />,
}))

const mockUseAnalyticsStore = useAnalyticsStore as jest.MockedFunction<typeof useAnalyticsStore>
const mockUseAuth = useAuth as jest.MockedFunction<typeof useAuth>

const mockDashboardData: AnalyticsData = {
  totalItems: 150,
  completedItems: 120,
  activeUsers: 25,
  averageCompletionTime: 3600,
  productivityScore: 85,
  trends: [
    { date: '2023-01-01', value: 10, metric: 'completed' },
    { date: '2023-01-02', value: 12, metric: 'completed' },
    { date: '2023-01-03', value: 8, metric: 'completed' },
  ],
}

const mockBoardAnalytics: BoardAnalytics = {
  boardId: 'board-1',
  boardName: 'Test Board',
  totalItems: 50,
  completedItems: 35,
  completionRate: 70,
  averageTimeToComplete: 2400,
  velocity: {
    itemsCompletedLastWeek: 15,
    itemsCompletedThisWeek: 18,
    averageCompletionTime: 2400,
    velocity: 1.2,
  },
  memberActivity: [
    { userId: 'user-1', userName: 'John Doe', itemsCreated: 10, itemsCompleted: 8, timeSpent: 7200, activityScore: 85 },
    { userId: 'user-2', userName: 'Jane Smith', itemsCreated: 15, itemsCompleted: 12, timeSpent: 9600, activityScore: 92 },
  ],
  itemDistribution: [
    { status: 'todo', count: 10, percentage: 20 },
    { status: 'in_progress', count: 5, percentage: 10 },
    { status: 'done', count: 35, percentage: 70 },
  ],
  trends: [
    { date: '2023-01-01', value: 5, metric: 'completed' },
    { date: '2023-01-02', value: 7, metric: 'completed' },
    { date: '2023-01-03', value: 4, metric: 'completed' },
  ],
}

const mockAnalyticsStore = {
  dashboardOverview: null,
  boardAnalytics: {},
  organizationAnalytics: {},
  loading: {
    dashboardOverview: false,
    boardAnalytics: {},
    organizationAnalytics: {},
    export: false,
  },
  errors: {
    dashboardOverview: null,
    boardAnalytics: {},
    organizationAnalytics: {},
    export: null,
  },
  fetchDashboardOverview: jest.fn(),
  fetchBoardAnalytics: jest.fn(),
  fetchOrganizationAnalytics: jest.fn(),
  exportData: jest.fn(),
}

describe('AnalyticsDashboard', () => {
  beforeEach(() => {
    jest.clearAllMocks()

    mockUseAuth.mockReturnValue({
      user: {
        id: 'user-1',
        email: 'test@example.com',
        fullName: 'Test User',
        firstName: 'Test',
        lastName: 'User',
        timezone: 'UTC',
        locale: 'en',
        settings: {},
        createdAt: '2023-01-01T00:00:00Z',
        updatedAt: '2023-01-01T00:00:00Z',
      },
      isAuthenticated: true,
      login: jest.fn(),
      logout: jest.fn(),
      register: jest.fn(),
      updateProfile: jest.fn(),
      loading: false,
    })

    mockUseAnalyticsStore.mockReturnValue(mockAnalyticsStore)
  })

  it('renders analytics dashboard with default data', () => {
    const storeWithData = {
      ...mockAnalyticsStore,
      dashboardOverview: mockDashboardData,
    }
    mockUseAnalyticsStore.mockReturnValue(storeWithData)

    render(<AnalyticsDashboard />)

    expect(screen.getByText('Analytics')).toBeInTheDocument()
    expect(screen.getByText('Total Items')).toBeInTheDocument()
    expect(screen.getByText('150')).toBeInTheDocument()
    expect(screen.getByText('Completed Items')).toBeInTheDocument()
    expect(screen.getByText('120')).toBeInTheDocument()
  })

  it('renders board-specific analytics', () => {
    const storeWithBoardData = {
      ...mockAnalyticsStore,
      boardAnalytics: { 'board-1': mockBoardAnalytics },
    }
    mockUseAnalyticsStore.mockReturnValue(storeWithBoardData)

    render(<AnalyticsDashboard boardId="board-1" />)

    expect(screen.getByText('Analytics')).toBeInTheDocument()
    expect(screen.getByText('50')).toBeInTheDocument() // Total items
    expect(screen.getByText('35')).toBeInTheDocument() // Completed items
  })

  it('shows loading state', () => {
    const loadingStore = {
      ...mockAnalyticsStore,
      loading: { ...mockAnalyticsStore.loading, dashboardOverview: true },
    }
    mockUseAnalyticsStore.mockReturnValue(loadingStore)

    render(<AnalyticsDashboard />)

    expect(screen.getByText('Loading analytics...')).toBeInTheDocument()
  })

  it('shows error state', () => {
    const errorStore = {
      ...mockAnalyticsStore,
      errors: { ...mockAnalyticsStore.errors, dashboardOverview: 'Failed to load analytics' },
    }
    mockUseAnalyticsStore.mockReturnValue(errorStore)

    render(<AnalyticsDashboard />)

    expect(screen.getByText('Error loading analytics')).toBeInTheDocument()
    expect(screen.getByText('Failed to load analytics')).toBeInTheDocument()
  })

  it('shows no data state', () => {
    render(<AnalyticsDashboard />)

    expect(screen.getByText('No data available')).toBeInTheDocument()
    expect(screen.getByText('Analytics data will appear here once you have some activity.')).toBeInTheDocument()
  })

  it('fetches dashboard overview on mount', () => {
    render(<AnalyticsDashboard />)

    expect(mockAnalyticsStore.fetchDashboardOverview).toHaveBeenCalled()
  })

  it('fetches board analytics when boardId is provided', () => {
    render(<AnalyticsDashboard boardId="board-1" />)

    expect(mockAnalyticsStore.fetchBoardAnalytics).toHaveBeenCalledWith('board-1', expect.any(Object))
  })

  it('fetches organization analytics when organizationId is provided', () => {
    render(<AnalyticsDashboard organizationId="org-1" />)

    expect(mockAnalyticsStore.fetchOrganizationAnalytics).toHaveBeenCalledWith('org-1', expect.any(Object))
  })

  it('changes time range and refetches data', async () => {
    const storeWithData = {
      ...mockAnalyticsStore,
      dashboardOverview: mockDashboardData,
    }
    mockUseAnalyticsStore.mockReturnValue(storeWithData)

    render(<AnalyticsDashboard />)

    const sevenDaysButton = screen.getByText('7 days')
    fireEvent.click(sevenDaysButton)

    await waitFor(() => {
      expect(mockAnalyticsStore.fetchDashboardOverview).toHaveBeenCalledTimes(2)
    })
  })

  it('exports data when export button is clicked', async () => {
    const storeWithData = {
      ...mockAnalyticsStore,
      dashboardOverview: mockDashboardData,
    }
    mockUseAnalyticsStore.mockReturnValue(storeWithData)

    render(<AnalyticsDashboard />)

    const exportButton = screen.getByText('Export')
    fireEvent.click(exportButton)

    await waitFor(() => {
      expect(mockAnalyticsStore.exportData).toHaveBeenCalledWith(
        expect.objectContaining({
          format: 'csv',
        })
      )
    })
  })

  it('calculates completion rate correctly', () => {
    const storeWithData = {
      ...mockAnalyticsStore,
      dashboardOverview: mockDashboardData,
    }
    mockUseAnalyticsStore.mockReturnValue(storeWithData)

    render(<AnalyticsDashboard />)

    // 120 completed / 150 total = 80%
    expect(screen.getByText('80%')).toBeInTheDocument()
  })

  it('renders trends chart', () => {
    const storeWithData = {
      ...mockAnalyticsStore,
      dashboardOverview: mockDashboardData,
    }
    mockUseAnalyticsStore.mockReturnValue(storeWithData)

    render(<AnalyticsDashboard />)

    expect(screen.getByText('Activity Trends')).toBeInTheDocument()
    expect(screen.getByTestId('line-chart')).toBeInTheDocument()
  })

  it('renders board-specific charts when board analytics available', () => {
    const storeWithBoardData = {
      ...mockAnalyticsStore,
      boardAnalytics: { 'board-1': mockBoardAnalytics },
    }
    mockUseAnalyticsStore.mockReturnValue(storeWithBoardData)

    render(<AnalyticsDashboard boardId="board-1" />)

    expect(screen.getByText('Item Status Distribution')).toBeInTheDocument()
    expect(screen.getByText('Member Activity')).toBeInTheDocument()
    expect(screen.getByText('Velocity')).toBeInTheDocument()
    expect(screen.getByTestId('pie-chart')).toBeInTheDocument()
    expect(screen.getByTestId('bar-chart')).toBeInTheDocument()
  })

  it('displays velocity metrics correctly', () => {
    const storeWithBoardData = {
      ...mockAnalyticsStore,
      boardAnalytics: { 'board-1': mockBoardAnalytics },
    }
    mockUseAnalyticsStore.mockReturnValue(storeWithBoardData)

    render(<AnalyticsDashboard boardId="board-1" />)

    expect(screen.getByText('18')).toBeInTheDocument() // This week
    expect(screen.getByText('15')).toBeInTheDocument() // Last week
    expect(screen.getByText('1h')).toBeInTheDocument() // Average completion time in hours
  })

  it('shows positive and negative trends correctly', () => {
    const storeWithData = {
      ...mockAnalyticsStore,
      dashboardOverview: mockDashboardData,
    }
    mockUseAnalyticsStore.mockReturnValue(storeWithData)

    render(<AnalyticsDashboard />)

    // Check for trend indicators
    expect(screen.getAllByText('vs last period')).toHaveLength(3)
    expect(screen.getByText('percentage points')).toBeInTheDocument()
  })

  it('renders recent activity section', () => {
    const storeWithData = {
      ...mockAnalyticsStore,
      dashboardOverview: mockDashboardData,
    }
    mockUseAnalyticsStore.mockReturnValue(storeWithData)

    render(<AnalyticsDashboard />)

    expect(screen.getByText('Recent Activity')).toBeInTheDocument()
    expect(screen.getByText('Live Data')).toBeInTheDocument()
  })

  afterEach(() => {
    jest.restoreAllMocks()
  })
})