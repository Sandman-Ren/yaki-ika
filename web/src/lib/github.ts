import { formatTime } from '@/lib/srt'

const REPO_OWNER = 'Sandman-Ren'
const REPO_NAME = 'yaki-ika'

export interface IssueContext {
  segmentIndex: number
  startTime: number
  endTime: number
  sourceText: string
  trackId: string
  trackLabel: string
  currentTranslation: string
  projectName: string
}

/** Build a pre-filled GitHub issue URL for a translation suggestion */
export function buildIssueUrl(ctx: IssueContext): string {
  const title = `[Subtitle] Segment ${ctx.segmentIndex + 1} (${formatTime(ctx.startTime)}) – ${ctx.trackLabel}`

  const body = `## Translation Suggestion

**Project**: ${ctx.projectName}
**Segment**: #${ctx.segmentIndex + 1}
**Time**: ${formatTime(ctx.startTime)} – ${formatTime(ctx.endTime)}
**Track**: ${ctx.trackLabel}

### Source (Japanese)
\`\`\`
${ctx.sourceText}
\`\`\`

### Current Translation (${ctx.trackLabel})
\`\`\`
${ctx.currentTranslation}
\`\`\`

### Suggested Change
<!-- Provide a corrected or improved translation below -->


### Context
<!-- Any additional context about why this translation needs attention -->
`

  const params = new URLSearchParams({
    title,
    body,
    labels: 'subtitle-review',
  })

  return `https://github.com/${REPO_OWNER}/${REPO_NAME}/issues/new?${params.toString()}`
}

/** Open the pre-filled issue in a new tab */
export function openIssue(ctx: IssueContext): void {
  window.open(buildIssueUrl(ctx), '_blank', 'noopener')
}
