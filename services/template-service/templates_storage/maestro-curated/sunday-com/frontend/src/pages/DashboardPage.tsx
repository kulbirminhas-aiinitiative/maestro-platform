import { motion } from 'framer-motion'
import { PlusIcon, FolderIcon, ClockIcon, TrendingUpIcon } from 'lucide-react'

import { Button } from '@/components/ui/Button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/Card'
import { Badge, StatusBadge } from '@/components/ui/Badge'
import { UserAvatar } from '@/components/ui/Avatar'
import { useUser } from '@/store/auth'

const mockStats = [
  {
    title: 'Active Boards',
    value: '12',
    description: 'Across 3 workspaces',
    icon: FolderIcon,
    trend: '+2 this week',
  },
  {
    title: 'Tasks Due Today',
    value: '8',
    description: '3 high priority',
    icon: ClockIcon,
    trend: '2 completed',
  },
  {
    title: 'Team Productivity',
    value: '94%',
    description: 'Up from last week',
    icon: TrendingUpIcon,
    trend: '+5% improvement',
  },
]

const mockRecentBoards = [
  {
    id: '1',
    name: 'Marketing Campaign Q1',
    workspace: 'Marketing',
    color: '#3b82f6',
    updatedAt: '2 hours ago',
    members: [
      { id: '1', firstName: 'John', lastName: 'Doe', avatarUrl: null },
      { id: '2', firstName: 'Jane', lastName: 'Smith', avatarUrl: null },
    ],
    progress: 75,
  },
  {
    id: '2',
    name: 'Product Roadmap',
    workspace: 'Product',
    color: '#10b981',
    updatedAt: '4 hours ago',
    members: [
      { id: '3', firstName: 'Mike', lastName: 'Johnson', avatarUrl: null },
    ],
    progress: 60,
  },
  {
    id: '3',
    name: 'Bug Tracking',
    workspace: 'Engineering',
    color: '#ef4444',
    updatedAt: '1 day ago',
    members: [
      { id: '4', firstName: 'Sarah', lastName: 'Wilson', avatarUrl: null },
      { id: '5', firstName: 'Tom', lastName: 'Brown', avatarUrl: null },
    ],
    progress: 40,
  },
]

const mockRecentTasks = [
  {
    id: '1',
    title: 'Design new landing page',
    board: 'Marketing Campaign Q1',
    status: 'In Progress',
    priority: 'High',
    dueDate: 'Today',
    assignee: { firstName: 'John', lastName: 'Doe' },
  },
  {
    id: '2',
    title: 'Fix authentication bug',
    board: 'Bug Tracking',
    status: 'Review',
    priority: 'Urgent',
    dueDate: 'Yesterday',
    assignee: { firstName: 'Sarah', lastName: 'Wilson' },
  },
  {
    id: '3',
    title: 'Update product requirements',
    board: 'Product Roadmap',
    status: 'Todo',
    priority: 'Medium',
    dueDate: 'Tomorrow',
    assignee: { firstName: 'Mike', lastName: 'Johnson' },
  },
]

