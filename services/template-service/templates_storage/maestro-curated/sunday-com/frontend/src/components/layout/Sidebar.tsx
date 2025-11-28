import { Link, useLocation } from 'react-router-dom'
import { motion } from 'framer-motion'
import {
  HomeIcon,
  FolderIcon,
  SettingsIcon,
  PlusIcon,
  ChevronLeftIcon,
  ChevronRightIcon,
} from 'lucide-react'

import { Button } from '@/components/ui/Button'
import { UserAvatar } from '@/components/ui/Avatar'
import { Badge } from '@/components/ui/Badge'
import { useSidebar } from '@/store/ui'
import { useUser } from '@/store/auth'
import { APP_NAME } from '@/lib/constants'
import { cn } from '@/lib/utils'

const navigation = [
  { name: 'Dashboard', href: '/app/dashboard', icon: HomeIcon },
  { name: 'Workspaces', href: '/app/workspaces', icon: FolderIcon },
  { name: 'Settings', href: '/app/settings', icon: SettingsIcon },
]

export default function Sidebar() {
  const location = useLocation()
  const { sidebarCollapsed, toggleSidebar } = useSidebar()
  const user = useUser()

  return (
    <>
      {/* Mobile backdrop */}
      {!sidebarCollapsed && (
        <div
          className="fixed inset-0 z-40 bg-background/80 backdrop-blur-sm lg:hidden"
          onClick={toggleSidebar}
        />
      )}

      {/* Sidebar */}
      <motion.div
        initial={false}
        animate={{
          width: sidebarCollapsed ? '4rem' : '16rem',
        }}
        transition={{ duration: 0.3, ease: 'easeInOut' }}
        className={cn(
          'fixed inset-y-0 left-0 z-50 flex flex-col bg-card border-r border-border',
          'w-64 lg:w-auto' // Full width on mobile, animated on desktop
        )}
      >
        {/* Header */}
        <div className="flex h-16 items-center justify-between px-4 border-b border-border">
          {!sidebarCollapsed && (
            <Link to="/app/dashboard" className="flex items-center space-x-2">
              <div className="h-8 w-8 rounded-lg bg-gradient-to-br from-primary to-primary/70 flex items-center justify-center">
                <span className="text-white font-bold text-sm">S</span>
              </div>
              <span className="font-bold text-lg">{APP_NAME}</span>
            </Link>
          )}

          <Button
            variant="ghost"
            size="icon-sm"
            onClick={toggleSidebar}
            className="hidden lg:flex"
          >
            {sidebarCollapsed ? (
              <ChevronRightIcon className="h-4 w-4" />
            ) : (
              <ChevronLeftIcon className="h-4 w-4" />
            )}
          </Button>
        </div>

        {/* Navigation */}
        <nav className="flex-1 px-4 py-6 space-y-2 overflow-y-auto">
          {/* Quick actions */}
          {!sidebarCollapsed && (
            <div className="space-y-2 mb-6">
              <Button className="w-full justify-start" leftIcon={<PlusIcon className="h-4 w-4" />}>
                New Board
              </Button>
            </div>
          )}

          {/* Main navigation */}
          <div className="space-y-1">
            {navigation.map((item) => {
              const isActive = location.pathname.startsWith(item.href)
              const Icon = item.icon

              return (
                <Link
                  key={item.name}
                  to={item.href}
                  className={cn(
                    'flex items-center rounded-lg px-3 py-2 text-sm font-medium transition-colors',
                    'hover:bg-accent hover:text-accent-foreground',
                    isActive
                      ? 'bg-accent text-accent-foreground'
                      : 'text-muted-foreground'
                  )}
                >
                  <Icon className="h-4 w-4 shrink-0" />
                  {!sidebarCollapsed && (
                    <span className="ml-3">{item.name}</span>
                  )}
                </Link>
              )
            })}
          </div>

          {/* Recent boards */}
          {!sidebarCollapsed && (
            <div className="mt-8">
              <h3 className="mb-2 px-3 text-xs font-semibold text-muted-foreground uppercase tracking-wider">
                Recent Boards
              </h3>
              <div className="space-y-1">
                {/* TODO: Replace with actual recent boards */}
                <div className="flex items-center rounded-lg px-3 py-2 text-sm hover:bg-accent">
                  <div className="h-4 w-4 rounded bg-blue-500 shrink-0" />
                  <span className="ml-3 text-muted-foreground">Marketing Campaign</span>
                </div>
                <div className="flex items-center rounded-lg px-3 py-2 text-sm hover:bg-accent">
                  <div className="h-4 w-4 rounded bg-green-500 shrink-0" />
                  <span className="ml-3 text-muted-foreground">Product Roadmap</span>
                </div>
                <div className="flex items-center rounded-lg px-3 py-2 text-sm hover:bg-accent">
                  <div className="h-4 w-4 rounded bg-purple-500 shrink-0" />
                  <span className="ml-3 text-muted-foreground">Bug Tracking</span>
                </div>
              </div>
            </div>
          )}
        </nav>

        {/* User section */}
        <div className="border-t border-border p-4">
          <div className="flex items-center space-x-3">
            <UserAvatar user={user} size="md" />
            {!sidebarCollapsed && (
              <div className="flex-1 min-w-0">
                <div className="flex items-center space-x-2">
                  <p className="text-sm font-medium text-foreground truncate">
                    {user?.fullName || 'User'}
                  </p>
                  <Badge variant="secondary" size="sm">
                    Pro
                  </Badge>
                </div>
                <p className="text-xs text-muted-foreground truncate">
                  {user?.email}
                </p>
              </div>
            )}
          </div>
        </div>
      </motion.div>
    </>
  )
}