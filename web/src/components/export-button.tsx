import { useCallback } from 'react'
import { Button } from '@/components/ui/button'
import { useProjectStore } from '@/stores/project-store'
import { buildSrt } from '@/lib/srt'
import { Download } from 'lucide-react'

export function ExportButton() {
  const segments = useProjectStore((s) => s.segments)
  const projectName = useProjectStore((s) => s.projectName)
  const isLoaded = useProjectStore((s) => s.isLoaded)

  const handleExport = useCallback(() => {
    const srtContent = buildSrt(segments)
    const blob = new Blob([srtContent], { type: 'text/srt;charset=utf-8' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `${projectName || 'subtitles'}.edited.srt`
    a.click()
    URL.revokeObjectURL(url)
  }, [segments, projectName])

  return (
    <Button variant="outline" size="sm" onClick={handleExport} disabled={!isLoaded}>
      <Download className="mr-2 h-4 w-4" />
      Export SRT
    </Button>
  )
}
