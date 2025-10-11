import React, { ReactElement } from 'react'
import { render, RenderOptions, screen, waitFor, fireEvent } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { BrowserRouter } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { create } from 'zustand'

// Types for test utilities
export interface MockUser {
  id: string
  email: string
  firstName: string
  lastName: string
  avatarUrl?: string
  organizations: Array<{
    id: string
    name: string
    role: string
  }>
}

export interface MockOrganization {
  id: string
  name: string
  slug: string
  memberCount: number
  workspaceCount: number
}

export interface MockWorkspace {
  id: string
  name: string
  organizationId: string
  boardCount: number
}

export interface MockBoard {
  id: string
  name: string
  workspaceId: string
  itemCount: number
  view: 'table' | 'kanban' | 'timeline' | 'calendar'
}

export interface MockTask {
  id: string
  name: string
  status: string
  priority?: string
  assignee?: MockUser
  dueDate?: string
  boardId: string
}

/**
 * Test data factory for frontend components
 */
export class FrontendTestFactory {
  static createMockUser(userData: Partial<MockUser> = {}): MockUser {
    return {
      id: userData.id || `user-${Math.random().toString(36).substr(2, 9)}`,
      email: userData.email || 'test@example.com',
      firstName: userData.firstName || 'Test',
      lastName: userData.lastName || 'User',
      avatarUrl: userData.avatarUrl,
      organizations: userData.organizations || [
        {
          id: 'org-1',
          name: 'Test Organization',
          role: 'admin',
        },
      ],
    }
  }

  static createMockOrganization(orgData: Partial<MockOrganization> = {}): MockOrganization {
    return {
      id: orgData.id || `org-${Math.random().toString(36).substr(2, 9)}`,
      name: orgData.name || 'Test Organization',
      slug: orgData.slug || 'test-org',
      memberCount: orgData.memberCount || 5,
      workspaceCount: orgData.workspaceCount || 3,
    }
  }

  static createMockWorkspace(workspaceData: Partial<MockWorkspace> = {}): MockWorkspace {
    return {
      id: workspaceData.id || `workspace-${Math.random().toString(36).substr(2, 9)}`,
      name: workspaceData.name || 'Test Workspace',
      organizationId: workspaceData.organizationId || 'org-1',
      boardCount: workspaceData.boardCount || 2,
    }
  }

  static createMockBoard(boardData: Partial<MockBoard> = {}): MockBoard {
    return {
      id: boardData.id || `board-${Math.random().toString(36).substr(2, 9)}`,
      name: boardData.name || 'Test Board',
      workspaceId: boardData.workspaceId || 'workspace-1',
      itemCount: boardData.itemCount || 10,
      view: boardData.view || 'table',
    }
  }

  static createMockTask(taskData: Partial<MockTask> = {}): MockTask {
    return {
      id: taskData.id || `task-${Math.random().toString(36).substr(2, 9)}`,
      name: taskData.name || 'Test Task',
      status: taskData.status || 'Not Started',
      priority: taskData.priority,
      assignee: taskData.assignee,
      dueDate: taskData.dueDate,
      boardId: taskData.boardId || 'board-1',
    }
  }

  static createMockTasks(count: number, boardId?: string): MockTask[] {
    return Array.from({ length: count }, (_, index) =>
      this.createMockTask({
        name: `Test Task ${index + 1}`,
        status: ['Not Started', 'In Progress', 'Completed'][index % 3],
        boardId,
      })
    )
  }
}

/**
 * Mock store creators for testing
 */
export const createMockAuthStore = (initialUser?: MockUser) => {
  return create<{
    user: MockUser | null
    isAuthenticated: boolean
    login: (user: MockUser) => void
    logout: () => void
  }>((set) => ({
    user: initialUser || null,
    isAuthenticated: !!initialUser,
    login: (user) => set({ user, isAuthenticated: true }),
    logout: () => set({ user: null, isAuthenticated: false }),
  }))
}

export const createMockUIStore = () => {
  return create<{
    sidebarOpen: boolean
    setSidebarOpen: (open: boolean) => void
    theme: 'light' | 'dark'
    setTheme: (theme: 'light' | 'dark') => void
  }>((set) => ({
    sidebarOpen: false,
    setSidebarOpen: (open) => set({ sidebarOpen: open }),
    theme: 'light',
    setTheme: (theme) => set({ theme }),
  }))
}

/**
 * API mock utilities
 */
