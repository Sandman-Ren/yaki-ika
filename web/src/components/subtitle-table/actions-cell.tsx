import { memo, useCallback } from 'react'
import { Button } from '@/components/ui/button'
import { MessageSquare } from 'lucide-react'
import { openIssue, type IssueContext } from '@/lib/github'

interface ActionsCellProps {
  issueContext: IssueContext
}

export const ActionsCell = memo(function ActionsCell({ issueContext }: ActionsCellProps) {
  const handleIssue = useCallback(
    (e: React.MouseEvent) => {
      e.stopPropagation()
      openIssue(issueContext)
    },
    [issueContext]
  )

  return (
    <div className="flex items-center justify-end">
      <Button
        variant="ghost"
        size="icon"
        className="h-6 w-6"
        title="Suggest translation change"
        onClick={handleIssue}
      >
        <MessageSquare className="h-3.5 w-3.5" />
      </Button>
    </div>
  )
})
