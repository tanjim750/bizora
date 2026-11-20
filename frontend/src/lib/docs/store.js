import fs from 'node:fs'
import path from 'node:path'
import { DEFAULT_SCHEDULE, getDefaultDocsConfig } from './config.js'
import { TEAM_MEMBERS, YC_PITCH_SECTIONS, TECHNICAL_SECTIONS } from './content.js'

let memoryConfig = null
let memoryContent = null

function getConfigFilePath() {
  return path.resolve(process.cwd(), 'src/data/docs-config.json')
}

function getContentFilePath() {
  return path.resolve(process.cwd(), 'src/data/docs-content.json')
}

export function loadDocsConfig() {
  if (memoryConfig) return memoryConfig
  try {
    const filePath = getConfigFilePath()
    if (fs.existsSync(filePath)) {
      const raw = fs.readFileSync(filePath, 'utf8')
      memoryConfig = { ...getDefaultDocsConfig(), ...JSON.parse(raw) }
      return memoryConfig
    }
  } catch (err) {
    console.warn('[DocsStore] Failed to read docs-config.json, using defaults:', err.message)
  }
  memoryConfig = getDefaultDocsConfig()
  return memoryConfig
}

export function saveDocsConfig(newConfig) {
  memoryConfig = {
    ...loadDocsConfig(),
    ...newConfig,
    updatedAt: new Date().toISOString(),
  }
  try {
    const filePath = getConfigFilePath()
    const dir = path.dirname(filePath)
    if (!fs.existsSync(dir)) fs.mkdirSync(dir, { recursive: true })
    fs.writeFileSync(filePath, JSON.stringify(memoryConfig, null, 2), 'utf8')
  } catch (err) {
    console.warn('[DocsStore] Failed to persist docs-config.json to disk:', err.message)
  }
  return memoryConfig
}

export function loadDocsContent() {
  if (memoryContent) return memoryContent
  try {
    const filePath = getContentFilePath()
    if (fs.existsSync(filePath)) {
      const raw = fs.readFileSync(filePath, 'utf8')
      memoryContent = JSON.parse(raw)
      return memoryContent
    }
  } catch (err) {
    console.warn('[DocsStore] Failed to read docs-content.json, using defaults:', err.message)
  }
  memoryContent = {
    teamMembers: TEAM_MEMBERS,
    pitchSections: YC_PITCH_SECTIONS,
    technicalSections: TECHNICAL_SECTIONS,
  }
  return memoryContent
}

export function saveDocsContent(newContent) {
  memoryContent = {
    ...loadDocsContent(),
    ...newContent,
    updatedAt: new Date().toISOString(),
  }
  try {
    const filePath = getContentFilePath()
    const dir = path.dirname(filePath)
    if (!fs.existsSync(dir)) fs.mkdirSync(dir, { recursive: true })
    fs.writeFileSync(filePath, JSON.stringify(memoryContent, null, 2), 'utf8')
  } catch (err) {
    console.warn('[DocsStore] Failed to persist docs-content.json to disk:', err.message)
  }
  return memoryContent
}
