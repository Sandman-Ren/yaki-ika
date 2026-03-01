/** Keyboard shortcut definitions */
export const SHORTCUTS = {
  // Playback
  'Space': 'Play / Pause',
  'Alt+ArrowLeft': 'Seek backward 5s',
  'Alt+ArrowRight': 'Seek forward 5s',

  // Navigation
  'ArrowUp': 'Previous segment',
  'ArrowDown': 'Next segment',
  'Tab': 'Next track column',
  'Shift+Tab': 'Previous track column',

  // Editing
  'Enter': 'Start editing / commit edit',
  'Escape': 'Cancel edit',
  'Shift+Enter': 'Newline in edit mode',

  // Review
  'Ctrl+Enter': 'Approve and advance',
  'Ctrl+Shift+Enter': 'Mark needs-revision and advance',

  // Undo/Redo
  'Ctrl+Z': 'Undo',
  'Ctrl+Shift+Z': 'Redo',

  // Search
  'Ctrl+F': 'Focus search',

  // Help
  '?': 'Toggle shortcuts help',
} as const

export type ShortcutKey = keyof typeof SHORTCUTS

/** Parse a keyboard event into a shortcut key string */
export function eventToShortcut(e: KeyboardEvent): string {
  const parts: string[] = []
  if (e.ctrlKey || e.metaKey) parts.push('Ctrl')
  if (e.shiftKey) parts.push('Shift')
  if (e.altKey) parts.push('Alt')
  parts.push(e.key === ' ' ? 'Space' : e.key)
  return parts.join('+')
}

/** Group shortcuts by category for display */
export function getShortcutGroups(): { label: string; shortcuts: { key: string; description: string }[] }[] {
  return [
    {
      label: 'Playback',
      shortcuts: [
        { key: 'Space', description: SHORTCUTS['Space'] },
        { key: 'Alt+←', description: SHORTCUTS['Alt+ArrowLeft'] },
        { key: 'Alt+→', description: SHORTCUTS['Alt+ArrowRight'] },
      ],
    },
    {
      label: 'Navigation',
      shortcuts: [
        { key: '↑', description: SHORTCUTS['ArrowUp'] },
        { key: '↓', description: SHORTCUTS['ArrowDown'] },
        { key: 'Tab', description: SHORTCUTS['Tab'] },
        { key: 'Shift+Tab', description: SHORTCUTS['Shift+Tab'] },
      ],
    },
    {
      label: 'Editing',
      shortcuts: [
        { key: 'Enter', description: SHORTCUTS['Enter'] },
        { key: 'Escape', description: SHORTCUTS['Escape'] },
        { key: 'Shift+Enter', description: SHORTCUTS['Shift+Enter'] },
      ],
    },
    {
      label: 'Review',
      shortcuts: [
        { key: 'Ctrl+Enter', description: SHORTCUTS['Ctrl+Enter'] },
        { key: 'Ctrl+Shift+Enter', description: SHORTCUTS['Ctrl+Shift+Enter'] },
      ],
    },
    {
      label: 'General',
      shortcuts: [
        { key: 'Ctrl+Z', description: SHORTCUTS['Ctrl+Z'] },
        { key: 'Ctrl+Shift+Z', description: SHORTCUTS['Ctrl+Shift+Z'] },
        { key: 'Ctrl+F', description: SHORTCUTS['Ctrl+F'] },
        { key: '?', description: SHORTCUTS['?'] },
      ],
    },
  ]
}
