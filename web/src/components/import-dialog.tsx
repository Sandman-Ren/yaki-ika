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
import { useUiStore } from '@/stores/ui-store'
import { classifyFiles, type ClassifiedFile } from '@/lib/file-loader'
import { LANGUAGE_LABELS, type LanguageCode, type ImportTrackFile } from '@/types'
import { Upload, X, Plus, FileVideo, FileText, FileJson } from 'lucide-react'

// Languages available for track assignment
const ASSIGNABLE_LANGUAGES: { value: LanguageCode; label: string }[] = [
  { value: 'en', label: 'English' },
  { value: 'zh-CN', label: '简体中文' },
  { value: 'zh-TW', label: '繁體中文' },
]

interface TrackSlot {
  file: File
  lang: LanguageCode
  label: string
}

interface FileSlots {
  video: File | null
  jaSrt: File | null
  tracks: TrackSlot[]
  termsFile: File | null
}

const EMPTY_SLOTS: FileSlots = {
  video: null,
  jaSrt: null,
  tracks: [],
  termsFile: null,
}

export function ImportDialog() {
  const [open, setOpen] = useState(false)
  const [files, setFiles] = useState<FileSlots>(EMPTY_SLOTS)
  const loadProject = useProjectStore((s) => s.loadProject)
  const setActiveTrackId = useUiStore((s) => s.setActiveTrackId)
  const setVisibleTrackIds = useUiStore((s) => s.setVisibleTrackIds)

  // For adding new tracks manually
  const [addLang, setAddLang] = useState<LanguageCode>('en')

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    const droppedFiles = Array.from(e.dataTransfer.files)
    const classified = classifyFiles(droppedFiles)
    applyClassified(classified)
  }, [])

  const applyClassified = useCallback((classified: ClassifiedFile[]) => {
    setFiles((prev) => {
      const next = { ...prev, tracks: [...prev.tracks] }

      // Collect unclassified SRTs for fallback assignment
      const unassigned: File[] = []

      for (const c of classified) {
        switch (c.category) {
          case 'video':
            next.video = c.file
            break
          case 'ja-srt':
            next.jaSrt = c.file
            break
          case 'translation-srt':
            if (c.detectedLang && c.detectedLabel) {
              // Skip if we already have this language
              if (!next.tracks.some((t) => t.lang === c.detectedLang)) {
                next.tracks.push({ file: c.file, lang: c.detectedLang, label: c.detectedLabel })
              }
            }
            break
          case 'terms':
            next.termsFile = c.file
            break
          case 'unknown':
            if (c.file.name.toLowerCase().endsWith('.srt')) {
              unassigned.push(c.file)
            }
            break
        }
      }

      // Fallback: assign unclassified SRTs
      for (const file of unassigned) {
        if (!next.jaSrt) {
          next.jaSrt = file
        } else {
          // Assign first available language
          const usedLangs = new Set(next.tracks.map((t) => t.lang))
          const available = ASSIGNABLE_LANGUAGES.find((l) => !usedLangs.has(l.value))
          if (available) {
            next.tracks.push({ file, lang: available.value, label: available.label })
          }
        }
      }

      return next
    })
  }, [])

  const handleFilePick = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const pickedFiles = Array.from(e.target.files ?? [])
    if (pickedFiles.length === 0) return
    const classified = classifyFiles(pickedFiles)
    applyClassified(classified)
    // Reset input so re-picking same file triggers onChange
    e.target.value = ''
  }, [applyClassified])

  const removeTrack = useCallback((index: number) => {
    setFiles((prev) => ({
      ...prev,
      tracks: prev.tracks.filter((_, i) => i !== index),
    }))
  }, [])

  const addTrackFromFile = useCallback(
    (file: File) => {
      setFiles((prev) => {
        if (prev.tracks.some((t) => t.lang === addLang)) return prev
        const label = LANGUAGE_LABELS[addLang] ?? addLang
        return { ...prev, tracks: [...prev.tracks, { file, lang: addLang, label }] }
      })
    },
    [addLang]
  )

  const canImport = files.video && files.jaSrt && files.tracks.length > 0

  const handleImport = async () => {
    if (!files.video || !files.jaSrt || files.tracks.length === 0) return

    const translationSrts: ImportTrackFile[] = files.tracks.map((t) => ({
      file: t.file,
      lang: t.lang,
      label: t.label,
    }))

    await loadProject({
      video: files.video,
      jaSrt: files.jaSrt,
      translationSrts,
      termsFile: files.termsFile ?? undefined,
    })

    // Set UI track state
    const trackIds = files.tracks.map((t) => t.lang)
    setVisibleTrackIds(trackIds)
    setActiveTrackId(trackIds[0] ?? null)

    setFiles(EMPTY_SLOTS)
    setOpen(false)
  }

  const usedLangs = new Set(files.tracks.map((t) => t.lang))
  const availableLangs = ASSIGNABLE_LANGUAGES.filter((l) => !usedLangs.has(l.value))

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

        {/* Drop zone */}
        <div
          className="rounded-lg border-2 border-dashed border-muted-foreground/25 p-6 text-center transition-colors hover:border-muted-foreground/50"
          onDragOver={(e) => e.preventDefault()}
          onDrop={handleDrop}
        >
          <p className="text-sm text-muted-foreground">
            Drag & drop all files here, or use the controls below
          </p>
          <label className="mt-2 inline-block">
            <input
              type="file"
              multiple
              accept=".mp4,.webm,.mkv,.srt,.vtt,.json"
              className="hidden"
              onChange={handleFilePick}
            />
            <span className="cursor-pointer text-xs text-primary underline">Browse files</span>
          </label>
        </div>

        {/* File slots */}
        <div className="space-y-3">
          {/* Video */}
          <FileSlotRow
            icon={<FileVideo className="h-4 w-4" />}
            label="Video"
            file={files.video}
            onRemove={() => setFiles((p) => ({ ...p, video: null }))}
            accept=".mp4,.webm,.mkv"
            onPick={(f) => setFiles((p) => ({ ...p, video: f }))}
          />

          {/* Japanese SRT */}
          <FileSlotRow
            icon={<FileText className="h-4 w-4" />}
            label="Source (JA)"
            file={files.jaSrt}
            onRemove={() => setFiles((p) => ({ ...p, jaSrt: null }))}
            accept=".srt,.vtt"
            onPick={(f) => setFiles((p) => ({ ...p, jaSrt: f }))}
          />

          {/* Separator */}
          <div className="border-t" />

          {/* Translation tracks */}
          <div className="space-y-2">
            <p className="text-xs font-medium text-muted-foreground">Translation Tracks</p>
            {files.tracks.map((track, i) => (
              <div key={track.lang} className="flex items-center gap-2">
                <span className="w-20 text-sm truncate">{track.label}</span>
                <span className="flex-1 truncate text-xs text-muted-foreground">{track.file.name}</span>
                <Button variant="ghost" size="icon" className="h-6 w-6" onClick={() => removeTrack(i)}>
                  <X className="h-3 w-3" />
                </Button>
              </div>
            ))}

            {/* Add track */}
            {availableLangs.length > 0 && (
              <div className="flex items-center gap-2">
                <select
                  value={addLang}
                  onChange={(e) => setAddLang(e.target.value as LanguageCode)}
                  className="h-7 rounded border bg-background px-2 text-sm"
                >
                  {availableLangs.map((l) => (
                    <option key={l.value} value={l.value}>
                      {l.label}
                    </option>
                  ))}
                </select>
                <label className="inline-flex items-center gap-1 cursor-pointer">
                  <input
                    type="file"
                    accept=".srt,.vtt"
                    className="hidden"
                    onChange={(e) => {
                      const f = e.target.files?.[0]
                      if (f) addTrackFromFile(f)
                      e.target.value = ''
                    }}
                  />
                  <Button variant="outline" size="sm" className="h-7 text-xs" asChild>
                    <span>
                      <Plus className="mr-1 h-3 w-3" />
                      Add track
                    </span>
                  </Button>
                </label>
              </div>
            )}
          </div>

          {/* Separator */}
          <div className="border-t" />

          {/* Terms */}
          <FileSlotRow
            icon={<FileJson className="h-4 w-4" />}
            label="Terms (opt)"
            file={files.termsFile}
            onRemove={() => setFiles((p) => ({ ...p, termsFile: null }))}
            accept=".json"
            onPick={(f) => setFiles((p) => ({ ...p, termsFile: f }))}
          />
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

// ---- Reusable file slot row ----

function FileSlotRow({
  icon,
  label,
  file,
  onRemove,
  accept,
  onPick,
}: {
  icon: React.ReactNode
  label: string
  file: File | null
  onRemove: () => void
  accept: string
  onPick: (file: File) => void
}) {
  return (
    <div className="flex items-center gap-2">
      <span className="text-muted-foreground">{icon}</span>
      <span className="w-20 text-sm font-medium shrink-0">{label}</span>
      {file ? (
        <>
          <span className="flex-1 truncate text-xs text-muted-foreground">{file.name}</span>
          <Button variant="ghost" size="icon" className="h-6 w-6" onClick={onRemove}>
            <X className="h-3 w-3" />
          </Button>
        </>
      ) : (
        <label className="cursor-pointer">
          <input
            type="file"
            accept={accept}
            className="hidden"
            onChange={(e) => {
              const f = e.target.files?.[0]
              if (f) onPick(f)
              e.target.value = ''
            }}
          />
          <span className="text-xs text-primary underline">Pick file</span>
        </label>
      )}
    </div>
  )
}
