import { useParams } from 'react-router-dom'
import { motion } from 'framer-motion'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/Card'

export default function BoardPage() {
  const { boardId } = useParams()

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className="space-y-8"
    >
      <div>
        <h1 className="text-3xl font-bold text-foreground">Board</h1>
        <p className="text-muted-foreground mt-2">
          Board ID: {boardId}
        </p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Coming Soon</CardTitle>
          <CardDescription>
            Board management interface is under development
          </CardDescription>
        </CardHeader>
        <CardContent>
          <p className="text-muted-foreground">
            This page will show board details, items, and collaboration features.
          </p>
        </CardContent>
      </Card>
    </motion.div>
  )
}