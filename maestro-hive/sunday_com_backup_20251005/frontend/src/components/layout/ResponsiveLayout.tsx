import React, { useState } from 'react'
import { useIsMobile } from '@/hooks/useResponsive'
import { Button } from '@/components/ui/Button'
import { Menu, X, ChevronLeft } from 'lucide-react'
import clsx from 'clsx'

interface ResponsiveLayoutProps {
  children: React.ReactNode
  sidebar?: React.ReactNode
  header?: React.ReactNode
  className?: string
}

export const ResponsiveLayout: React.FC<ResponsiveLayoutProps> = ({
  children,
  sidebar,
  header,
  className,
}) => {
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const isMobile = useIsMobile()

  const closeSidebar = () => setSidebarOpen(false)
  const toggleSidebar = () => setSidebarOpen(!sidebarOpen)

  return (
    <div className={clsx('flex h-screen bg-gray-50', className)}>
      {/* Sidebar */}
      {sidebar && (
        <>
          {/* Mobile sidebar overlay */}
          {isMobile && sidebarOpen && (
            <div
              className="fixed inset-0 z-40 bg-black bg-opacity-25"
              onClick={closeSidebar}
            />
          )}

          {/* Sidebar content */}
          <div
            className={clsx(
              'z-50 flex flex-col bg-white border-r border-gray-200',
              isMobile ? [
                'fixed inset-y-0 left-0 w-64 transform transition-transform duration-300 ease-in-out',
                sidebarOpen ? 'translate-x-0' : '-translate-x-full'
              ] : 'w-64 relative'
            )}
          >
            {/* Mobile sidebar header */}
            {isMobile && (
              <div className="flex items-center justify-between p-4 border-b border-gray-200">
                <h2 className="text-lg font-semibold text-gray-900">Menu</h2>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={closeSidebar}
                  className="text-gray-500 hover:text-gray-700"
                >
                  <X className="h-5 w-5" />
                </Button>
              </div>
            )}

            {/* Sidebar content */}
            <div className="flex-1 overflow-y-auto">
              {sidebar}
            </div>
          </div>
        </>
      )}

      {/* Main content area */}
      <div className="flex-1 flex flex-col overflow-hidden">
        {/* Header */}
        {header && (
          <div className="bg-white border-b border-gray-200 px-4 py-3">
            <div className="flex items-center justify-between">
              {/* Mobile menu button */}
              {isMobile && sidebar && (
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={toggleSidebar}
                  className="text-gray-500 hover:text-gray-700 mr-3"
                >
                  <Menu className="h-5 w-5" />
                </Button>
              )}

              {/* Header content */}
              <div className="flex-1">
                {header}
              </div>
            </div>
          </div>
        )}

        {/* Main content */}
        <div className="flex-1 overflow-hidden">
          {children}
        </div>
      </div>
    </div>
  )
}

interface MobileDrawerProps {
  isOpen: boolean
  onClose: () => void
  title?: string
  children: React.ReactNode
  className?: string
}

export const MobileDrawer: React.FC<MobileDrawerProps> = ({
  isOpen,
  onClose,
  title,
  children,
  className,
}) => {
  const isMobile = useIsMobile()

  if (!isMobile) return null

  return (
    <>
      {/* Overlay */}
      {isOpen && (
        <div
          className="fixed inset-0 z-40 bg-black bg-opacity-25"
          onClick={onClose}
        />
      )}

      {/* Drawer */}
      <div
        className={clsx(
          'fixed inset-y-0 right-0 z-50 w-full max-w-sm bg-white shadow-xl transform transition-transform duration-300 ease-in-out',
          isOpen ? 'translate-x-0' : 'translate-x-full',
          className
        )}
      >
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b border-gray-200">
          <h2 className="text-lg font-semibold text-gray-900">
            {title || 'Details'}
          </h2>
          <Button
            variant="ghost"
            size="sm"
            onClick={onClose}
            className="text-gray-500 hover:text-gray-700"
          >
            <X className="h-5 w-5" />
          </Button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-4">
          {children}
        </div>
      </div>
    </>
  )
}

interface ResponsiveGridProps {
  children: React.ReactNode
  cols?: {
    default?: number
    sm?: number
    md?: number
    lg?: number
    xl?: number
  }
  gap?: number
  className?: string
}

export const ResponsiveGrid: React.FC<ResponsiveGridProps> = ({
  children,
  cols = { default: 1, sm: 2, md: 3, lg: 4 },
  gap = 6,
  className,
}) => {
  const gridClasses = [
    `grid gap-${gap}`,
    cols.default && `grid-cols-${cols.default}`,
    cols.sm && `sm:grid-cols-${cols.sm}`,
    cols.md && `md:grid-cols-${cols.md}`,
    cols.lg && `lg:grid-cols-${cols.lg}`,
    cols.xl && `xl:grid-cols-${cols.xl}`,
  ].filter(Boolean).join(' ')

  return (
    <div className={clsx(gridClasses, className)}>
      {children}
    </div>
  )
}

interface ResponsiveStackProps {
  children: React.ReactNode
  direction?: {
    default?: 'horizontal' | 'vertical'
    sm?: 'horizontal' | 'vertical'
    md?: 'horizontal' | 'vertical'
    lg?: 'horizontal' | 'vertical'
  }
  gap?: number
  className?: string
}

export const ResponsiveStack: React.FC<ResponsiveStackProps> = ({
  children,
  direction = { default: 'vertical', md: 'horizontal' },
  gap = 4,
  className,
}) => {
  const stackClasses = [
    'flex',
    `gap-${gap}`,
    direction.default === 'horizontal' ? 'flex-row' : 'flex-col',
    direction.sm === 'horizontal' ? 'sm:flex-row' : direction.sm === 'vertical' ? 'sm:flex-col' : '',
    direction.md === 'horizontal' ? 'md:flex-row' : direction.md === 'vertical' ? 'md:flex-col' : '',
    direction.lg === 'horizontal' ? 'lg:flex-row' : direction.lg === 'vertical' ? 'lg:flex-col' : '',
  ].filter(Boolean).join(' ')

  return (
    <div className={clsx(stackClasses, className)}>
      {children}
    </div>
  )
}

interface MobileMenuProps {
  isOpen: boolean
  onClose: () => void
  children: React.ReactNode
}

export const MobileMenu: React.FC<MobileMenuProps> = ({
  isOpen,
  onClose,
  children,
}) => {
  const isMobile = useIsMobile()

  if (!isMobile) return null

  return (
    <>
      {/* Overlay */}
      {isOpen && (
        <div
          className="fixed inset-0 z-40 bg-black bg-opacity-25"
          onClick={onClose}
        />
      )}

      {/* Menu */}
      <div
        className={clsx(
          'fixed top-0 left-0 z-50 h-full w-64 bg-white shadow-xl transform transition-transform duration-300 ease-in-out',
          isOpen ? 'translate-x-0' : '-translate-x-full'
        )}
      >
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b border-gray-200">
          <h2 className="text-lg font-semibold text-gray-900">Menu</h2>
          <Button
            variant="ghost"
            size="sm"
            onClick={onClose}
            className="text-gray-500 hover:text-gray-700"
          >
            <X className="h-5 w-5" />
          </Button>
        </div>

        {/* Content */}
        <div className="overflow-y-auto">
          {children}
        </div>
      </div>
    </>
  )
}