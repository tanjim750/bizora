import test from 'node:test'
import assert from 'node:assert/strict'
import fs from 'node:fs'
import path from 'node:path'
import {
  DEFAULT_SCHEDULE,
  getDefaultDocsConfig,
  evaluateDocsAccess,
  isDocsAdmin,
} from '../src/lib/docs/config.js'
import { TEAM_MEMBERS, YC_PITCH_SECTIONS, TECHNICAL_SECTIONS } from '../src/lib/docs/content.js'
import { generateMarkdownExport } from '../src/lib/docs/export.js'
import { DEFAULT_LIVE_STATS, LIVE_FEATURE_MATRIX } from '../src/lib/docs/liveStats.js'

test('docs config defaults conform to critical scheduling requirements', () => {
  const cfg = getDefaultDocsConfig()
  assert.equal(cfg.enabled, true)
  assert.equal(cfg.overrideMode, 'SCHEDULE')
  assert.equal(cfg.startDate, '2026-06-10T00:00:00+06:00')
  assert.equal(cfg.endDate, '2026-06-14T23:59:59+06:00')
  assert.equal(cfg.timezone, 'Asia/Dhaka')
  assert.ok(cfg.teamName)
})

test('evaluateDocsAccess handles all override modes and date windows', () => {
  const cfg = getDefaultDocsConfig()

  // 1. Inside schedule window (June 12, 2026)
  const insideDate = new Date('2026-06-12T12:00:00+06:00')
  const resInside = evaluateDocsAccess(cfg, null, insideDate)
  assert.equal(resInside.granted, true)
  assert.equal(resInside.publicGranted, true)
  assert.equal(resInside.publicReason, 'SCHEDULE_ACTIVE')

  // 2. Before schedule window (June 01, 2026)
  const beforeDate = new Date('2026-06-01T12:00:00+06:00')
  const resBefore = evaluateDocsAccess(cfg, null, beforeDate)
  assert.equal(resBefore.granted, false)
  assert.equal(resBefore.publicGranted, false)
  assert.equal(resBefore.publicReason, 'SCHEDULE_PENDING')

  // 3. After schedule window (June 20, 2026)
  const afterDate = new Date('2026-06-20T12:00:00+06:00')
  const resAfter = evaluateDocsAccess(cfg, null, afterDate)
  assert.equal(resAfter.granted, false)
  assert.equal(resAfter.publicGranted, false)
  assert.equal(resAfter.publicReason, 'SCHEDULE_EXPIRED')

  // 4. Force Offline override
  const offlineCfg = { ...cfg, overrideMode: 'FORCE_OFFLINE' }
  const resOffline = evaluateDocsAccess(offlineCfg, null, insideDate)
  assert.equal(resOffline.granted, false)
  assert.equal(resOffline.publicReason, 'FORCE_OFFLINE')

  // 5. Always Public override (even before window)
  const alwaysCfg = { ...cfg, overrideMode: 'ALWAYS_PUBLIC' }
  const resAlways = evaluateDocsAccess(alwaysCfg, null, beforeDate)
  assert.equal(resAlways.granted, true)
  assert.equal(resAlways.publicGranted, true)
  assert.equal(resAlways.publicReason, 'ALWAYS_PUBLIC')

  // 6. Disabled flag
  const disabledCfg = { ...cfg, enabled: false }
  const resDisabled = evaluateDocsAccess(disabledCfg, null, insideDate)
  assert.equal(resDisabled.granted, false)
  assert.equal(resDisabled.publicReason, 'DISABLED')
})

test('admin sessions bypass restrictions with admin preview notice', () => {
  const cfg = getDefaultDocsConfig()
  const beforeDate = new Date('2026-06-01T12:00:00+06:00')
  const adminSession = {
    authenticated: true,
    user: { is_staff: true },
    businesses: [{ id: 1, role: 'OWNER' }],
  }

  const resAdmin = evaluateDocsAccess(cfg, adminSession, beforeDate)
  assert.equal(resAdmin.isAdmin, true)
  assert.equal(resAdmin.granted, true)
  assert.equal(resAdmin.publicGranted, false)
  assert.equal(resAdmin.reason, 'ADMIN_OVERRIDE')
  assert.match(resAdmin.message, /Admin Preview/)
})

