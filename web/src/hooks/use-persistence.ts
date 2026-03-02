import { useEffect, useRef } from 'react'
import { useProjectStore } from '@/stores/project-store'

const DEBOUNCE_MS = 500

/**
 * Auto-saves project to IndexedDB when segments change.
 * On mount, checks for a saved session and sets pendingRestore
 * (the welcome screen prompts the user to restore or dismiss).
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

  // Check for saved session on mount (does NOT restore — just sets pendingRestore)
  useEffect(() => {
    const { isLoaded, checkForSavedSession } = useProjectStore.getState()
    if (!isLoaded) checkForSavedSession()
  }, [])
}
