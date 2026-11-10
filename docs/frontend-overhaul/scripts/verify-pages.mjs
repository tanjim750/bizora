#!/usr/bin/env node
// Screenshot and automatic checks for pages of the running frontend. Needs no Chrome: it uses Playwright from frontend/node_modules
// with any headless Chromium it can find (see findBrowser). Signs in through the development-only demo endpoint.
//
//   node docs/frontend-overhaul/scripts/verify-pages.mjs --label phase1 --theme light,dark --sizes 1440x900,390x844 /login /business/{id}/overview
//   node docs/frontend-overhaul/scripts/verify-pages.mjs --label matrix --theme light,dark --matrix /business/{id}/overview
//
// {id} is replaced by the id of the first business of the demo user. Options:
//   --label NAME (folder name in ~/bizora-shots/),
//   --theme light,dark (default light),
//   --sizes WxH,WxH (default 1440x900,390x844),
//   --matrix (expands --sizes to 7 viewports: 360x740, 390x844, 768x1024, 1024x768, 1280x800, 1440x900, 1920x1080),
//   --strict (exit code 1 when any check fails),
//   --no-shots (checks only, skips writing PNG files).
// Environment: BIZORA_FRONTEND (default http://127.0.0.1:3000), BIZORA_SHOTS_DIR (default ~/bizora-shots), BIZORA_BROWSER (path to a browser executable).
// Checks per page and size: raw content (JSON, ISO dates, "Record #id"), HTTP status, console errors and warnings, page errors, failed or 4xx/5xx requests, horizontal overflow, h1 count,
// controls without an accessible name, text contrast (WCAG: 4.5, or 3 for large text), touch targets (<40px on viewports <=480px), min font size (<12px), keyboard focus visibility on the first 15 Tab stops, body font.
import { createRequire } from 'node:module'
import fs from 'node:fs'
import os from 'node:os'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

const here = path.dirname(fileURLToPath(import.meta.url))
const repo = path.resolve(here, '../../..')
const require = createRequire(path.join(repo, 'frontend', 'package.json'))
const { chromium } = require('@playwright/test')

const args = process.argv.slice(2)
const opt = (name, fallback) => {
  const i = args.indexOf(`--${name}`)
  if (i === -1) return fallback
  const v = args[i + 1]
  args.splice(i, 2)
  return v
}
const flag = (name) => {
  const i = args.indexOf(`--${name}`)
  if (i === -1) return false
  args.splice(i, 1)
  return true
}
const label = opt('label', 'run')
const themes = opt('theme', 'light').split(',')
const matrix = flag('matrix')
const MATRIX_SIZES = '360x740,390x844,768x1024,1024x768,1280x800,1440x900,1920x1080'
const sizes = (matrix ? MATRIX_SIZES : opt('sizes', '1440x900,390x844'))
  .split(',')
  .map((s) => s.split('x').map(Number))
const strict = flag('strict')
const noShots = flag('no-shots')
const paths = args.filter((a) => a.startsWith('/'))
if (!paths.length) {
  console.error('Give at least one path, for example /login /business/{id}/overview')
  process.exit(2)
}
const base = (process.env.BIZORA_FRONTEND || 'http://127.0.0.1:3000').replace(/\/$/, '')
const shotsRoot = process.env.BIZORA_SHOTS_DIR || path.join(os.homedir(), 'bizora-shots')
const outDir = path.join(shotsRoot, label)
fs.mkdirSync(outDir, { recursive: true })

function findBrowser() {
  if (process.env.BIZORA_BROWSER) return process.env.BIZORA_BROWSER
  const root = path.join(os.homedir(), '.cache', 'ms-playwright')
  try {
    const dirs = fs
      .readdirSync(root)
      .filter((d) => d.startsWith('chromium_headless_shell-'))
      .sort()
      .reverse()
    for (const d of dirs) {
      const bin = path.join(root, d, 'chrome-headless-shell-linux64', 'chrome-headless-shell')
      if (fs.existsSync(bin)) return bin
    }
  } catch {}
  return undefined
}

async function launch() {
  try {
    return await chromium.launch()
  } catch (first) {
    const exe = findBrowser()
    if (!exe) {
      console.error(
        'No browser found. Set BIZORA_BROWSER to a Chromium executable, or ask the owner to allow: cd frontend && npx playwright install chromium',
      )
      throw first
    }
    return chromium.launch({ executablePath: exe })
  }
}

