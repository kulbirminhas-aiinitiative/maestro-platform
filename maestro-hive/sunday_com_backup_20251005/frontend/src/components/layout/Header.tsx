import { useState } from 'react'
import { Link } from 'react-router-dom'
import {
  BellIcon,
  SearchIcon,
  MenuIcon,
  SunIcon,
  MoonIcon,
  LogOutIcon,
  UserIcon,
  SettingsIcon,
} from 'lucide-react'

import { Button } from '@/components/ui/Button'
import { Input } from '@/components/ui/Input'
import { UserAvatar } from '@/components/ui/Avatar'
import { Badge } from '@/components/ui/Badge'
import * as DropdownMenu from '@radix-ui/react-dropdown-menu'
import { useSidebar, useTheme } from '@/store/ui'
import { useUser } from '@/store/auth'
import { useLogout } from '@/hooks/useAuth'

export default function Header() {
  const [searchQuery, setSearchQuery] = useState('')
  const { toggleSidebar } = useSidebar()
  const { theme, setTheme } = useTheme()
  const user = useUser()
  const logout = useLogout()

  const handleLogout = () => {
    logout()
  }

  const toggleTheme = () => {
    setTheme(theme === 'dark' ? 'light' : 'dark')
  }

  return (
    <header className="sticky top-0 z-40 w-full border-b bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
      <div className="container flex h-16 items-center justify-between px-4">
        {/* Left section */}
        <div className="flex items-center space-x-4">
          {/* Mobile menu button */}
          <Button
            variant="ghost"
            size="icon-sm"
            onClick={toggleSidebar}
            className="lg:hidden"
          >
            <MenuIcon className="h-4 w-4" />
          </Button>

          {/* Search */}
          <div className="relative w-64 hidden md:block">
            <Input
              type="search"
              placeholder="Search boards, items..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              leftIcon={<SearchIcon className="h-4 w-4" />}
              className="w-full"
            />
          </div>
        </div>

        {/* Right section */}
        <div className="flex items-center space-x-4">
          {/* Search button for mobile */}
          <Button variant="ghost" size="icon" className="md:hidden">
            <SearchIcon className="h-4 w-4" />
          </Button>

          {/* Theme toggle */}
          <Button variant="ghost" size="icon" onClick={toggleTheme}>
            {theme === 'dark' ? (
              <SunIcon className="h-4 w-4" />
            ) : (
              <MoonIcon className="h-4 w-4" />
            )}
          </Button>

          {/* Notifications */}
          <Button variant="ghost" size="icon" className="relative">
            <BellIcon className="h-4 w-4" />
            <Badge
              variant="danger"
              className="absolute -top-1 -right-1 h-5 w-5 rounded-full p-0 text-xs"
            >
              3
            </Badge>
          </Button>

          {/* User menu */}
          <DropdownMenu.Root>
            <DropdownMenu.Trigger asChild>
              <Button variant="ghost" className="h-10 w-10 rounded-full">
                <UserAvatar user={user} size="md" />
              </Button>
            </DropdownMenu.Trigger>

            <DropdownMenu.Portal>
              <DropdownMenu.Content
                className="min-w-56 overflow-hidden rounded-md border bg-popover p-1 text-popover-foreground shadow-md data-[state=open]:animate-in data-[state=closed]:animate-out data-[state=closed]:fade-out-0 data-[state=open]:fade-in-0 data-[state=closed]:zoom-out-95 data-[state=open]:zoom-in-95 data-[side=bottom]:slide-in-from-top-2 data-[side=left]:slide-in-from-right-2 data-[side=right]:slide-in-from-left-2 data-[side=top]:slide-in-from-bottom-2"
                sideOffset={5}
              >
                {/* User info */}
                <div className="px-2 py-1.5 text-sm">
                  <div className="flex items-center space-x-2">
                    <UserAvatar user={user} size="sm" />
                    <div className="flex flex-col space-y-1">
                      <p className="text-sm font-medium leading-none">
                        {user?.fullName || 'User'}
                      </p>
                      <p className="text-xs leading-none text-muted-foreground">
                        {user?.email}
                      </p>
                    </div>
                  </div>
                </div>

                <DropdownMenu.Separator className="h-px bg-border my-1" />

                {/* Menu items */}
                <DropdownMenu.Item
                  className="relative flex cursor-default select-none items-center rounded-sm px-2 py-1.5 text-sm outline-none transition-colors focus:bg-accent focus:text-accent-foreground data-[disabled]:pointer-events-none data-[disabled]:opacity-50"
                  asChild
                >
                  <Link to="/app/settings/profile">
                    <UserIcon className="mr-2 h-4 w-4" />
                    <span>Profile</span>
                  </Link>
                </DropdownMenu.Item>

                <DropdownMenu.Item
                  className="relative flex cursor-default select-none items-center rounded-sm px-2 py-1.5 text-sm outline-none transition-colors focus:bg-accent focus:text-accent-foreground data-[disabled]:pointer-events-none data-[disabled]:opacity-50"
                  asChild
                >
                  <Link to="/app/settings">
                    <SettingsIcon className="mr-2 h-4 w-4" />
                    <span>Settings</span>
                  </Link>
                </DropdownMenu.Item>

                <DropdownMenu.Separator className="h-px bg-border my-1" />

                <DropdownMenu.Item
                  className="relative flex cursor-default select-none items-center rounded-sm px-2 py-1.5 text-sm outline-none transition-colors focus:bg-accent focus:text-accent-foreground data-[disabled]:pointer-events-none data-[disabled]:opacity-50"
                  onClick={handleLogout}
                >
                  <LogOutIcon className="mr-2 h-4 w-4" />
                  <span>Log out</span>
                </DropdownMenu.Item>
              </DropdownMenu.Content>
            </DropdownMenu.Portal>
          </DropdownMenu.Root>
        </div>
      </div>
    </header>
  )
}