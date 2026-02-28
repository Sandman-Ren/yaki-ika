import type { GlossaryTerm } from '@/types'

export function readFileAsText(file: File): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader()
    reader.onload = () => resolve(reader.result as string)
    reader.onerror = () => reject(new Error(`Failed to read file: ${file.name}`))
    reader.readAsText(file)
  })
}

export async function parseTermsFile(file: File): Promise<GlossaryTerm[]> {
  const text = await readFileAsText(file)
  const data = JSON.parse(text)

  if (!Array.isArray(data)) {
    throw new Error('Terms file must contain a JSON array')
  }

  return data.map((item: Record<string, unknown>) => ({
    jp: String(item.jp ?? item.source ?? ''),
    target: String(item.target ?? item.en ?? item.translated ?? ''),
    category: String(item.category ?? 'unknown'),
    notes: item.notes != null ? String(item.notes) : undefined,
  }))
}

export function createVideoUrl(file: File): string {
  return URL.createObjectURL(file)
}

export function revokeVideoUrl(url: string): void {
  URL.revokeObjectURL(url)
}
