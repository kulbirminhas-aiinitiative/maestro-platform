import React, { useState } from 'react'
import { motion } from 'framer-motion'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/Card'
import { Button } from '@/components/ui/Button'
import { Badge } from '@/components/ui/Badge'
import { WebhookManager } from '@/components/webhooks/WebhookManager'
import { AnalyticsDashboard } from '@/components/analytics/AnalyticsDashboard'
import { useAuth } from '@/hooks/useAuth'
import {
  User,
  Building2,
  Webhook,
  Bell,
  Shield,
  Palette,
  BarChart3,
  Settings as SettingsIcon,
  Globe,
  Lock,
  Zap,
} from 'lucide-react'
import clsx from 'clsx'

type SettingsTab =
  | 'profile'
  | 'organization'
  | 'webhooks'
  | 'notifications'
  | 'security'
  | 'appearance'
  | 'analytics'

export default function SettingsPage() {
  const [activeTab, setActiveTab] = useState<SettingsTab>('profile')
  const { user } = useAuth()

  const tabs = [
    { id: 'profile' as const, label: 'Profile', icon: User, description: 'Personal information and preferences' },
    { id: 'organization' as const, label: 'Organization', icon: Building2, description: 'Organization settings and billing' },
    { id: 'webhooks' as const, label: 'Webhooks', icon: Webhook, description: 'Manage webhook integrations' },
    { id: 'notifications' as const, label: 'Notifications', icon: Bell, description: 'Email and push notifications' },
    { id: 'security' as const, label: 'Security', icon: Shield, description: 'Password and authentication' },
    { id: 'appearance' as const, label: 'Appearance', icon: Palette, description: 'Theme and display preferences' },
    { id: 'analytics' as const, label: 'Analytics', icon: BarChart3, description: 'Usage statistics and insights' },
  ]

  const renderTabContent = () => {
    switch (activeTab) {
      case 'profile':
        return (
          <div className="space-y-6">
            <div>
              <h3 className="text-lg font-medium text-gray-900 mb-4">Profile Information</h3>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Full Name
                  </label>
                  <div className="text-gray-900">{user?.fullName || 'Not set'}</div>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Email
                  </label>
                  <div className="text-gray-900">{user?.email}</div>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Timezone
                  </label>
                  <div className="text-gray-900">{user?.timezone || 'UTC'}</div>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Language
                  </label>
                  <div className="text-gray-900">{user?.locale || 'en'}</div>
                </div>
              </div>
              <div className="mt-6">
                <Button>Edit Profile</Button>
              </div>
            </div>
          </div>
        )

      case 'organization':
        return (
          <div className="space-y-6">
            <div>
              <h3 className="text-lg font-medium text-gray-900 mb-4">Organization Settings</h3>
              <Card>
                <CardContent className="p-6">
                  <div className="flex items-center space-x-4">
                    <div className="w-16 h-16 bg-blue-100 rounded-lg flex items-center justify-center">
                      <Building2 className="h-8 w-8 text-blue-600" />
                    </div>
                    <div className="flex-1">
                      <h4 className="text-lg font-medium text-gray-900">Your Organization</h4>
                      <p className="text-gray-500">Manage organization settings, members, and billing</p>
                      <div className="mt-2">
                        <Badge variant="default">Pro Plan</Badge>
                      </div>
                    </div>
                    <Button variant="outline">Manage</Button>
                  </div>
                </CardContent>
              </Card>
            </div>
          </div>
        )

      case 'webhooks':
        return (
          <div className="space-y-6">
            <div>
              <h3 className="text-lg font-medium text-gray-900 mb-2">Webhook Integrations</h3>
              <p className="text-gray-600 mb-6">
                Configure webhooks to receive real-time notifications about events in your organization.
              </p>
            </div>
            <WebhookManager
              organizationId={user?.organizations?.[0]?.id}
            />
          </div>
        )

      case 'notifications':
        return (
          <div className="space-y-6">
            <div>
              <h3 className="text-lg font-medium text-gray-900 mb-4">Notification Preferences</h3>
              <div className="space-y-4">
                <Card>
                  <CardContent className="p-4">
                    <div className="flex items-center justify-between">
                      <div>
                        <h4 className="font-medium text-gray-900">Email Notifications</h4>
                        <p className="text-sm text-gray-500">Receive notifications via email</p>
                      </div>
                      <Button variant="outline" size="sm">Configure</Button>
                    </div>
                  </CardContent>
                </Card>
                <Card>
                  <CardContent className="p-4">
                    <div className="flex items-center justify-between">
                      <div>
                        <h4 className="font-medium text-gray-900">Push Notifications</h4>
                        <p className="text-sm text-gray-500">Browser and mobile push notifications</p>
                      </div>
                      <Button variant="outline" size="sm">Configure</Button>
                    </div>
                  </CardContent>
                </Card>
              </div>
            </div>
          </div>
        )

      case 'security':
        return (
          <div className="space-y-6">
            <div>
              <h3 className="text-lg font-medium text-gray-900 mb-4">Security Settings</h3>
              <div className="space-y-4">
                <Card>
                  <CardContent className="p-4">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center space-x-3">
                        <Lock className="h-5 w-5 text-gray-400" />
                        <div>
                          <h4 className="font-medium text-gray-900">Password</h4>
                          <p className="text-sm text-gray-500">Change your password</p>
                        </div>
                      </div>
                      <Button variant="outline" size="sm">Change</Button>
                    </div>
                  </CardContent>
                </Card>
                <Card>
                  <CardContent className="p-4">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center space-x-3">
                        <Shield className="h-5 w-5 text-gray-400" />
                        <div>
                          <h4 className="font-medium text-gray-900">Two-Factor Authentication</h4>
                          <p className="text-sm text-gray-500">Add an extra layer of security</p>
                        </div>
                      </div>
                      <Button variant="outline" size="sm">Enable</Button>
                    </div>
                  </CardContent>
                </Card>
              </div>
            </div>
          </div>
        )

      case 'appearance':
        return (
          <div className="space-y-6">
            <div>
              <h3 className="text-lg font-medium text-gray-900 mb-4">Appearance Settings</h3>
              <div className="space-y-4">
                <Card>
                  <CardContent className="p-4">
                    <div className="flex items-center justify-between">
                      <div>
                        <h4 className="font-medium text-gray-900">Theme</h4>
                        <p className="text-sm text-gray-500">Choose your interface theme</p>
                      </div>
                      <div className="flex space-x-2">
                        <Button variant="outline" size="sm">Light</Button>
                        <Button variant="default" size="sm">Dark</Button>
                        <Button variant="outline" size="sm">Auto</Button>
                      </div>
                    </div>
                  </CardContent>
                </Card>
                <Card>
                  <CardContent className="p-4">
                    <div className="flex items-center justify-between">
                      <div>
                        <h4 className="font-medium text-gray-900">Density</h4>
                        <p className="text-sm text-gray-500">Choose your interface density</p>
                      </div>
                      <div className="flex space-x-2">
                        <Button variant="outline" size="sm">Compact</Button>
                        <Button variant="default" size="sm">Normal</Button>
                        <Button variant="outline" size="sm">Comfortable</Button>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              </div>
            </div>
          </div>
        )

      case 'analytics':
        return (
          <div className="space-y-6">
            <div>
              <h3 className="text-lg font-medium text-gray-900 mb-2">Organization Analytics</h3>
              <p className="text-gray-600 mb-6">
                View detailed analytics and insights for your organization's usage and productivity.
              </p>
            </div>
            <AnalyticsDashboard
              organizationId={user?.organizations?.[0]?.id}
            />
          </div>
        )

      default:
        return null
    }
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className="min-h-screen bg-gray-50"
    >
      <div className="max-w-7xl mx-auto">
        <div className="bg-white border-b border-gray-200">
          <div className="px-6 py-8">
            <div className="flex items-center space-x-3">
              <SettingsIcon className="h-8 w-8 text-gray-400" />
              <div>
                <h1 className="text-3xl font-bold text-gray-900">Settings</h1>
                <p className="text-gray-600 mt-1">
                  Manage your account, organization, and application preferences
                </p>
              </div>
            </div>
          </div>
        </div>

        <div className="flex">
          {/* Sidebar */}
          <div className="w-64 bg-white border-r border-gray-200 min-h-screen">
            <nav className="p-4 space-y-1">
              {tabs.map((tab) => {
                const Icon = tab.icon
                return (
                  <button
                    key={tab.id}
                    onClick={() => setActiveTab(tab.id)}
                    className={clsx(
                      'w-full text-left px-3 py-2 rounded-lg transition-colors duration-200 flex items-center space-x-3 group',
                      activeTab === tab.id
                        ? 'bg-blue-50 text-blue-700 border border-blue-200'
                        : 'text-gray-700 hover:bg-gray-50 hover:text-gray-900'
                    )}
                  >
                    <Icon
                      className={clsx(
                        'h-5 w-5',
                        activeTab === tab.id
                          ? 'text-blue-600'
                          : 'text-gray-400 group-hover:text-gray-600'
                      )}
                    />
                    <div className="flex-1 min-w-0">
                      <div className="font-medium">{tab.label}</div>
                      <div className="text-xs text-gray-500 truncate">
                        {tab.description}
                      </div>
                    </div>
                  </button>
                )
              })}
            </nav>
          </div>

          {/* Main Content */}
          <div className="flex-1 p-8">
            <motion.div
              key={activeTab}
              initial={{ opacity: 0, x: 20 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ duration: 0.2 }}
            >
              {renderTabContent()}
            </motion.div>
          </div>
        </div>
      </div>
    </motion.div>
  )
}