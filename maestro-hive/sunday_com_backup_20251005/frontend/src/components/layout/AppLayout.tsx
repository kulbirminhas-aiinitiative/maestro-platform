import { ReactNode } from 'react'
import { motion } from 'framer-motion'
import Sidebar from './Sidebar'
import Header from './Header'
import { useSidebar } from '@/store/ui'

interface AppLayoutProps {
  children: ReactNode
}

export default function AppLayout({ children }: AppLayoutProps) {
  const { sidebarCollapsed } = useSidebar()

  return (
    <div className="min-h-screen bg-background">
      {/* Sidebar */}
      <Sidebar />

      {/* Main content */}
      <div
        className={`transition-all duration-300 ${
          sidebarCollapsed ? 'lg:ml-16' : 'lg:ml-64'
        }`}
      >
        <Header />
        <main className="flex-1">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -20 }}
            className="container mx-auto px-4 py-6"
          >
            {children}
          </motion.div>
        </main>
      </div>
    </div>
  )
}