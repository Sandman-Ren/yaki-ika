import type { GlossaryTerm, LanguageCode } from '@/types'
import { LANGUAGE_LABELS } from '@/types'

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

// ---- File classification for multi-track import ----

const VIDEO_EXTENSIONS = new Set(['.mp4', '.webm', '.mkv', '.avi', '.mov'])
const SRT_EXTENSIONS = new Set(['.srt', '.vtt', '.ass', '.ssa'])

/** Known language patterns in filenames */
const LANG_PATTERNS: { pattern: RegExp; lang: LanguageCode }[] = [
  { pattern: /[._-]ja[._-]|[._-]ja$|\.ja\./i, lang: 'ja' },
  { pattern: /[._-]en[._-]|[._-]en$|\.en\./i, lang: 'en' },
  { pattern: /[._-]zh-CN[._-]|[._-]zh-CN$|\.zh-CN\.|[._-]zh_CN/i, lang: 'zh-CN' },
  { pattern: /[._-]zh-TW[._-]|[._-]zh-TW$|\.zh-TW\.|[._-]zh_TW/i, lang: 'zh-TW' },
  { pattern: /[._-]zh[._-]|[._-]zh$|\.zh\./i, lang: 'zh-CN' },
]

export type FileCategory = 'video' | 'ja-srt' | 'translation-srt' | 'terms' | 'unknown'

export interface ClassifiedFile {
  file: File
  category: FileCategory
  /** Detected language for SRT files */
  detectedLang?: LanguageCode
  /** Display label for detected language */
  detectedLabel?: string
}

function getExtension(name: string): string {
  const i = name.lastIndexOf('.')
  return i >= 0 ? name.slice(i).toLowerCase() : ''
}

/** Detect language from filename patterns */
function detectLanguage(name: string): { lang: LanguageCode; label: string } | null {
  for (const { pattern, lang } of LANG_PATTERNS) {
    if (pattern.test(name)) {
      return { lang, label: LANGUAGE_LABELS[lang] ?? lang }
    }
  }
  return null
}

/** Classify a dropped/selected file by extension and name patterns */
export function classifyFile(file: File): ClassifiedFile {
  const ext = getExtension(file.name)

  if (VIDEO_EXTENSIONS.has(ext)) {
    return { file, category: 'video' }
  }

  if (ext === '.json') {
    return { file, category: 'terms' }
  }

  if (SRT_EXTENSIONS.has(ext)) {
    const lang = detectLanguage(file.name)
    if (lang?.lang === 'ja') {
      return { file, category: 'ja-srt' }
    }
    if (lang) {
      return { file, category: 'translation-srt', detectedLang: lang.lang, detectedLabel: lang.label }
    }
    // Unrecognized SRT — user will assign language manually
    return { file, category: 'unknown' }
  }

  return { file, category: 'unknown' }
}

/** Classify multiple files at once, returning them grouped */
export function classifyFiles(files: File[]): ClassifiedFile[] {
  return files.map(classifyFile)
}
