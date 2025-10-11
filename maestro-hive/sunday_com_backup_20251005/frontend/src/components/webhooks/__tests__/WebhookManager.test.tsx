import React from 'react'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { WebhookManager } from '../WebhookManager'
import { useWebhookStore } from '@/stores/webhook.store'
import type { Webhook, WebhookDelivery } from '@/types'

// Mock the webhook store
jest.mock('@/stores/webhook.store')

const mockUseWebhookStore = useWebhookStore as jest.MockedFunction<typeof useWebhookStore>

const mockWebhook: Webhook = {
  id: 'webhook-1',
  name: 'Test Webhook',
  url: 'https://example.com/webhook',
  events: ['item.created', 'item.updated'],
  isActive: true,
  secret: 'whsec_test123',
  organizationId: 'org-1',
  createdAt: '2023-01-01T00:00:00Z',
  updatedAt: '2023-01-01T00:00:00Z',
  deliveryCount: 15,
  failureCount: 2,
  lastDeliveryAt: '2023-01-02T10:00:00Z',
}

const mockDelivery: WebhookDelivery = {
  id: 'delivery-1',
  webhookId: 'webhook-1',
  eventType: 'item.created',
  status: 'success',
  responseStatus: 200,
  responseTime: 150,
  payload: { test: 'data' },
  createdAt: '2023-01-02T10:00:00Z',
  retryCount: 0,
}

const mockWebhookStore = {
  webhooks: [],
  deliveries: {},
  availableEvents: ['item.created', 'item.updated', 'board.created'],
  loading: {
    webhooks: false,
    deliveries: {},
    creating: false,
    updating: false,
    deleting: false,
    testing: false,
    retrying: false,
  },
  errors: {
    webhooks: null,
    deliveries: {},
    creating: null,
    updating: null,
    deleting: null,
    testing: null,
    retrying: null,
  },
  createWebhook: jest.fn(),
  fetchWebhooks: jest.fn(),
  updateWebhook: jest.fn(),
  deleteWebhook: jest.fn(),
  testWebhook: jest.fn(),
  fetchDeliveries: jest.fn(),
  retryDelivery: jest.fn(),
  setScope: jest.fn(),
}

