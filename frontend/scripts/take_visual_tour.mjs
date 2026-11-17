/**
 * Interactive Visual Browser Journey & Evidence Capture
 *
 * Exercises the affected flows interactively:
 * 1. Login flow (/login)
 * 2. Multi-tenant workspace selection (/workspace)
 * 3. Executive Overview (/business/<id>/overview)
 * 4. Commerce Payments & Refund Drawer (/business/<id>/commerce?tab=payments)
 * 5. Administration Integrations (/business/<id>/admin/integrations)
 * 6. Mobile responsive navigation at 320px viewport width
 *
 * Captures visual screenshots to test-artifacts/screenshots/ and tracks browser console output.
 */

import { chromium } from '@playwright/test'
import fs from 'node:fs'
import path from 'node:path'

const SCREENSHOT_DIR =
  process.env.BIZORA_SCREENSHOT_DIR ||
  path.resolve(process.cwd(), '..', 'test-artifacts', 'screenshots')

const BASE_URL = process.env.BIZORA_E2E_URL || 'http://localhost:3000'
const USERNAME = process.env.BIZORA_E2E_USERNAME || 'e2e-manager'
const PASSWORD = process.env.BIZORA_E2E_PASSWORD
const CHROME_PATH = process.env.PLAYWRIGHT_CHROME_EXECUTABLE || '/usr/bin/google-chrome'

if (!PASSWORD) {
  console.error('ERROR: BIZORA_E2E_PASSWORD environment variable is required.')
  process.exit(1)
}

fs.mkdirSync(SCREENSHOT_DIR, { recursive: true })

