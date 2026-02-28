import { Layout } from '@/components/layout'
import { useActiveSegment } from '@/hooks/use-active-segment'

function App() {
  useActiveSegment()

  return <Layout />
}

export default App
