import { useProjectStore } from '@/stores/project-store'
import { FileVideo } from 'lucide-react'

export function WelcomeScreen() {
  const videoFileName = useProjectStore((s) => s.videoFileName)
  const videoUrl = useProjectStore((s) => s.videoUrl)
  const reloadVideo = useProjectStore((s) => s.reloadVideo)

  // Session restored from IndexedDB but video needs re-import
  if (videoFileName && !videoUrl) {
    return (
      <div className="flex flex-col items-center justify-center bg-muted/30 aspect-video max-h-[40vh] gap-3">
        <FileVideo className="h-8 w-8 text-muted-foreground" />
        <p className="text-sm text-muted-foreground">
          Previous session restored. Re-import video to continue:
        </p>
        <p className="text-xs font-mono text-muted-foreground">{videoFileName}</p>
        <label className="cursor-pointer">
          <input
            type="file"
            accept=".mp4,.webm,.mkv"
            className="hidden"
            onChange={(e) => {
              const f = e.target.files?.[0]
              if (f) reloadVideo(f)
            }}
          />
          <span className="inline-flex items-center gap-2 rounded-md border bg-background px-3 py-1.5 text-sm font-medium hover:bg-muted transition-colors">
            <FileVideo className="h-4 w-4" />
            Pick video file
          </span>
        </label>
      </div>
    )
  }

  return (
    <div className="flex flex-col items-center justify-center bg-muted/30 aspect-video max-h-[40vh] gap-2">
      <FileVideo className="h-8 w-8 text-muted-foreground" />
      <p className="text-sm text-muted-foreground">Import a project to begin</p>
    </div>
  )
}