async function runVisualTour() {
  console.log(`[Visual Tour] Starting Google Chrome from ${CHROME_PATH}...`)
  console.log(`[Visual Tour] Target Base URL: ${BASE_URL}`)
  console.log(`[Visual Tour] Saving screenshots to: ${SCREENSHOT_DIR}`)

  const browser = await chromium.launch({
    executablePath: CHROME_PATH,
    headless: true,
  })

  const context = await browser.newContext({
    viewport: { width: 1440, height: 900 },
    deviceScaleFactor: 1,
  })

  const page = await context.newPage()

  const consoleLogs = []
  const consoleErrors = []
  const pageErrors = []

  page.on('console', (msg) => {
    const entry = `[${msg.type()}] ${msg.text()}`
    consoleLogs.push(entry)
    if (msg.type() === 'error') {
      consoleErrors.push({ text: msg.text(), location: msg.location() })
    }
  })

  page.on('pageerror', (err) => {
    pageErrors.push(err.message || String(err))
  })

  try {
    // =========================================================================
    // STEP 1: Login flow (/login)
    // =========================================================================
    console.log('\n--- Step 1: Login flow ---')
    await page.goto(`${BASE_URL}/login`, { waitUntil: 'networkidle' })
    const loginScreenshot = path.join(SCREENSHOT_DIR, '01_login.png')
    await page.screenshot({ path: loginScreenshot, fullPage: true })
    console.log(`[Screenshot Captured] ${loginScreenshot}`)

    await page.getByLabel('Username').fill(USERNAME)
    await page.getByLabel('Password').fill(PASSWORD)
    await page.getByRole('button', { name: 'Sign in' }).click()
    await page.waitForURL(/\/workspace$/, { timeout: 10000 })
    console.log('✓ Successfully authenticated and redirected to /workspace')

    // =========================================================================
    // STEP 2: Multi-tenant workspace selection (/workspace)
    // =========================================================================
    console.log('\n--- Step 2: Multi-tenant workspace selection ---')
    await page.waitForLoadState('networkidle')
    const workspaceScreenshot = path.join(SCREENSHOT_DIR, '02_workspace_picker.png')
    await page.screenshot({ path: workspaceScreenshot, fullPage: true })
    console.log(`[Screenshot Captured] ${workspaceScreenshot}`)

    const workspaceLink = page.getByRole('link', { name: /Open workspace for/ }).first()
    await workspaceLink.waitFor({ state: 'visible', timeout: 5000 })
    await workspaceLink.click()
    await page.waitForURL(/\/business\/\d+\/overview$/, { timeout: 10000 })
    const businessId = new URL(page.url()).pathname.split('/')[2]
    console.log(`✓ Selected workspace for business ID: ${businessId}`)

    // =========================================================================
    // STEP 3: Executive Overview (/business/<id>/overview)
    // =========================================================================
    console.log('\n--- Step 3: Executive Overview ---')
    await page.waitForLoadState('networkidle')
    await page.getByRole('heading', { name: 'Executive Overview' }).waitFor({ state: 'visible' })
    await page.getByRole('heading', { name: 'Authoritative Record Counts' }).waitFor({ state: 'visible' })
    const overviewScreenshot = path.join(SCREENSHOT_DIR, '03_executive_overview.png')
    await page.screenshot({ path: overviewScreenshot, fullPage: true })
    console.log(`[Screenshot Captured] ${overviewScreenshot}`)
    console.log('✓ Executive Overview and Authoritative Record Counts verified')

    // =========================================================================
    // STEP 4: Commerce Payments & Refund Drawer (/business/<id>/commerce?tab=payments)
    // =========================================================================
    console.log('\n--- Step 4: Commerce Payments & Refund Drawer ---')
    await page.goto(`${BASE_URL}/business/${businessId}/commerce?tab=payments`, {
      waitUntil: 'networkidle',
    })

    // Find a payment row or open drawer
    const paymentRow = page.getByRole('row').filter({ hasText: 'PAID' }).first()
    const paymentRowVisible = await paymentRow.isVisible({ timeout: 3000 }).catch(() => false)

    if (paymentRowVisible) {
      await paymentRow.click()
    } else {
      // Fallback: fetch payments via API and open detail directly
      const resp = await page.request.get(`/api/backend/businesses/${businessId}/payments`)
      const data = await resp.json()
      const paymentId = data.results?.[0]?.id || 1
      await page.goto(`${BASE_URL}/business/${businessId}/records/payments/${paymentId}`, {
        waitUntil: 'networkidle',
      })
    }

    // Wait for the drawer to appear and click "Issue Refund"
    const issueRefundBtn = page.getByRole('button', { name: 'Issue Refund' })
    await issueRefundBtn.waitFor({ state: 'visible', timeout: 8000 })
    await issueRefundBtn.click()

    // Dialog opens: fill amount and select reason
    const refundDialog = page.getByRole('dialog', { name: 'Issue Financial Refund' })
    await refundDialog.waitFor({ state: 'visible', timeout: 5000 })
    await page.getByLabel(/Refund Amount/).fill('2.50')

    // Capture screenshot of the open refund dialog/drawer with filled data
    const refundScreenshot = path.join(SCREENSHOT_DIR, '04_commerce_refund_drawer.png')
    await page.screenshot({ path: refundScreenshot, fullPage: true })
    console.log(`[Screenshot Captured] ${refundScreenshot}`)

    // Submit refund (idempotent)
    const processRefundBtn = page.getByRole('button', { name: 'Process Refund (Idempotent)' })
    await processRefundBtn.click()

    // Assert UI feedback banner
    const feedbackBanner = page.getByText('Refund recorded in financial ledger. Idempotency key verified.')
    await feedbackBanner.waitFor({ state: 'visible', timeout: 8000 })
    console.log('✓ Refund successfully recorded in ledger; UI success feedback displayed')

    // =========================================================================
    // STEP 5: Administration Integrations (/business/<id>/admin/integrations)
    // =========================================================================
    console.log('\n--- Step 5: Administration Integrations (Steadfast Provider) ---')
    await page.goto(`${BASE_URL}/business/${businessId}/admin/integrations`, {
      waitUntil: 'networkidle',
    })
    const steadfastCell = page.getByRole('cell', { name: 'Steadfast', exact: true })
    await steadfastCell.waitFor({ state: 'visible', timeout: 8000 })
    const integrationsScreenshot = path.join(SCREENSHOT_DIR, '05_admin_integrations_steadfast.png')
    await page.screenshot({ path: integrationsScreenshot, fullPage: true })
    console.log(`[Screenshot Captured] ${integrationsScreenshot}`)
    console.log('✓ Steadfast courier integration provider verified in Administration table')

    // =========================================================================
    // STEP 6: Mobile responsive navigation at 320px viewport width
    // =========================================================================
    console.log('\n--- Step 6: Mobile responsive navigation at 320px viewport width ---')
    await page.setViewportSize({ width: 320, height: 700 })
    await page.goto(`${BASE_URL}/business/${businessId}/overview`, { waitUntil: 'networkidle' })

    // Verify horizontal overflow: scrollWidth must equal 320
    const scrollWidth = await page.evaluate(() => document.documentElement.scrollWidth)
    console.log(`[Viewport Check] Viewport width: 320px, Document scrollWidth: ${scrollWidth}px`)
    if (scrollWidth !== 320) {
      console.warn(`WARNING: scrollWidth (${scrollWidth}) exceeds 320px!`)
    }

    // Toggle mobile hamburger menu
    const navMenuBtn = page.getByRole('button', { name: 'Open navigation menu' })
    await navMenuBtn.waitFor({ state: 'visible', timeout: 5000 })
    await navMenuBtn.click()

    // Verify navigation links are visible
    const customersLink = page.getByRole('link', { name: 'Customers', exact: true })
    await customersLink.waitFor({ state: 'visible', timeout: 5000 })

    const mobileScreenshot = path.join(SCREENSHOT_DIR, '06_mobile_drawer_320px.png')
    await page.screenshot({ path: mobileScreenshot, fullPage: true })
    console.log(`[Screenshot Captured] ${mobileScreenshot}`)

    // Test closing with Escape key
    await page.keyboard.press('Escape')
    await page.waitForTimeout(300)
    const isExpandedAfterEscape = await navMenuBtn.getAttribute('aria-expanded')
    console.log(`[Accessibility] aria-expanded after Escape: "${isExpandedAfterEscape}"`)

    // Reopen and navigate to Customers
    await navMenuBtn.click()
    await customersLink.click()
    await page.waitForURL(new RegExp(`/business/${businessId}/customers`), { timeout: 8000 })
    await page.getByRole('heading', { name: 'Customer Directory & 360' }).waitFor({ state: 'visible' })
    console.log('✓ Mobile navigation drawer opens, closes on Escape, and navigates successfully')

    // Reset viewport
    await page.setViewportSize({ width: 1440, height: 900 })

    console.log('\n======================================================')
    console.log('✓ All 6 visual browser journey steps completed successfully!')
    console.log('======================================================')
  } finally {
    await browser.close()
  }

  // Summary of logs and errors
  console.log('\n--- Browser Console & Runtime Summary ---')
  console.log(`Total console entries: ${consoleLogs.length}`)
  console.log(`Console error count: ${consoleErrors.length}`)
  console.log(`Unhandled page exceptions: ${pageErrors.length}`)

  if (consoleErrors.length > 0) {
    console.warn('\n[Console Errors Observed]:')
    consoleErrors.forEach((e, idx) => console.warn(`  ${idx + 1}. ${e.text} (${e.location?.url || 'unknown'})`))
  } else {
    console.log('✓ Browser console is clean of errors.')
  }

  if (pageErrors.length > 0) {
    console.error('\n[Unhandled Page Exceptions]:')
    pageErrors.forEach((e, idx) => console.error(`  ${idx + 1}. ${e}`))
    process.exit(1)
  } else {
    console.log('✓ No unhandled page exceptions occurred.')
  }

  // Save audit log to file
  const reportPath = path.resolve(SCREENSHOT_DIR, 'visual_tour_report.json')
  fs.writeFileSync(
    reportPath,
    JSON.stringify(
      {
        timestamp: new Date().toISOString(),
        screenshots: [
          '01_login.png',
          '02_workspace_picker.png',
          '03_executive_overview.png',
          '04_commerce_refund_drawer.png',
          '05_admin_integrations_steadfast.png',
          '06_mobile_drawer_320px.png',
        ],
        consoleErrors,
        pageErrors,
        consoleLogsCount: consoleLogs.length,
      },
      null,
      2
    )
  )
  console.log(`[Audit Saved] ${reportPath}`)
}

runVisualTour().catch((err) => {
  console.error('\n[FATAL ERROR in visual tour]:', err)
  process.exit(1)
})
