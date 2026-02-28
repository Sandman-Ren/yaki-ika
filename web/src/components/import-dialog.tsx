import { useState, useCallback } from 'react'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
  DialogFooter,
  DialogClose,
} from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'
import { useProjectStore } from '@/stores/project-store'
import { Upload } from 'lucide-react'

interface FileSlots {
  video: File | null
  jaSrt: File | null
  translatedSrt: File | null
  termsFile: File | null
}

function classifyFile(file: File): keyof FileSlots | null {
  const name = file.name.toLowerCase()
  const ext = name.split('.').pop() ?? ''

  if (['mp4', 'webm', 'mkv'].includes(ext)) return 'video'
  if (ext === 'json') return 'termsFile'
  if (ext === 'srt') {
    if (name.includes('.ja.') || name.includes('.ja_') || name.includes('_ja.') || name.includes('-ja.')) return 'jaSrt'
    if (name.includes('.en.') || name.includes('.en_') || name.includes('_en.') || name.includes('-en.') ||
        name.includes('.zh.') || name.includes('.translated.')) return 'translatedSrt'
    // Fallback: first SRT → jaSrt, second → translated
    return null
  }

  return null
}

const SLOT_LABELS: Record<keyof FileSlots, string> = {
  video: 'Video (.mp4, .webm, .mkv)',
  jaSrt: 'Japanese SRT',
  translatedSrt: 'Translated SRT',
  termsFile: 'Terms JSON (optional)',
}

const SLOT_ACCEPT: Record<keyof FileSlots, string> = {
  video: '.mp4,.webm,.mkv',
  jaSrt: '.srt',
  translatedSrt: '.srt',
  termsFile: '.json',
}

export function ImportDialog() {
  const [open, setOpen] = useState(false)
  const [files, setFiles] = useState<FileSlots>({
    video: null,
    jaSrt: null,
    translatedSrt: null,
    termsFile: null,
  })
  const loadProject = useProjectStore((s) => s.loadProject)

  const setSlot = useCallback((slot: keyof FileSlots, file: File | null) => {
    setFiles((prev) => ({ ...prev, [slot]: file }))
  }, [])

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault()
      const droppedFiles = Array.from(e.dataTransfer.files)
      const unclassified: File[] = []

      for (const file of droppedFiles) {
        const slot = classifyFile(file)
        if (slot) {
          setSlot(slot, file)
        } else {
          unclassified.push(file)
        }
      }

      // Assign unclassified SRTs in order: jaSrt first, then translatedSrt
      for (const file of unclassified) {
        if (file.name.toLowerCase().endsWith('.srt')) {
          setFiles((prev) => {
            if (!prev.jaSrt) return { ...prev, jaSrt: file }
            if (!prev.translatedSrt) return { ...prev, translatedSrt: file }
            return prev
          })
        }
      }
    },
    [setSlot]
  )

  const canImport = files.video && files.jaSrt && files.translatedSrt

  const handleImport = async () => {
    if (!files.video || !files.jaSrt || !files.translatedSrt) return

    await loadProject({
      video: files.video,
      jaSrt: files.jaSrt,
      translatedSrt: files.translatedSrt,
      termsFile: files.termsFile ?? undefined,
    })

    setFiles({ video: null, jaSrt: null, translatedSrt: null, termsFile: null })
    setOpen(false)
  }

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button variant="outline" size="sm">
          <Upload className="mr-2 h-4 w-4" />
          Import
        </Button>
      </DialogTrigger>
      <DialogContent className="sm:max-w-lg">
        <DialogHeader>
          <DialogTitle>Import Project Files</DialogTitle>
        </DialogHeader>

        <div
          className="rounded-lg border-2 border-dashed border-muted-foreground/25 p-6 text-center transition-colors hover:border-muted-foreground/50"
          onDragOver={(e) => e.preventDefault()}
          onDrop={handleDrop}
        >
          <p className="text-sm text-muted-foreground">
            Drag & drop files here, or use the pickers below
          </p>
        </div>

        <div className="grid gap-3">
          {(Object.keys(SLOT_LABELS) as (keyof FileSlots)[]).map((slot) => (
            <div key={slot} className="flex items-center gap-3">
              <label className="w-44 text-sm font-medium shrink-0">
                {SLOT_LABELS[slot]}
              </label>
              <input
                type="file"
                accept={SLOT_ACCEPT[slot]}
                className="text-sm file:mr-2 file:rounded-md file:border-0 file:bg-secondary file:px-3 file:py-1 file:text-sm file:font-medium"
                onChange={(e) => setSlot(slot, e.target.files?.[0] ?? null)}
              />
              {files[slot] && (
                <span className="truncate text-xs text-muted-foreground max-w-32">
                  {files[slot]!.name}
                </span>
              )}
            </div>
          ))}
        </div>

        <DialogFooter>
          <DialogClose asChild>
            <Button variant="ghost">Cancel</Button>
          </DialogClose>
          <Button onClick={handleImport} disabled={!canImport}>
            Load Project
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
