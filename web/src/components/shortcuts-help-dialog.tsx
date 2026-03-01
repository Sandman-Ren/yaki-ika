import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { useUiStore } from '@/stores/ui-store'
import { getShortcutGroups } from '@/lib/keyboard'

export function ShortcutsHelpDialog() {
  const show = useUiStore((s) => s.showShortcutsHelp)
  const setShow = useUiStore((s) => s.setShowShortcutsHelp)
  const groups = getShortcutGroups()

  return (
    <Dialog open={show} onOpenChange={setShow}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>Keyboard Shortcuts</DialogTitle>
        </DialogHeader>

        <div className="space-y-4 max-h-[60vh] overflow-auto">
          {groups.map((group) => (
            <div key={group.label}>
              <h3 className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-1.5">
                {group.label}
              </h3>
              <div className="space-y-1">
                {group.shortcuts.map((s) => (
                  <div key={s.key} className="flex items-center justify-between text-sm">
                    <span className="text-muted-foreground">{s.description}</span>
                    <kbd className="ml-4 inline-flex items-center rounded border bg-muted px-1.5 py-0.5 font-mono text-xs text-muted-foreground">
                      {s.key}
                    </kbd>
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>
      </DialogContent>
    </Dialog>
  )
}