export default function DashboardPage() {
  const user = useUser()

  return (
    <div className="space-y-8">
      {/* Header */}
      <motion.div
        initial={{ opacity: 0, y: -20 }}
        animate={{ opacity: 1, y: 0 }}
        className="flex items-center justify-between"
      >
        <div>
          <h1 className="text-3xl font-bold text-foreground">
            Welcome back, {user?.firstName || 'there'}!
          </h1>
          <p className="text-muted-foreground mt-2">
            Here's what's happening with your projects today.
          </p>
        </div>
        <Button leftIcon={<PlusIcon className="h-4 w-4" />}>
          New Board
        </Button>
      </motion.div>

      {/* Stats Cards */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.1 }}
        className="grid gap-6 md:grid-cols-2 lg:grid-cols-3"
      >
        {mockStats.map((stat, index) => {
          const Icon = stat.icon
          return (
            <Card key={stat.title}>
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">
                  {stat.title}
                </CardTitle>
                <Icon className="h-4 w-4 text-muted-foreground" />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">{stat.value}</div>
                <p className="text-xs text-muted-foreground">
                  {stat.description}
                </p>
                <p className="text-xs text-success-600 mt-1">
                  {stat.trend}
                </p>
              </CardContent>
            </Card>
          )
        })}
      </motion.div>

      <div className="grid gap-8 lg:grid-cols-2">
        {/* Recent Boards */}
        <motion.div
          initial={{ opacity: 0, x: -20 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ delay: 0.2 }}
        >
          <Card>
            <CardHeader>
              <CardTitle>Recent Boards</CardTitle>
              <CardDescription>
                Boards you've been working on recently
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              {mockRecentBoards.map((board) => (
                <div
                  key={board.id}
                  className="flex items-center space-x-4 p-3 rounded-lg hover:bg-accent cursor-pointer transition-colors"
                >
                  <div
                    className="h-10 w-10 rounded flex-shrink-0"
                    style={{ backgroundColor: board.color }}
                  />
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-foreground truncate">
                      {board.name}
                    </p>
                    <p className="text-xs text-muted-foreground">
                      {board.workspace} • Updated {board.updatedAt}
                    </p>
                    <div className="flex items-center mt-2 space-x-2">
                      <div className="flex -space-x-1">
                        {board.members.slice(0, 3).map((member, index) => (
                          <UserAvatar
                            key={member.id}
                            user={{
                              firstName: member.firstName,
                              lastName: member.lastName,
                              fullName: `${member.firstName} ${member.lastName}`,
                              avatarUrl: member.avatarUrl,
                            }}
                            size="sm"
                            className="border-2 border-background"
                          />
                        ))}
                        {board.members.length > 3 && (
                          <div className="h-6 w-6 rounded-full bg-muted border-2 border-background flex items-center justify-center text-xs">
                            +{board.members.length - 3}
                          </div>
                        )}
                      </div>
                      <div className="flex-1 bg-muted rounded-full h-2">
                        <div
                          className="bg-primary h-2 rounded-full transition-all"
                          style={{ width: `${board.progress}%` }}
                        />
                      </div>
                      <span className="text-xs text-muted-foreground">
                        {board.progress}%
                      </span>
                    </div>
                  </div>
                </div>
              ))}
            </CardContent>
          </Card>
        </motion.div>

        {/* Recent Tasks */}
        <motion.div
          initial={{ opacity: 0, x: 20 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ delay: 0.3 }}
        >
          <Card>
            <CardHeader>
              <CardTitle>Your Tasks</CardTitle>
              <CardDescription>
                Tasks assigned to you across all boards
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              {mockRecentTasks.map((task) => (
                <div
                  key={task.id}
                  className="flex items-center space-x-4 p-3 rounded-lg hover:bg-accent cursor-pointer transition-colors"
                >
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-foreground truncate">
                      {task.title}
                    </p>
                    <p className="text-xs text-muted-foreground">
                      {task.board}
                    </p>
                    <div className="flex items-center mt-2 space-x-2">
                      <StatusBadge status={task.status} />
                      <Badge
                        variant={
                          task.priority === 'Urgent'
                            ? 'danger'
                            : task.priority === 'High'
                            ? 'warning'
                            : 'secondary'
                        }
                        size="sm"
                      >
                        {task.priority}
                      </Badge>
                      <span className="text-xs text-muted-foreground">
                        Due {task.dueDate}
                      </span>
                    </div>
                  </div>
                  <UserAvatar
                    user={{
                      firstName: task.assignee.firstName,
                      lastName: task.assignee.lastName,
                      fullName: `${task.assignee.firstName} ${task.assignee.lastName}`,
                    }}
                    size="sm"
                  />
                </div>
              ))}
            </CardContent>
          </Card>
        </motion.div>
      </div>
    </div>
  )
}