// Runs inside the page.
function pageChecks() {
  const parse = (c) => {
    const m = c.match(/rgba?\(([^)]+)\)/)
    if (!m) return null
    const p = m[1]
      .split(/[ ,/]+/)
      .filter(Boolean)
      .map(Number)
    return { r: p[0], g: p[1], b: p[2], a: p[3] === undefined ? 1 : p[3] }
  }
  const lum = ({ r, g, b }) => {
    const f = (v) => ((v /= 255) <= 0.03928 ? v / 12.92 : ((v + 0.055) / 1.055) ** 2.4)
    return 0.2126 * f(r) + 0.7152 * f(g) + 0.0722 * f(b)
  }
  const ratio = (a, b) => {
    const [hi, lo] = [lum(a), lum(b)].sort((x, y) => y - x)
    return (hi + 0.05) / (lo + 0.05)
  }
  const bgOf = (el) => {
    for (let e = el; e; e = e.parentElement) {
      const c = parse(getComputedStyle(e).backgroundColor)
      if (c && c.a > 0.9) return c
    }
    return { r: 255, g: 255, b: 255, a: 1 }
  }
  const visible = (el) => {
    const s = getComputedStyle(el)
    const r = el.getBoundingClientRect()
    return (
      s.visibility !== 'hidden' &&
      s.display !== 'none' &&
      Number(s.opacity) > 0 &&
      r.width > 0 &&
      r.height > 0
    )
  }
  const sel = (el) => {
    let s = el.tagName.toLowerCase()
    if (el.id) s += `#${el.id}`
    else if (el.className && typeof el.className === 'string')
      s +=
        '.' +
        el.className
          .trim()
          .split(/\s+/)
          .slice(0, 2)
          .join('.')
    return s
  }

  const contrastFails = []
  const fontFails = []
  const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT)
  const seen = new Set()
  while (walker.nextNode()) {
    const node = walker.currentNode
    const text = node.textContent.trim()
    const el = node.parentElement
    if (
      !text ||
      !el ||
      seen.has(el) ||
      ['SCRIPT', 'STYLE', 'NOSCRIPT'].includes(el.tagName) ||
      !visible(el)
    )
      continue
    seen.add(el)
    const s = getComputedStyle(el)

    // Minimum font size check (<12px).
    // Note: 11px is deliberately permitted by 20-design-system.md ONLY for uppercase overline labels, kbd shortcuts, and badges.
    const size = parseFloat(s.fontSize)
    const isOverlineOrBadge =
      s.textTransform === 'uppercase' ||
      el.tagName === 'KBD' ||
      el.classList.contains('badge') ||
      el.classList.contains('nav-badge') ||
      el.classList.contains('status-chip') ||
      el.closest(
        '.sidebar-context-label, .sidebar-nav-group-title, .auth-context, .page-context, .topbar-role-badge, .nav-badge, .badge, .sidebar-dev-badge, .user-role-tag, kbd',
      )
    if (size < 12 && !isOverlineOrBadge) {
      fontFails.push({ el: sel(el), text: text.slice(0, 30), size })
    }

    const fg = parse(s.color)
    if (!fg) continue
    const bg = bgOf(el)
    const bold = Number(s.fontWeight) >= 700
    const need = size >= 24 || (size >= 18.66 && bold) ? 3 : 4.5
    const got = ratio(fg, bg)
    if (got < need && !el.closest('[disabled], [aria-disabled="true"]')) {
      contrastFails.push({
        el: sel(el),
        text: text.slice(0, 30),
        ratio: Math.round(got * 100) / 100,
        need,
      })
    }
  }

  // Touch target check on mobile viewports (<=480px)
  const targetFails = []
  if (window.innerWidth <= 480) {
    const interactive = document.querySelectorAll(
      'button, a[href], input:not([type=hidden]):not([type=checkbox]):not([type=radio]), select, textarea, [role=button]',
    )
    for (const el of interactive) {
      if (!visible(el)) continue
      // Ignore inline text links inside sentences, breadcrumbs, or prose per WCAG 2.5.8
      if (
        el.tagName === 'A' &&
        (el.classList.contains('text-link') ||
          el.classList.contains('breadcrumb-link') ||
          el.closest('nav[aria-label="Breadcrumb"], .breadcrumbs, p, span, li, dt, dd, td') ||
          getComputedStyle(el).display.includes('inline'))
      ) {
        continue
      }
      const r = el.getBoundingClientRect()
      if (r.height < 40) {
        targetFails.push({
          el: sel(el),
          height: Math.round(r.height),
          text: (el.getAttribute('aria-label') || el.textContent || '').trim().slice(0, 24),
        })
      }
    }
  }

  const name = (el) =>
    (el.getAttribute('aria-label') || '').trim() ||
    (el.getAttribute('aria-labelledby') ? 'x' : '') ||
    (el.labels && el.labels.length ? 'x' : '') ||
    (el.closest('label') ? 'x' : '') ||
    (el.getAttribute('title') || '').trim() ||
    (el.tagName === 'INPUT' && ['submit', 'button'].includes(el.type) && el.value ? 'x' : '') ||
    el.textContent.trim() ||
    (el.querySelector('img[alt]:not([alt=""])') ? 'x' : '')
  const unnamed = [
    ...document.querySelectorAll(
      'button, a[href], input:not([type=hidden]), select, textarea, [role=button]',
    ),
  ]
    .filter((el) => visible(el) && !name(el))
    .map(sel)
  // Content quality: the problems the audit found (raw JSON, raw ISO timestamps, placeholder record titles, "[object Object]").
  const rawContent = []
  for (const pre of document.querySelectorAll('pre')) {
    if (visible(pre) && /^\s*[{[]/.test(pre.textContent))
      rawContent.push(`raw JSON block: ${pre.textContent.trim().slice(0, 40)}`)
  }
  const isoRe = /\b\d{4}-\d{2}-\d{2}T\d{2}:\d{2}(:\d{2})?(\.\d+)?(Z|[+-]\d{2}:?\d{2})?\b/
  const tw = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT)
  while (tw.nextNode()) {
    const el = tw.currentNode.parentElement
    const t = tw.currentNode.textContent.trim()
    if (!t || !el || ['SCRIPT', 'STYLE', 'NOSCRIPT'].includes(el.tagName) || !visible(el)) continue
    if (isoRe.test(t)) rawContent.push(`raw ISO timestamp: ${t.slice(0, 40)}`)
    if (/^Record #\d+$/.test(t)) rawContent.push(`placeholder title: ${t}`)
    if (t.includes('[object Object]')) rawContent.push('[object Object] on screen')
    if (/<\/?untrusted_customer_data>/.test(t))
      rawContent.push('untrusted_customer_data wrapper on screen')
  }
  return {
    rawContentCount: rawContent.length,
    rawContent: rawContent.slice(0, 8),
    overflowX: document.documentElement.scrollWidth > window.innerWidth + 1,
    overflowElements: Array.from(document.querySelectorAll('*'))
      .filter((el) => {
        const r = el.getBoundingClientRect()
        return r.right > window.innerWidth + 1 && el.offsetWidth > 0
      })
      .slice(0, 5)
      .map((el) => `${el.tagName.toLowerCase()}${el.className ? '.' + String(el.className).trim().split(/\s+/).join('.') : ''}${el.id ? '#' + el.id : ''} (r=${Math.round(el.getBoundingClientRect().right)}, w=${Math.round(el.getBoundingClientRect().width)})`),
    scrollWidth: document.documentElement.scrollWidth,
    h1: document.querySelectorAll('h1').length,
    unnamedControls: unnamed.slice(0, 10),
    unnamedCount: unnamed.length,
    contrastFails: contrastFails.slice(0, 12),
    contrastFailCount: contrastFails.length,
    targetFails: targetFails.slice(0, 10),
    targetFailCount: targetFails.length,
    fontFails: fontFails.slice(0, 10),
    fontFailCount: fontFails.length,
    bodyFont: getComputedStyle(document.body).fontFamily.split(',')[0].replaceAll('"', ''),
    theme: document.documentElement.getAttribute('data-theme') || '(system)',
  }
}

async function focusCheck(page) {
  const fails = []
  await page.evaluate(() => document.activeElement && document.activeElement.blur())
  for (let i = 0; i < 15; i++) {
    await page.keyboard.press('Tab')
    const r = await page.evaluate(() => {
      const el = document.activeElement
      if (!el || el === document.body) return null
      if (['NEXTJS-PORTAL', 'NEXT-ROUTE-ANNOUNCER'].includes(el.tagName)) return null // Next.js development overlay, not our UI
      const s = getComputedStyle(el)
      const outline = s.outlineStyle !== 'none' && parseFloat(s.outlineWidth) >= 1
      const shadow = s.boxShadow && s.boxShadow !== 'none'

      // Check composite container (e.g. .input-group:focus-within)
      const group = el.closest('.input-group')
      const gs = group ? getComputedStyle(group) : null
      const groupOutline = gs && gs.outlineStyle !== 'none' && parseFloat(gs.outlineWidth) >= 1
      const groupShadow = gs && gs.boxShadow && gs.boxShadow !== 'none'

      const hasVisibleFocus = outline || shadow || groupOutline || groupShadow
      return {
        el:
          el.tagName.toLowerCase() +
          (el.id ? `#${el.id}` : '') +
          ' "' +
          (el.getAttribute('aria-label') || el.textContent || '').trim().slice(0, 24) +
          '"',
        ok: hasVisibleFocus,
      }
    })
    if (r && !r.ok) fails.push(r.el)
  }
  return fails
}

const browser = await launch()
const rows = []
try {
  for (const theme of themes) {
    const context = await browser.newContext({
      colorScheme: theme === 'dark' ? 'dark' : 'light',
      baseURL: base,
    })
    const login = await context.request.post('/api/demo-login', { headers: { origin: base } })
    let bizId = '1'
    if (login.ok()) {
      const session = await (await context.request.get('/api/backend/frontend/session')).json()
      bizId = String(session.businesses?.[0]?.id ?? 1)
    } else if (paths.some((p) => !p.startsWith('/login'))) {
      console.error(
        `Demo sign-in failed (HTTP ${login.status()}). Start the frontend with dev-frontend.sh so the demo endpoint is enabled. Pages that need a session will redirect to /login.`,
      )
    }
    let anon = null // signed-out context, used for /login so it is not redirected
    for (const [w, h] of sizes) {
      for (const raw of paths) {
        const url = raw.replaceAll('{id}', bizId)
        const useAnon = raw.startsWith('/login')
        if (useAnon && !anon)
          anon = await browser.newContext({
            colorScheme: theme === 'dark' ? 'dark' : 'light',
            baseURL: base,
          })
        const page = await (useAnon ? anon : context).newPage()
        await page.setViewportSize({ width: w, height: h })
        const consoleErrors = []
        const consoleWarnings = []
        const failed = []
        page.on('console', (m) => {
          const t = m.text()
          // Ignore synthetic Playwright artifact (Playwright caret hiding triggers false React hydration warning on inputs)
          if (t.includes('caret-color')) return
          if (m.type() === 'error') consoleErrors.push(t.slice(0, 140))
          if (m.type() === 'warning') consoleWarnings.push(t.slice(0, 140))
        })
        page.on('pageerror', (e) => consoleErrors.push(`pageerror: ${String(e).slice(0, 140)}`))
        page.on('requestfailed', (r) => {
          const why = r.failure()?.errorText ?? ''
          if (!why.includes('ERR_ABORTED'))
            failed.push(`${r.method()} ${new URL(r.url()).pathname} ${why}`) // aborts happen on redirects and prefetches
        })
        page.on('response', (r) => {
          if (r.status() >= 400 && !r.url().endsWith('favicon.ico'))
            failed.push(`${r.status()} ${new URL(r.url()).pathname}`)
        })
        let status = 0
        try {
          const resp = await page.goto(url, { waitUntil: 'networkidle', timeout: 30000 })
          status = resp ? resp.status() : 0
        } catch (e) {
          consoleErrors.push(`navigation: ${String(e).split('\n')[0]}`)
        }
        const checks = await page.evaluate(pageChecks)
        const focusFails = await focusCheck(page)
        const slug = url.replace(/^\//, '').replace(/[^a-zA-Z0-9]+/g, '-') || 'root'
        const file = `${slug}-${w}-${theme}.png`
        if (!noShots) await page.screenshot({ path: path.join(outDir, file), fullPage: true })
        rows.push({
          url,
          size: `${w}x${h}`,
          requestedTheme: theme,
          finalUrl: page.url().replace(base, ''),
          status,
          consoleErrors,
          consoleWarnings,
          failed,
          focusFails,
          file: noShots ? '' : file,
          ...checks,
        })
        await page.close()
      }
    }
    await context.close()
    if (anon) await anon.close()
  }
} finally {
  await browser.close()
}

fs.writeFileSync(path.join(outDir, 'report.json'), JSON.stringify(rows, null, 2))
const pad = (v, n) => String(v).padEnd(n)
console.log(`\nverify-pages: ${rows.length} page checks, shots in ${outDir}\n`)
console.log(
  pad('page', 36),
  pad('size', 10),
  pad('theme', 6),
  pad('http', 5),
  'err warn net ovf h1 name ctr tgt fnt foc raw font',
)
let issues = 0
for (const r of rows) {
  const bad =
    r.consoleErrors.length +
    r.failed.length +
    (r.overflowX ? 1 : 0) +
    (r.h1 !== 1 ? 1 : 0) +
    r.unnamedCount +
    r.contrastFailCount +
    (r.targetFailCount || 0) +
    (r.fontFailCount || 0) +
    r.focusFails.length +
    r.rawContentCount
  issues += bad
  console.log(
    pad(r.url, 36),
    pad(r.size, 10),
    pad(r.requestedTheme, 6),
    pad(r.status, 5),
    pad(r.consoleErrors.length, 3),
    pad(r.consoleWarnings.length, 4),
    pad(r.failed.length, 3),
    pad(r.overflowX ? 'YES' : 'no', 3),
    pad(r.h1, 2),
    pad(r.unnamedCount, 4),
    pad(r.contrastFailCount, 3),
    pad(r.targetFailCount || 0, 3),
    pad(r.fontFailCount || 0, 3),
    pad(r.focusFails.length, 3),
    pad(r.rawContentCount, 3),
    r.bodyFont,
    r.finalUrl !== r.url ? `-> ${r.finalUrl}` : '',
  )
}
console.log(
  '\nColumns: err = console errors/page errors, warn = warnings, net = failed requests, ovf = horizontal overflow, h1 = h1 count, name = unnamed controls, ctr = contrast fails, tgt = touch targets <40px (<=480px), fnt = fonts <12px, foc = invisible focus stops, raw = raw JSON/ISO dates/placeholders.',
)
const details = rows.filter(
  (r) =>
    r.consoleErrors.length ||
    r.failed.length ||
    r.contrastFailCount ||
    r.unnamedCount ||
    r.targetFailCount ||
    r.fontFailCount ||
    r.focusFails.length ||
    r.rawContentCount,
)
for (const r of details.slice(0, 40)) {
  console.log(`\n${r.url} ${r.size} ${r.requestedTheme}`)
  for (const e of r.consoleErrors.slice(0, 3)) console.log('  console:', e)
  for (const e of r.failed.slice(0, 3)) console.log('  request:', e)
  if (r.overflowX && r.overflowElements?.length) {
    console.log('  overflow elements:', r.overflowElements.join(', '))
  }
  for (const c of r.contrastFails.slice(0, 4))
    console.log(`  contrast ${c.ratio} < ${c.need}: ${c.el} "${c.text}"`)
  for (const t of (r.targetFails || []).slice(0, 4))
    console.log(`  target height ${t.height}px < 40px: ${t.el} "${t.text}"`)
  for (const f of (r.fontFails || []).slice(0, 4))
    console.log(`  font size ${f.size}px < 12px: ${f.el} "${f.text}"`)
  for (const e of r.unnamedControls.slice(0, 3)) console.log('  no accessible name:', e)
  for (const e of r.focusFails.slice(0, 3)) console.log('  focus not visible:', e)
  for (const e of r.rawContent.slice(0, 4)) console.log('  content:', e)
}
console.log(`\nTOTAL ISSUES: ${issues}${strict && issues ? ' (strict: exiting 1)' : ''}`)
process.exit(strict && issues ? 1 : 0)
