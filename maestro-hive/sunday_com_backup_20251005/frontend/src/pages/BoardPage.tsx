import { useParams } from 'react-router-dom'
import { motion } from 'framer-motion'
import { BoardView } from '@/components/boards/BoardView'

export default function BoardPage() {
  const { boardId } = useParams()

  if (!boardId) {
    return (
      <div className="flex items-center justify-center h-64">
        <p className="text-muted-foreground">Board not found</p>
      </div>
    )
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className="h-full"
    >
      <BoardView />
    </motion.div>
  )
}