import { useEffect, useRef } from 'react'
import { useProjectStore } from '@/stores/project-store'

const DEBOUNCE_MS = 500

/**
 * Auto-saves project to IndexedDB when segments change.
 * Debounced to avoid excessive writes during rapid editing.
 */
export function usePersistence() {
  const segments = useProjectStore((s) => s.segments)
  const meta = useProjectStore((s) => s.meta)
  const saveToIndexedDB = useProjectStore((s) => s.saveToIndexedDB)
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  // Auto-save on segment/meta changes
  useEffect(() => {
    if (!meta) return

    if (timerRef.current) clearTimeout(timerRef.current)
    timerRef.current = setTimeout(() => {
      saveToIndexedDB()
    }, DEBOUNCE_MS)

    return () => {
      if (timerRef.current) clearTimeout(timerRef.current)
    }
  }, [segments, meta, saveToIndexedDB])

  // Restore on mount
  useEffect(() => {
    const restore = async () => {
      const isLoaded = useProjectStore.getState().isLoaded
      if (isLoaded) return
      await useProjectStore.getState().loadFromIndexedDB()
    }
    restore()
  }, [])
}