test('team members section satisfies mandatory enhancement requirements', () => {
  assert.ok(Array.isArray(TEAM_MEMBERS))
  assert.ok(TEAM_MEMBERS.length >= 4)

  for (const member of TEAM_MEMBERS) {
    assert.ok(member.id, 'Member must have an ID')
    assert.ok(member.name, 'Member must have a full name')
    assert.ok(member.role, 'Member must have a defined role in the application')
    assert.ok(member.email, 'Member must have an email address')
    assert.match(member.email, /^[^\s@]+@[^\s@]+\.[^\s@]+$/, 'Member must have a valid email address')
    assert.ok(member.initials, 'Member must have fallback initials')
    assert.ok(Array.isArray(member.focusAreas), 'Member must have focus areas')
  }
})

test('YC pitch deck sections cover all required subjects', () => {
  const sectionIds = YC_PITCH_SECTIONS.map((s) => s.id)
  const required = [
    'problem',
    'solution',
    'why-now',
    'product-demo',
    'market-opportunity',
    'business-model',
    'traction',
    'competition',
    'unique-advantage',
    'gtm',
    'team',
    'vision',
  ]

  for (const req of required) {
    assert.ok(sectionIds.includes(req), `Pitch deck must include ${req} section`)
  }
})

test('technical sections cover architecture, api, data layer, security and changelog', () => {
  const sectionIds = TECHNICAL_SECTIONS.map((s) => s.id)
  const required = [
    'tech-overview',
    'tech-stack',
    'api-reference',
    'security-data-privacy',
    'roadmap',
    'changelog',
  ]

  for (const req of required) {
    assert.ok(sectionIds.includes(req), `Technical documentation must include ${req} section`)
  }
})

test('markdown exporter generates comprehensive document with all sections', () => {
  const md = generateMarkdownExport(YC_PITCH_SECTIONS, TECHNICAL_SECTIONS, TEAM_MEMBERS, DEFAULT_LIVE_STATS)

  assert.ok(md.includes('# Bizora — Autonomous Enterprise Business Brain'))
  assert.ok(md.includes('## Table of Contents'))
  assert.ok(md.includes('## Part 1: YC-Style Pitch Deck'))
  assert.ok(md.includes('## Part 2: Deep Technical Whitepaper'))
  assert.ok(md.includes('Tanjim Abubokor'))
  assert.ok(md.includes('Ismail Hossen'))
  assert.ok(md.includes('/api/businesses/{id}/shipping/steadfast/send/'))
})

test('all docs components and styles enforce zero raw hex color rules', () => {
  const filesToCheck = [
    'src/styles/docs.css',
    'src/components/docs/DocsTeamSection.js',
    'src/components/docs/DocsDiagrams.js',
    'src/components/docs/DocsPitchDeck.js',
    'src/components/docs/DocsTechnical.js',
    'src/components/docs/DocsLiveSystem.js',
    'src/components/docs/DocsAdminPanel.js',
    'src/components/docs/DocsAccessRestricted.js',
    'src/components/docs/DocsPortal.js',
  ]

  for (const rel of filesToCheck) {
    const full = path.resolve(rel)
    assert.ok(fs.existsSync(full), `File ${rel} must exist`)
    const content = fs.readFileSync(full, 'utf8')
    // Match hex color patterns (#fff, #ffffff, #123456)
    const hexMatches = content.match(/#(?:[0-9a-fA-F]{3}){1,2}\b/g) || []
    assert.equal(
      hexMatches.length,
      0,
      `File ${rel} contains forbidden raw hex colors: ${hexMatches.join(', ')}`,
    )
  }
})