export class ApiMockUtils {
  static mockFetch(mockData: any, status = 200) {
    const mockFetch = global.fetch as jest.MockedFunction<typeof fetch>
    mockFetch.mockResolvedValueOnce({
      ok: status >= 200 && status < 300,
      status,
      json: async () => ({
        success: status >= 200 && status < 300,
        data: mockData,
      }),
    } as Response)
  }

  static mockFetchError(error: string, status = 400) {
    const mockFetch = global.fetch as jest.MockedFunction<typeof fetch>
    mockFetch.mockResolvedValueOnce({
      ok: false,
      status,
      json: async () => ({
        success: false,
        error,
      }),
    } as Response)
  }

  static mockFetchReject(error: Error) {
    const mockFetch = global.fetch as jest.MockedFunction<typeof fetch>
    mockFetch.mockRejectedValueOnce(error)
  }

  static clearFetchMocks() {
    const mockFetch = global.fetch as jest.MockedFunction<typeof fetch>
    mockFetch.mockClear()
  }
}

/**
 * Custom render function with providers
 */
interface CustomRenderOptions extends Omit<RenderOptions, 'wrapper'> {
  user?: MockUser
  initialRoute?: string
  queryClient?: QueryClient
}

function createTestQueryClient() {
  return new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
        gcTime: 0,
      },
      mutations: {
        retry: false,
      },
    },
  })
}

function AllTheProviders({ children, user, initialRoute = '/', queryClient }: {
  children: React.ReactNode
  user?: MockUser
  initialRoute?: string
  queryClient?: QueryClient
}) {
  const testQueryClient = queryClient || createTestQueryClient()

  // Mock the auth store if user is provided
  if (user) {
    // Set up global auth state mock
    Object.defineProperty(window, '__TEST_AUTH_USER__', {
      value: user,
      writable: true,
    })
  }

  return (
    <QueryClientProvider client={testQueryClient}>
      <BrowserRouter>
        {children}
      </BrowserRouter>
    </QueryClientProvider>
  )
}

export function renderWithProviders(
  ui: ReactElement,
  options: CustomRenderOptions = {}
) {
  const { user, initialRoute, queryClient, ...renderOptions } = options

  function Wrapper({ children }: { children: React.ReactNode }) {
    return (
      <AllTheProviders user={user} initialRoute={initialRoute} queryClient={queryClient}>
        {children}
      </AllTheProviders>
    )
  }

  return {
    user: userEvent.setup(),
    ...render(ui, { wrapper: Wrapper, ...renderOptions }),
  }
}

/**
 * Common test utilities
 */
export class TestHelpers {
  /**
   * Wait for element to appear with custom timeout
   */
  static async waitForElement(
    selector: string,
    timeout = 3000
  ): Promise<HTMLElement> {
    return await waitFor(
      () => {
        const element = screen.getByTestId(selector)
        expect(element).toBeInTheDocument()
        return element
      },
      { timeout }
    )
  }

  /**
   * Wait for element to disappear
   */
  static async waitForElementToDisappear(
    selector: string,
    timeout = 3000
  ): Promise<void> {
    await waitFor(
      () => {
        expect(screen.queryByTestId(selector)).not.toBeInTheDocument()
      },
      { timeout }
    )
  }

  /**
   * Fill and submit a form
   */
  static async fillAndSubmitForm(
    formData: Record<string, string>,
    submitButtonText = 'Submit'
  ) {
    const user = userEvent.setup()

    // Fill form fields
    for (const [field, value] of Object.entries(formData)) {
      const input = screen.getByLabelText(new RegExp(field, 'i'))
      await user.clear(input)
      await user.type(input, value)
    }

    // Submit form
    const submitButton = screen.getByRole('button', { name: new RegExp(submitButtonText, 'i') })
    await user.click(submitButton)
  }

  /**
   * Test component accessibility
   */
  static async testAccessibility(component: ReactElement) {
    const { container } = renderWithProviders(component)

    // Test keyboard navigation
    const focusableElements = container.querySelectorAll(
      'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
    )

    // Ensure all interactive elements are focusable
    focusableElements.forEach((element) => {
      expect(element).toHaveAttribute('tabindex')
    })

    // Test ARIA attributes
    const elementsWithARIA = container.querySelectorAll('[aria-label], [aria-describedby], [role]')
    expect(elementsWithARIA.length).toBeGreaterThan(0)
  }

