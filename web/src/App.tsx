import { Layout } from '@/components/layout'
import { useActiveSegment } from '@/hooks/use-active-segment'
import { usePersistence } from '@/hooks/use-persistence'
import { useKeyboardShortcuts } from '@/hooks/use-keyboard-shortcuts'

function App() {
  useActiveSegment()
  usePersistence()
  useKeyboardShortcuts()

  return <Layout />
}

export default App
