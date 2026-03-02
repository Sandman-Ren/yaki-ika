import { useCallback } from 'react'
import { useProjectStore } from '@/stores/project-store'
import { useUiStore } from '@/stores/ui-store'
import { classifyFiles } from '@/lib/file-loader'
import { LANGUAGE_LABELS, type LanguageCode, type ImportTrackFile } from '@/types'
import { Upload, FileVideo, X, Plus, FileText, FileJson } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { useState } from 'react'

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

export function WelcomeScreen() {
  const videoFileName = useProjectStore((s) => s.videoFileName)
  const videoUrl = useProjectStore((s) => s.videoUrl)
  const reloadVideo = useProjectStore((s) => s.reloadVideo)
  const pendingRestore = useProjectStore((s) => s.pendingRestore)
  const restoreSession = useProjectStore((s) => s.restoreSession)
  const dismissRestore = useProjectStore((s) => s.dismissRestore)

  // Session was restored and needs video re-import
  if (videoFileName && !videoUrl) {
    return (
      <div className="flex flex-col items-center justify-center bg-muted/30 aspect-video max-h-[40vh] gap-3">
        <FileVideo className="h-8 w-8 text-muted-foreground" />
        <p className="text-sm text-muted-foreground">
          Session restored. Re-import video to continue:
        </p>
        <p className="text-xs font-mono text-muted-foreground max-w-md truncate">{videoFileName}</p>
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

  // Saved session found — ask user whether to restore
  if (pendingRestore) {
    return (
      <div className="flex flex-col items-center bg-muted/30 py-8 px-4">
        <div className="w-full max-w-md space-y-4">
          <div className="rounded-lg border bg-background p-5 text-center space-y-3">
            <p className="text-sm font-medium">Previous session found</p>
            <p className="text-xs text-muted-foreground">
              <span className="font-mono">{pendingRestore.name}</span>
              {' '}&mdash; {pendingRestore.segmentCount} segments, {pendingRestore.trackCount} track{pendingRestore.trackCount !== 1 ? 's' : ''}
            </p>
            <div className="flex items-center justify-center gap-2">
              <Button variant="outline" size="sm" onClick={dismissRestore}>
                Start fresh
              </Button>
              <Button size="sm" onClick={restoreSession}>
                Restore session
              </Button>
            </div>
          </div>

          <div className="text-center">
            <p className="text-xs text-muted-foreground mb-3">Or import a new project:</p>
          </div>

          <InlineImportForm />
        </div>
      </div>
    )
  }

  // No project loaded, no saved session — show inline import form
  return <InlineImportForm />
}

/** Full import form shown directly on the page when no project is loaded */
function InlineImportForm() {
  const [files, setFiles] = useState<FileSlots>(EMPTY_SLOTS)
  const [addLang, setAddLang] = useState<LanguageCode>('en')
  const [loading, setLoading] = useState(false)
  const loadProject = useProjectStore((s) => s.loadProject)
  const setActiveTrackId = useUiStore((s) => s.setActiveTrackId)
  const setVisibleTrackIds = useUiStore((s) => s.setVisibleTrackIds)

  const applyClassified = useCallback((classified: ReturnType<typeof classifyFiles>) => {
    setFiles((prev) => {
      const next = { ...prev, tracks: [...prev.tracks] }
      const unassigned: File[] = []

      for (const c of classified) {
        switch (c.category) {
          case 'video': next.video = c.file; break
          case 'ja-srt': next.jaSrt = c.file; break
          case 'translation-srt':
            if (c.detectedLang && c.detectedLabel && !next.tracks.some((t) => t.lang === c.detectedLang)) {
              next.tracks.push({ file: c.file, lang: c.detectedLang, label: c.detectedLabel })
            }
            break
          case 'terms': next.termsFile = c.file; break
          case 'unknown':
            if (c.file.name.toLowerCase().endsWith('.srt')) unassigned.push(c.file)
            break
        }
      }

      for (const file of unassigned) {
        if (!next.jaSrt) { next.jaSrt = file; continue }
        const usedLangs = new Set(next.tracks.map((t) => t.lang))
        const available = ASSIGNABLE_LANGUAGES.find((l) => !usedLangs.has(l.value))
        if (available) next.tracks.push({ file, lang: available.value, label: available.label })
      }

      return next
    })
  }, [])

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    applyClassified(classifyFiles(Array.from(e.dataTransfer.files)))
  }, [applyClassified])

  const handleFilePick = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const picked = Array.from(e.target.files ?? [])
    if (picked.length > 0) applyClassified(classifyFiles(picked))
    e.target.value = ''
  }, [applyClassified])

  const addTrackFromFile = useCallback((file: File) => {
    setFiles((prev) => {
      if (prev.tracks.some((t) => t.lang === addLang)) return prev
      return { ...prev, tracks: [...prev.tracks, { file, lang: addLang, label: LANGUAGE_LABELS[addLang] ?? addLang }] }
    })
  }, [addLang])

  const canImport = files.video && files.jaSrt && files.tracks.length > 0

  const handleImport = async () => {
    if (!files.video || !files.jaSrt || files.tracks.length === 0) return
    setLoading(true)
    try {
      const translationSrts: ImportTrackFile[] = files.tracks.map((t) => ({ file: t.file, lang: t.lang, label: t.label }))
      await loadProject({ video: files.video, jaSrt: files.jaSrt, translationSrts, termsFile: files.termsFile ?? undefined })
      const trackIds = files.tracks.map((t) => t.lang)
      setVisibleTrackIds(trackIds)
      setActiveTrackId(trackIds[0] ?? null)
    } finally {
      setLoading(false)
    }
  }

  const usedLangs = new Set(files.tracks.map((t) => t.lang))
  const availableLangs = ASSIGNABLE_LANGUAGES.filter((l) => !usedLangs.has(l.value))
  const hasAnyFile = files.video || files.jaSrt || files.tracks.length > 0 || files.termsFile

  return (
    <div className="flex flex-col items-center bg-muted/30 py-8 px-4">
      <div className="w-full max-w-md space-y-4">
        {/* Drop zone */}
        <div
          className="rounded-lg border-2 border-dashed border-muted-foreground/25 p-8 text-center transition-colors hover:border-muted-foreground/50"
          onDragOver={(e) => e.preventDefault()}
          onDrop={handleDrop}
        >
          <Upload className="mx-auto h-8 w-8 text-muted-foreground/50 mb-2" />
          <p className="text-sm text-muted-foreground">
            Drag & drop your video, SRT, and terms files here
          </p>
          <label className="mt-2 inline-block">
            <input type="file" multiple accept=".mp4,.webm,.mkv,.srt,.vtt,.json" className="hidden" onChange={handleFilePick} />
            <span className="cursor-pointer text-xs text-primary underline">or browse files</span>
          </label>
        </div>

        {/* File slots — only shown once any file is added */}
        {hasAnyFile && (
          <div className="space-y-2 rounded-lg border bg-background p-4">
            <FileSlotRow icon={<FileVideo className="h-4 w-4" />} label="Video" file={files.video}
              onRemove={() => setFiles((p) => ({ ...p, video: null }))} accept=".mp4,.webm,.mkv"
              onPick={(f) => setFiles((p) => ({ ...p, video: f }))} />
            <FileSlotRow icon={<FileText className="h-4 w-4" />} label="Source (JA)" file={files.jaSrt}
              onRemove={() => setFiles((p) => ({ ...p, jaSrt: null }))} accept=".srt,.vtt"
              onPick={(f) => setFiles((p) => ({ ...p, jaSrt: f }))} />

            <div className="border-t my-2" />

            <p className="text-xs font-medium text-muted-foreground">Translation Tracks</p>
            {files.tracks.map((track, i) => (
              <div key={track.lang} className="flex items-center gap-2 min-w-0">
                <span className="w-20 text-sm shrink-0 truncate">{track.label}</span>
                <span className="flex-1 min-w-0 truncate text-xs text-muted-foreground">{track.file.name}</span>
                <Button variant="ghost" size="icon" className="h-6 w-6 shrink-0" onClick={() => setFiles((p) => ({ ...p, tracks: p.tracks.filter((_, j) => j !== i) }))}>
                  <X className="h-3 w-3" />
                </Button>
              </div>
            ))}
            {availableLangs.length > 0 && (
              <div className="flex items-center gap-2">
                <select value={addLang} onChange={(e) => setAddLang(e.target.value as LanguageCode)}
                  className="h-7 rounded border bg-background px-2 text-sm">
                  {availableLangs.map((l) => <option key={l.value} value={l.value}>{l.label}</option>)}
                </select>
                <label className="inline-flex items-center gap-1 cursor-pointer">
                  <input type="file" accept=".srt,.vtt" className="hidden" onChange={(e) => { const f = e.target.files?.[0]; if (f) addTrackFromFile(f); e.target.value = '' }} />
                  <Button variant="outline" size="sm" className="h-7 text-xs" asChild>
                    <span><Plus className="mr-1 h-3 w-3" />Add track</span>
                  </Button>
                </label>
              </div>
            )}

            <div className="border-t my-2" />

            <FileSlotRow icon={<FileJson className="h-4 w-4" />} label="Terms (opt)" file={files.termsFile}
              onRemove={() => setFiles((p) => ({ ...p, termsFile: null }))} accept=".json"
              onPick={(f) => setFiles((p) => ({ ...p, termsFile: f }))} />

            <Button className="w-full mt-3" onClick={handleImport} disabled={!canImport || loading}>
              {loading ? 'Loading...' : 'Load Project'}
            </Button>
          </div>
        )}
      </div>
    </div>
  )
}

function FileSlotRow({ icon, label, file, onRemove, accept, onPick }: {
  icon: React.ReactNode; label: string; file: File | null
  onRemove: () => void; accept: string; onPick: (file: File) => void
}) {
  return (
    <div className="flex items-center gap-2 min-w-0">
      <span className="text-muted-foreground shrink-0">{icon}</span>
      <span className="w-20 text-sm font-medium shrink-0">{label}</span>
      {file ? (
        <>
          <span className="flex-1 min-w-0 truncate text-xs text-muted-foreground" title={file.name}>{file.name}</span>
          <Button variant="ghost" size="icon" className="h-6 w-6 shrink-0" onClick={onRemove}>
            <X className="h-3 w-3" />
          </Button>
        </>
      ) : (
        <label className="cursor-pointer">
          <input type="file" accept={accept} className="hidden" onChange={(e) => { const f = e.target.files?.[0]; if (f) onPick(f); e.target.value = '' }} />
          <span className="text-xs text-primary underline">Pick file</span>
        </label>
      )}
    </div>
  )
}