  /**
   * Test component loading states
   */
  static async testLoadingState(
    component: ReactElement,
    loadingText = 'Loading...'
  ) {
    renderWithProviders(component)

    // Should show loading initially
    expect(screen.getByText(loadingText)).toBeInTheDocument()

    // Wait for loading to complete
    await waitFor(() => {
      expect(screen.queryByText(loadingText)).not.toBeInTheDocument()
    })
  }

  /**
   * Test error states
   */
  static async testErrorState(
    component: ReactElement,
    errorMessage: string
  ) {
    // Mock API error
    ApiMockUtils.mockFetchError(errorMessage, 500)

    renderWithProviders(component)

    // Should show error message
    await waitFor(() => {
      expect(screen.getByText(errorMessage)).toBeInTheDocument()
    })
  }

  /**
   * Test responsive behavior
   */
  static testResponsive(component: ReactElement) {
    // Test mobile viewport
    global.innerWidth = 320
    global.dispatchEvent(new Event('resize'))

    const { rerender } = renderWithProviders(component)

    // Test tablet viewport
    global.innerWidth = 768
    global.dispatchEvent(new Event('resize'))
    rerender(component)

    // Test desktop viewport
    global.innerWidth = 1024
    global.dispatchEvent(new Event('resize'))
    rerender(component)

    // Reset to default
    global.innerWidth = 1024
  }
}

/**
 * Custom matchers for testing
 */
export const customMatchers = {
  toBeVisible: (received: HTMLElement) => {
    const pass = received.style.display !== 'none' && received.style.visibility !== 'hidden'
    return {
      message: () => `expected element to ${pass ? 'not ' : ''}be visible`,
      pass,
    }
  },

  toHaveClass: (received: HTMLElement, className: string) => {
    const pass = received.classList.contains(className)
    return {
      message: () => `expected element to ${pass ? 'not ' : ''}have class "${className}"`,
      pass,
    }
  },

  toBeDisabled: (received: HTMLElement) => {
    const pass = received.hasAttribute('disabled') || received.getAttribute('aria-disabled') === 'true'
    return {
      message: () => `expected element to ${pass ? 'not ' : ''}be disabled`,
      pass,
    }
  },
}

/**
 * Mock WebSocket for real-time features
 */
export class MockWebSocket {
  static instance: MockWebSocket | null = null
  public onopen: ((event: Event) => void) | null = null
  public onclose: ((event: CloseEvent) => void) | null = null
  public onmessage: ((event: MessageEvent) => void) | null = null
  public onerror: ((event: Event) => void) | null = null
  public readyState: number = WebSocket.CONNECTING

  constructor(url: string) {
    MockWebSocket.instance = this
    setTimeout(() => {
      this.readyState = WebSocket.OPEN
      if (this.onopen) {
        this.onopen(new Event('open'))
      }
    }, 100)
  }

  send(data: string) {
    // Mock sending data
    console.log('WebSocket mock send:', data)
  }

  close() {
    this.readyState = WebSocket.CLOSED
    if (this.onclose) {
      this.onclose(new CloseEvent('close'))
    }
  }

  static simulateMessage(data: any) {
    if (MockWebSocket.instance && MockWebSocket.instance.onmessage) {
      MockWebSocket.instance.onmessage(
        new MessageEvent('message', { data: JSON.stringify(data) })
      )
    }
  }

  static simulateError() {
    if (MockWebSocket.instance && MockWebSocket.instance.onerror) {
      MockWebSocket.instance.onerror(new Event('error'))
    }
  }

  static reset() {
    MockWebSocket.instance = null
  }
}

// Mock WebSocket globally
Object.defineProperty(global, 'WebSocket', {
  value: MockWebSocket,
  writable: true,
})

/**
 * Performance testing utilities
 */
export class PerformanceTestUtils {
  static measureRenderTime<T>(renderFn: () => T): { result: T; time: number } {
    const start = performance.now()
    const result = renderFn()
    const end = performance.now()
    return { result, time: end - start }
  }

  static async measureAsyncRenderTime<T>(renderFn: () => Promise<T>): Promise<{ result: T; time: number }> {
    const start = performance.now()
    const result = await renderFn()
    const end = performance.now()
    return { result, time: end - start }
  }

  static expectRenderTimeUnder(time: number, threshold: number) {
    expect(time).toBeLessThan(threshold)
  }
}

// Re-export everything from testing-library for convenience
export * from '@testing-library/react'
export { userEvent }
export { renderWithProviders as render }