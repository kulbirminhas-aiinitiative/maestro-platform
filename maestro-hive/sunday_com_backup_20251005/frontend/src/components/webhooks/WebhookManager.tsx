import React, { useEffect, useState } from 'react'
import { useWebhookStore, getWebhookEventDescription } from '@/stores/webhook.store'
import { Button } from '@/components/ui/Button'
import { Card } from '@/components/ui/Card'
import { Badge } from '@/components/ui/Badge'
import { Input } from '@/components/ui/Input'
import { LoadingScreen } from '@/components/ui/LoadingScreen'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from '@/components/ui/Dialog'
import {
  Plus,
  Settings,
  Trash2,
  Globe,
  AlertCircle,
  CheckCircle,
  XCircle,
  RotateCcw,
  Copy,
  Eye,
  EyeOff,
  TestTube,
} from 'lucide-react'
import { format } from 'date-fns'
import clsx from 'clsx'
import type { Webhook, CreateWebhookData, UpdateWebhookData } from '@/types'

interface WebhookManagerProps {
  className?: string
  organizationId?: string
  workspaceId?: string
  boardId?: string
}

export const WebhookManager: React.FC<WebhookManagerProps> = ({
  className,
  organizationId,
  workspaceId,
  boardId,
}) => {
  const [showCreateModal, setShowCreateModal] = useState(false)
  const [editingWebhook, setEditingWebhook] = useState<Webhook | null>(null)
  const [showSecret, setShowSecret] = useState<Record<string, boolean>>({})
  const [selectedWebhook, setSelectedWebhook] = useState<string | null>(null)

  const {
    webhooks,
    deliveries,
    availableEvents,
    loading,
    errors,
    fetchWebhooks,
    createWebhook,
    updateWebhook,
    deleteWebhook,
    testWebhook,
    fetchDeliveries,
    retryDelivery,
    setScope,
  } = useWebhookStore()

  // Set scope and fetch webhooks on mount
  useEffect(() => {
    const scope = { organizationId, workspaceId, boardId }
    setScope(scope)
    fetchWebhooks(scope)
  }, [organizationId, workspaceId, boardId, setScope, fetchWebhooks])

  const handleCreateWebhook = async (data: CreateWebhookData) => {
    try {
      await createWebhook({
        ...data,
        organizationId,
        workspaceId,
        boardId,
      })
      setShowCreateModal(false)
    } catch (error) {
      console.error('Failed to create webhook:', error)
    }
  }

  const handleUpdateWebhook = async (id: string, data: UpdateWebhookData) => {
    try {
      await updateWebhook(id, data)
      setEditingWebhook(null)
    } catch (error) {
      console.error('Failed to update webhook:', error)
    }
  }

  const handleDeleteWebhook = async (id: string) => {
    if (window.confirm('Are you sure you want to delete this webhook?')) {
      try {
        await deleteWebhook(id)
      } catch (error) {
        console.error('Failed to delete webhook:', error)
      }
    }
  }

  const handleTestWebhook = async (id: string) => {
    try {
      await testWebhook(id)
      alert('Test webhook sent successfully!')
    } catch (error) {
      console.error('Failed to test webhook:', error)
      alert('Failed to send test webhook')
    }
  }

  const handleCopySecret = (secret: string) => {
    navigator.clipboard.writeText(secret)
    alert('Secret copied to clipboard!')
  }

  const toggleSecret = (webhookId: string) => {
    setShowSecret(prev => ({
      ...prev,
      [webhookId]: !prev[webhookId],
    }))
  }

  const getStatusIcon = (webhook: Webhook) => {
    if (!webhook.isActive) {
      return <XCircle className="h-5 w-5 text-gray-400" />
    }
    if (webhook.failureCount > 0) {
      return <AlertCircle className="h-5 w-5 text-yellow-500" />
    }
    return <CheckCircle className="h-5 w-5 text-green-500" />
  }

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'success':
        return 'bg-green-100 text-green-800'
      case 'failed':
        return 'bg-red-100 text-red-800'
      case 'pending':
        return 'bg-blue-100 text-blue-800'
      case 'retrying':
        return 'bg-yellow-100 text-yellow-800'
      default:
        return 'bg-gray-100 text-gray-800'
    }
  }

  if (loading.webhooks) {
    return <LoadingScreen message="Loading webhooks..." />
  }

  return (
    <div className={clsx('space-y-6', className)}>
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-gray-900">Webhooks</h2>
          <p className="text-gray-500">
            Manage webhook integrations for real-time event notifications
          </p>
        </div>
        <Button
          onClick={() => setShowCreateModal(true)}
          className="flex items-center space-x-2"
        >
          <Plus className="h-4 w-4" />
          <span>Add Webhook</span>
        </Button>
      </div>

      {/* Error display */}
      {errors.webhooks && (
        <div className="bg-red-50 border border-red-200 rounded-md p-4">
          <p className="text-sm text-red-800">{errors.webhooks}</p>
        </div>
      )}

      {/* Webhooks List */}
      {webhooks.length === 0 ? (
        <Card className="p-8 text-center">
          <Globe className="h-12 w-12 text-gray-400 mx-auto mb-4" />
          <h3 className="text-lg font-medium text-gray-900 mb-2">No webhooks configured</h3>
          <p className="text-gray-500 mb-4">
            Get started by creating your first webhook to receive real-time notifications.
          </p>
          <Button onClick={() => setShowCreateModal(true)}>
            <Plus className="h-4 w-4 mr-2" />
            Create Webhook
          </Button>
        </Card>
      ) : (
        <div className="grid grid-cols-1 gap-6">
          {webhooks.map((webhook) => (
            <Card key={webhook.id} className="p-6">
              <div className="flex items-start justify-between">
                <div className="flex items-start space-x-4 flex-1">
                  {getStatusIcon(webhook)}
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center space-x-3 mb-2">
                      <h3 className="text-lg font-medium text-gray-900 truncate">
                        {webhook.name}
                      </h3>
                      <Badge variant={webhook.isActive ? 'default' : 'secondary'}>
                        {webhook.isActive ? 'Active' : 'Inactive'}
                      </Badge>
                    </div>

                    <div className="space-y-2">
                      <div>
                        <span className="text-sm font-medium text-gray-700">URL:</span>
                        <code className="ml-2 text-sm bg-gray-100 px-2 py-1 rounded">
                          {webhook.url}
                        </code>
                      </div>

                      <div>
                        <span className="text-sm font-medium text-gray-700">Events:</span>
                        <div className="flex flex-wrap gap-1 mt-1">
                          {webhook.events.slice(0, 3).map((event) => (
                            <Badge key={event} variant="outline" className="text-xs">
                              {event}
                            </Badge>
                          ))}
                          {webhook.events.length > 3 && (
                            <Badge variant="outline" className="text-xs">
                              +{webhook.events.length - 3} more
                            </Badge>
                          )}
                        </div>
                      </div>

                      <div>
                        <span className="text-sm font-medium text-gray-700">Secret:</span>
                        <div className="flex items-center space-x-2 mt-1">
                          <code className="text-sm bg-gray-100 px-2 py-1 rounded font-mono">
                            {showSecret[webhook.id]
                              ? webhook.secret
                              : '•'.repeat(webhook.secret.length)}
                          </code>
                          <Button
                            size="sm"
                            variant="ghost"
                            onClick={() => toggleSecret(webhook.id)}
                          >
                            {showSecret[webhook.id] ? (
                              <EyeOff className="h-4 w-4" />
                            ) : (
                              <Eye className="h-4 w-4" />
                            )}
                          </Button>
                          <Button
                            size="sm"
                            variant="ghost"
                            onClick={() => handleCopySecret(webhook.secret)}
                          >
                            <Copy className="h-4 w-4" />
                          </Button>
                        </div>
                      </div>

                      <div className="flex items-center space-x-4 text-sm text-gray-500">
                        <span>
                          {webhook.deliveryCount} deliveries
                        </span>
                        {webhook.failureCount > 0 && (
                          <span className="text-red-600">
                            {webhook.failureCount} failures
                          </span>
                        )}
                        <span>
                          Created {format(new Date(webhook.createdAt), 'MMM d, yyyy')}
                        </span>
                        {webhook.lastDeliveryAt && (
                          <span>
                            Last delivery {format(new Date(webhook.lastDeliveryAt), 'MMM d, yyyy')}
                          </span>
                        )}
                      </div>
                    </div>
                  </div>
                </div>

                <div className="flex items-center space-x-2">
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => handleTestWebhook(webhook.id)}
                    disabled={loading.testing}
                    className="flex items-center space-x-1"
                  >
                    <TestTube className="h-4 w-4" />
                    <span>Test</span>
                  </Button>

                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => {
                      setSelectedWebhook(webhook.id)
                      fetchDeliveries(webhook.id)
                    }}
                  >
                    View Deliveries
                  </Button>

                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => setEditingWebhook(webhook)}
                  >
                    <Settings className="h-4 w-4" />
                  </Button>

                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => handleDeleteWebhook(webhook.id)}
                    disabled={loading.deleting}
                    className="text-red-600 hover:text-red-700"
                  >
                    <Trash2 className="h-4 w-4" />
                  </Button>
                </div>
              </div>
            </Card>
          ))}
        </div>
      )}

      {/* Deliveries Modal */}
      {selectedWebhook && (
        <Dialog
          open={!!selectedWebhook}
          onOpenChange={() => setSelectedWebhook(null)}
        >
          <DialogContent className="max-w-4xl max-h-[80vh] overflow-y-auto">
            <DialogHeader>
              <DialogTitle>Webhook Deliveries</DialogTitle>
            </DialogHeader>

            <div className="space-y-4">
              {loading.deliveries[selectedWebhook] ? (
                <div className="text-center py-8">
                  <p className="text-gray-500">Loading deliveries...</p>
                </div>
              ) : deliveries[selectedWebhook]?.length === 0 ? (
                <div className="text-center py-8">
                  <p className="text-gray-500">No deliveries yet</p>
                </div>
              ) : (
                <div className="space-y-3">
                  {deliveries[selectedWebhook]?.map((delivery) => (
                    <div
                      key={delivery.id}
                      className="border border-gray-200 rounded-lg p-4"
                    >
                      <div className="flex items-center justify-between mb-2">
                        <div className="flex items-center space-x-3">
                          <Badge className={getStatusColor(delivery.status)}>
                            {delivery.status}
                          </Badge>
                          <span className="text-sm font-medium">
                            {delivery.eventType}
                          </span>
                          {delivery.responseStatus && (
                            <span className="text-sm text-gray-500">
                              HTTP {delivery.responseStatus}
                            </span>
                          )}
                        </div>
                        <div className="flex items-center space-x-2">
                          <span className="text-sm text-gray-500">
                            {format(new Date(delivery.createdAt), 'MMM d, HH:mm')}
                          </span>
                          {delivery.status === 'failed' && (
                            <Button
                              size="sm"
                              variant="outline"
                              onClick={() => retryDelivery(delivery.id)}
                              disabled={loading.retrying}
                            >
                              <RotateCcw className="h-4 w-4" />
                            </Button>
                          )}
                        </div>
                      </div>

                      {delivery.errorMessage && (
                        <div className="text-sm text-red-600 mb-2">
                          Error: {delivery.errorMessage}
                        </div>
                      )}

                      <div className="text-sm text-gray-500">
                        Retry count: {delivery.retryCount}
                        {delivery.responseTime && (
                          <span className="ml-4">
                            Response time: {delivery.responseTime}ms
                          </span>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>

            <DialogFooter>
              <Button onClick={() => setSelectedWebhook(null)}>Close</Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      )}

      {/* Create/Edit Webhook Modal */}
      <WebhookForm
        isOpen={showCreateModal || !!editingWebhook}
        onClose={() => {
          setShowCreateModal(false)
          setEditingWebhook(null)
        }}
        webhook={editingWebhook}
        availableEvents={availableEvents}
        onSubmit={editingWebhook ?
          (data) => handleUpdateWebhook(editingWebhook.id, data) :
          handleCreateWebhook
        }
        loading={loading.creating || loading.updating}
      />
    </div>
  )
}

interface WebhookFormProps {
  isOpen: boolean
  onClose: () => void
  webhook?: Webhook | null
  availableEvents: string[]
  onSubmit: (data: CreateWebhookData | UpdateWebhookData) => void
  loading: boolean
}

const WebhookForm: React.FC<WebhookFormProps> = ({
  isOpen,
  onClose,
  webhook,
  availableEvents,
  onSubmit,
  loading,
}) => {
  const [formData, setFormData] = useState({
    name: '',
    url: '',
    events: [] as string[],
    isActive: true,
  })

  // Reset form when webhook changes
  useEffect(() => {
    if (webhook) {
      setFormData({
        name: webhook.name,
        url: webhook.url,
        events: webhook.events,
        isActive: webhook.isActive,
      })
    } else {
      setFormData({
        name: '',
        url: '',
        events: [],
        isActive: true,
      })
    }
  }, [webhook])

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    onSubmit(formData)
  }

  const toggleEvent = (event: string) => {
    setFormData(prev => ({
      ...prev,
      events: prev.events.includes(event)
        ? prev.events.filter(e => e !== event)
        : [...prev.events, event],
    }))
  }

  return (
    <Dialog open={isOpen} onOpenChange={onClose}>
      <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>
            {webhook ? 'Edit Webhook' : 'Create Webhook'}
          </DialogTitle>
        </DialogHeader>

        <form onSubmit={handleSubmit} className="space-y-6">
          <div className="space-y-4">
            <div>
              <label htmlFor="name" className="block text-sm font-medium text-gray-700 mb-1">
                Name *
              </label>
              <Input
                id="name"
                value={formData.name}
                onChange={(e) => setFormData(prev => ({ ...prev, name: e.target.value }))}
                placeholder="My Webhook"
                required
              />
            </div>

            <div>
              <label htmlFor="url" className="block text-sm font-medium text-gray-700 mb-1">
                URL *
              </label>
              <Input
                id="url"
                type="url"
                value={formData.url}
                onChange={(e) => setFormData(prev => ({ ...prev, url: e.target.value }))}
                placeholder="https://your-app.com/webhooks"
                required
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Events *
              </label>
              <div className="grid grid-cols-2 gap-2 max-h-48 overflow-y-auto">
                {availableEvents.map((event) => (
                  <label
                    key={event}
                    className="flex items-center space-x-2 p-2 hover:bg-gray-50 rounded cursor-pointer"
                  >
                    <input
                      type="checkbox"
                      checked={formData.events.includes(event)}
                      onChange={() => toggleEvent(event)}
                      className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                    />
                    <div>
                      <div className="text-sm font-medium">{event}</div>
                      <div className="text-xs text-gray-500">
                        {getWebhookEventDescription(event)}
                      </div>
                    </div>
                  </label>
                ))}
              </div>
              {formData.events.length === 0 && (
                <p className="text-sm text-red-600 mt-1">
                  Please select at least one event
                </p>
              )}
            </div>

            <div className="flex items-center space-x-2">
              <input
                id="isActive"
                type="checkbox"
                checked={formData.isActive}
                onChange={(e) => setFormData(prev => ({ ...prev, isActive: e.target.checked }))}
                className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
              />
              <label htmlFor="isActive" className="text-sm font-medium text-gray-700">
                Active
              </label>
            </div>
          </div>

          <DialogFooter className="flex justify-end space-x-3">
            <Button type="button" variant="outline" onClick={onClose}>
              Cancel
            </Button>
            <Button
              type="submit"
              disabled={loading || formData.events.length === 0}
            >
              {loading ? 'Saving...' : webhook ? 'Update' : 'Create'}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )
}