describe('WebhookManager', () => {
  beforeEach(() => {
    jest.clearAllMocks()
    mockUseWebhookStore.mockReturnValue(mockWebhookStore)
  })

  it('renders empty state when no webhooks exist', () => {
    render(<WebhookManager organizationId="org-1" />)

    expect(screen.getByText('Webhooks')).toBeInTheDocument()
    expect(screen.getByText('No webhooks configured')).toBeInTheDocument()
    expect(screen.getByText('Get started by creating your first webhook to receive real-time notifications.')).toBeInTheDocument()
  })

  it('renders webhooks list when webhooks exist', () => {
    const storeWithWebhooks = {
      ...mockWebhookStore,
      webhooks: [mockWebhook],
    }
    mockUseWebhookStore.mockReturnValue(storeWithWebhooks)

    render(<WebhookManager organizationId="org-1" />)

    expect(screen.getByText('Test Webhook')).toBeInTheDocument()
    expect(screen.getByText('https://example.com/webhook')).toBeInTheDocument()
    expect(screen.getByText('Active')).toBeInTheDocument()
    expect(screen.getByText('15 deliveries')).toBeInTheDocument()
    expect(screen.getByText('2 failures')).toBeInTheDocument()
  })

  it('opens create webhook modal when add button is clicked', async () => {
    const user = userEvent.setup()
    render(<WebhookManager organizationId="org-1" />)

    await user.click(screen.getByText('Add Webhook'))

    expect(screen.getByText('Create Webhook')).toBeInTheDocument()
    expect(screen.getByLabelText('Name *')).toBeInTheDocument()
    expect(screen.getByLabelText('URL *')).toBeInTheDocument()
  })

  it('creates webhook with correct data', async () => {
    const user = userEvent.setup()
    mockWebhookStore.createWebhook.mockResolvedValue(mockWebhook)

    render(<WebhookManager organizationId="org-1" />)

    await user.click(screen.getByText('Add Webhook'))

    // Fill out form
    await user.type(screen.getByLabelText('Name *'), 'New Webhook')
    await user.type(screen.getByLabelText('URL *'), 'https://example.com/new-webhook')

    // Select events
    const itemCreatedCheckbox = screen.getByLabelText(/item.created/)
    await user.click(itemCreatedCheckbox)

    // Submit form
    await user.click(screen.getByText('Create'))

    await waitFor(() => {
      expect(mockWebhookStore.createWebhook).toHaveBeenCalledWith({
        name: 'New Webhook',
        url: 'https://example.com/new-webhook',
        events: ['item.created'],
        isActive: true,
        organizationId: 'org-1',
        workspaceId: undefined,
        boardId: undefined,
      })
    })
  })

  it('shows and hides webhook secret', async () => {
    const user = userEvent.setup()
    const storeWithWebhooks = {
      ...mockWebhookStore,
      webhooks: [mockWebhook],
    }
    mockUseWebhookStore.mockReturnValue(storeWithWebhooks)

    render(<WebhookManager organizationId="org-1" />)

    // Secret should be hidden by default
    expect(screen.getByText('•'.repeat(mockWebhook.secret.length))).toBeInTheDocument()

    // Show secret
    const eyeButton = screen.getByRole('button', { name: /eye/i })
    await user.click(eyeButton)

    expect(screen.getByText('whsec_test123')).toBeInTheDocument()
  })

  it('tests webhook when test button is clicked', async () => {
    const user = userEvent.setup()
    const storeWithWebhooks = {
      ...mockWebhookStore,
      webhooks: [mockWebhook],
    }
    mockUseWebhookStore.mockReturnValue(storeWithWebhooks)

    render(<WebhookManager organizationId="org-1" />)

    await user.click(screen.getByText('Test'))

    await waitFor(() => {
      expect(mockWebhookStore.testWebhook).toHaveBeenCalledWith('webhook-1')
    })
  })

  it('deletes webhook with confirmation', async () => {
    const user = userEvent.setup()
    const storeWithWebhooks = {
      ...mockWebhookStore,
      webhooks: [mockWebhook],
    }
    mockUseWebhookStore.mockReturnValue(storeWithWebhooks)

    // Mock window.confirm
    jest.spyOn(window, 'confirm').mockReturnValue(true)

    render(<WebhookManager organizationId="org-1" />)

    const deleteButton = screen.getByRole('button', { name: /trash/i })
    await user.click(deleteButton)

    await waitFor(() => {
      expect(mockWebhookStore.deleteWebhook).toHaveBeenCalledWith('webhook-1')
    })
  })

  it('opens deliveries modal and shows delivery history', async () => {
    const user = userEvent.setup()
    const storeWithWebhooks = {
      ...mockWebhookStore,
      webhooks: [mockWebhook],
      deliveries: { 'webhook-1': [mockDelivery] },
    }
    mockUseWebhookStore.mockReturnValue(storeWithWebhooks)

    render(<WebhookManager organizationId="org-1" />)

    await user.click(screen.getByText('View Deliveries'))

    expect(screen.getByText('Webhook Deliveries')).toBeInTheDocument()
    expect(mockWebhookStore.fetchDeliveries).toHaveBeenCalledWith('webhook-1')

    // Should show delivery details
    expect(screen.getByText('item.created')).toBeInTheDocument()
    expect(screen.getByText('success')).toBeInTheDocument()
    expect(screen.getByText('HTTP 200')).toBeInTheDocument()
  })

  it('retries failed delivery', async () => {
    const user = userEvent.setup()
    const failedDelivery: WebhookDelivery = {
      ...mockDelivery,
      status: 'failed',
      errorMessage: 'Connection timeout',
    }

    const storeWithWebhooks = {
      ...mockWebhookStore,
      webhooks: [mockWebhook],
      deliveries: { 'webhook-1': [failedDelivery] },
    }
    mockUseWebhookStore.mockReturnValue(storeWithWebhooks)

    render(<WebhookManager organizationId="org-1" />)

    await user.click(screen.getByText('View Deliveries'))

    const retryButton = screen.getByRole('button', { name: /rotateccw/i })
    await user.click(retryButton)

    await waitFor(() => {
      expect(mockWebhookStore.retryDelivery).toHaveBeenCalledWith('delivery-1')
    })
  })

  it('shows loading state when fetching webhooks', () => {
    const loadingStore = {
      ...mockWebhookStore,
      loading: { ...mockWebhookStore.loading, webhooks: true },
    }
    mockUseWebhookStore.mockReturnValue(loadingStore)

    render(<WebhookManager organizationId="org-1" />)

    expect(screen.getByText('Loading webhooks...')).toBeInTheDocument()
  })

  it('shows error state when webhook fetching fails', () => {
    const errorStore = {
      ...mockWebhookStore,
      errors: { ...mockWebhookStore.errors, webhooks: 'Failed to load webhooks' },
    }
    mockUseWebhookStore.mockReturnValue(errorStore)

    render(<WebhookManager organizationId="org-1" />)

    expect(screen.getByText('Failed to load webhooks')).toBeInTheDocument()
  })

  it('sets correct scope on mount', () => {
    render(<WebhookManager organizationId="org-1" workspaceId="workspace-1" />)

    expect(mockWebhookStore.setScope).toHaveBeenCalledWith({
      organizationId: 'org-1',
      workspaceId: 'workspace-1',
      boardId: undefined,
    })

    expect(mockWebhookStore.fetchWebhooks).toHaveBeenCalledWith({
      organizationId: 'org-1',
      workspaceId: 'workspace-1',
      boardId: undefined,
    })
  })

  it('validates form before submission', async () => {
    const user = userEvent.setup()
    render(<WebhookManager organizationId="org-1" />)

    await user.click(screen.getByText('Add Webhook'))

    // Try to submit without required fields
    const createButton = screen.getByText('Create')
    expect(createButton).toBeDisabled()

    // Fill name and URL but no events
    await user.type(screen.getByLabelText('Name *'), 'Test')
    await user.type(screen.getByLabelText('URL *'), 'https://example.com')

    // Should still be disabled without events
    expect(createButton).toBeDisabled()

    // Add an event
    const eventCheckbox = screen.getByLabelText(/item.created/)
    await user.click(eventCheckbox)

    // Now should be enabled
    expect(createButton).not.toBeDisabled()
  })

  it('shows inactive webhook status correctly', () => {
    const inactiveWebhook = { ...mockWebhook, isActive: false }
    const storeWithWebhooks = {
      ...mockWebhookStore,
      webhooks: [inactiveWebhook],
    }
    mockUseWebhookStore.mockReturnValue(storeWithWebhooks)

    render(<WebhookManager organizationId="org-1" />)

    expect(screen.getByText('Inactive')).toBeInTheDocument()
  })

  it('copies secret to clipboard', async () => {
    const user = userEvent.setup()
    const storeWithWebhooks = {
      ...mockWebhookStore,
      webhooks: [mockWebhook],
    }
    mockUseWebhookStore.mockReturnValue(storeWithWebhooks)

    // Mock clipboard API
    Object.assign(navigator, {
      clipboard: {
        writeText: jest.fn(),
      },
    })

    // Mock alert
    jest.spyOn(window, 'alert').mockImplementation(() => {})

    render(<WebhookManager organizationId="org-1" />)

    const copyButton = screen.getByRole('button', { name: /copy/i })
    await user.click(copyButton)

    expect(navigator.clipboard.writeText).toHaveBeenCalledWith('whsec_test123')
    expect(window.alert).toHaveBeenCalledWith('Secret copied to clipboard!')
  })

  afterEach(() => {
    jest.restoreAllMocks()
  })
})