import { openDB, type IDBPDatabase } from 'idb'
import type { ProjectMeta, Segment, TrackMeta, GlossaryTerm } from '@/types'

// ---- Database schema ----

interface YakiIkaDB {
  projects: {
    key: string
    value: ProjectData
  }
  settings: {
    key: string
    value: unknown
  }
}

export interface ProjectData {
  meta: ProjectMeta
  segments: Segment[]
  trackMetas: TrackMeta[]
  terms: GlossaryTerm[]
  videoFileName: string | null
}

const DB_NAME = 'yaki-ika-review'
const DB_VERSION = 1

let dbPromise: Promise<IDBPDatabase<YakiIkaDB>> | null = null

function getDB(): Promise<IDBPDatabase<YakiIkaDB>> {
  if (!dbPromise) {
    dbPromise = openDB<YakiIkaDB>(DB_NAME, DB_VERSION, {
      upgrade(db) {
        if (!db.objectStoreNames.contains('projects')) {
          db.createObjectStore('projects')
        }
        if (!db.objectStoreNames.contains('settings')) {
          db.createObjectStore('settings')
        }
      },
    })
  }
  return dbPromise
}

// ---- Project persistence ----

export async function saveProject(name: string, data: ProjectData): Promise<void> {
  const db = await getDB()
  await db.put('projects', data, name)
}

export async function loadProject(name: string): Promise<ProjectData | undefined> {
  const db = await getDB()
  return db.get('projects', name)
}

export async function loadLatestProject(): Promise<{ name: string; data: ProjectData } | null> {
  const db = await getDB()
  const keys = await db.getAllKeys('projects')
  if (keys.length === 0) return null

  // Find the most recently modified project
  let latest: { name: string; data: ProjectData } | null = null
  for (const key of keys) {
    const data = await db.get('projects', key)
    if (data) {
      if (!latest || data.meta.lastModifiedAt > latest.data.meta.lastModifiedAt) {
        latest = { name: key as string, data }
      }
    }
  }
  return latest
}

export async function deleteProject(name: string): Promise<void> {
  const db = await getDB()
  await db.delete('projects', name)
}

export async function listProjects(): Promise<string[]> {
  const db = await getDB()
  const keys = await db.getAllKeys('projects')
  return keys as string[]
}

// ---- Settings persistence ----

export async function saveSetting(key: string, value: unknown): Promise<void> {
  const db = await getDB()
  await db.put('settings', value, key)
}

export async function loadSetting<T>(key: string): Promise<T | undefined> {
  const db = await getDB()
  return db.get('settings', key) as Promise<T | undefined>
}
