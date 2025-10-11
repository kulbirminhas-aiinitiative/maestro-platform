import React, { useState } from 'react'
import { Link, useLocation } from 'react-router-dom'
import { useAuthContext } from '@/contexts/AuthContext'
import { Button } from '@/components/ui/Button'
import { Avatar } from '@/components/ui/Avatar'
import { Badge } from '@/components/ui/Badge'
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
  SheetTrigger,
  SheetDescription,
} from '@/components/ui/Sheet'
import {
  Menu,
  Home,
  Folder,
  Settings,
  Users,
  Bell,
  Search,
  Plus,
  X,
  LogOut,
  User,
} from 'lucide-react'
import clsx from 'clsx'

interface MobileNavigationProps {
  className?: string
}

export const MobileNavigation: React.FC<MobileNavigationProps> = ({ className }) => {
  const location = useLocation()
  const { user, isAuthenticated } = useAuthContext()
  const [isOpen, setIsOpen] = useState(false)

  const navigationItems = [
    {
      name: 'Dashboard',
      href: '/dashboard',
      icon: Home,
      current: location.pathname === '/dashboard',
    },
    {
      name: 'Workspaces',
      href: '/workspaces',
      icon: Folder,
      current: location.pathname.startsWith('/workspaces'),
    },
    {
      name: 'Teams',
      href: '/teams',
      icon: Users,
      current: location.pathname.startsWith('/teams'),
    },
    {
      name: 'Settings',
      href: '/settings',
      icon: Settings,
      current: location.pathname.startsWith('/settings'),
    },
  ]

  const handleLogout = () => {
    // Implement logout functionality
    setIsOpen(false)
  }

  if (!isAuthenticated) return null

  return (
    <div className={clsx('md:hidden', className)}>
      {/* Mobile Header */}
      <div className="fixed top-0 left-0 right-0 z-40 bg-white border-b border-gray-200 px-4 py-3">
        <div className="flex items-center justify-between">
          {/* Menu Button */}
          <Sheet open={isOpen} onOpenChange={setIsOpen}>
            <SheetTrigger asChild>
              <Button variant="ghost" size="sm">
                <Menu className="h-5 w-5" />
              </Button>
            </SheetTrigger>
            <SheetContent side="left" className="w-80 p-0">
              <div className="flex flex-col h-full">
                <SheetHeader className="p-6 border-b border-gray-200">
                  <div className="flex items-center space-x-3">
                    <Avatar
                      src={user?.avatarUrl}
                      alt={user?.fullName || 'User'}
                      size="md"
                    />
                    <div className="flex-1 text-left">
                      <SheetTitle className="text-base font-medium text-gray-900">
                        {user?.fullName || 'User'}
                      </SheetTitle>
                      <SheetDescription className="text-sm text-gray-500">
                        {user?.email}
                      </SheetDescription>
                    </div>
                  </div>
                </SheetHeader>

                {/* Navigation */}
                <nav className="flex-1 px-6 py-4">
                  <div className="space-y-2">
                    {navigationItems.map((item) => (
                      <Link
                        key={item.name}
                        to={item.href}
                        onClick={() => setIsOpen(false)}
                        className={clsx(
                          'flex items-center space-x-3 px-3 py-2 rounded-lg text-sm font-medium transition-colors',
                          item.current
                            ? 'bg-blue-50 text-blue-700'
                            : 'text-gray-700 hover:bg-gray-100'
                        )}
                      >
                        <item.icon className="h-5 w-5" />
                        <span>{item.name}</span>
                      </Link>
                    ))}
                  </div>

                  {/* Quick Actions */}
                  <div className="mt-8">
                    <h3 className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-3">
                      Quick Actions
                    </h3>
                    <div className="space-y-2">
                      <Button
                        variant="outline"
                        size="sm"
                        className="w-full justify-start"
                        onClick={() => setIsOpen(false)}
                      >
                        <Plus className="h-4 w-4 mr-2" />
                        New Board
                      </Button>
                      <Button
                        variant="outline"
                        size="sm"
                        className="w-full justify-start"
                        onClick={() => setIsOpen(false)}
                      >
                        <Search className="h-4 w-4 mr-2" />
                        Search
                      </Button>
                    </div>
                  </div>
                </nav>

                {/* Footer */}
                <div className="p-6 border-t border-gray-200">
                  <div className="space-y-2">
                    <Link
                      to="/profile"
                      onClick={() => setIsOpen(false)}
                      className="flex items-center space-x-3 px-3 py-2 rounded-lg text-sm font-medium text-gray-700 hover:bg-gray-100"
                    >
                      <User className="h-5 w-5" />
                      <span>Profile</span>
                    </Link>
                    <button
                      onClick={handleLogout}
                      className="flex items-center space-x-3 px-3 py-2 rounded-lg text-sm font-medium text-red-700 hover:bg-red-50 w-full text-left"
                    >
                      <LogOut className="h-5 w-5" />
                      <span>Sign out</span>
                    </button>
                  </div>
                </div>
              </div>
            </SheetContent>
          </Sheet>

          {/* Logo */}
          <Link to="/dashboard" className="flex items-center">
            <span className="text-xl font-bold text-blue-600">Sunday</span>
          </Link>

          {/* Right Actions */}
          <div className="flex items-center space-x-2">
            <Button variant="ghost" size="sm">
              <Search className="h-5 w-5" />
            </Button>
            <Button variant="ghost" size="sm" className="relative">
              <Bell className="h-5 w-5" />
              <Badge
                variant="secondary"
                className="absolute -top-1 -right-1 h-5 w-5 rounded-full p-0 flex items-center justify-center text-xs"
              >
                3
              </Badge>
            </Button>
          </div>
        </div>
      </div>

      {/* Bottom Navigation */}
      <div className="fixed bottom-0 left-0 right-0 z-40 bg-white border-t border-gray-200">
        <nav className="flex">
          {navigationItems.slice(0, 4).map((item) => (
            <Link
              key={item.name}
              to={item.href}
              className={clsx(
                'flex-1 flex flex-col items-center justify-center py-2 px-1',
                item.current
                  ? 'text-blue-600'
                  : 'text-gray-500 hover:text-gray-700'
              )}
            >
              <item.icon className="h-5 w-5 mb-1" />
              <span className="text-xs font-medium">{item.name}</span>
            </Link>
          ))}
        </nav>
      </div>
    </div>
  )
}

// Mobile-specific spacer components
export const MobileHeaderSpacer: React.FC = () => (
  <div className="h-16 md:hidden" />
)

export const MobileBottomSpacer: React.FC = () => (
  <div className="h-16 md:hidden" />
)

export default MobileNavigation