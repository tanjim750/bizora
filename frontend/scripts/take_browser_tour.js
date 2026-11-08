import { chromium } from '@playwright/test'
import path from 'path'

const SCREENSHOT_DIR = process.env.BIZORA_SCREENSHOT_DIR || path.join(process.cwd(), 'screenshots')

async function run() {
  console.log('Starting Playwright web test tour...')
  const browser = await chromium.launch({
    executablePath: '/usr/bin/google-chrome',
    headless: true,
  })

  const context = await browser.newContext({
    viewport: { width: 1366, height: 850 },
    deviceScaleFactor: 1,
  })

  const page = await context.newPage()

  // 1. Login Page
  console.log('Navigating to Login page...')
  await page.goto('http://localhost:3000/login')
  await page.waitForLoadState('networkidle')
  await page.screenshot({ path: path.join(SCREENSHOT_DIR, '01_login.png'), fullPage: true })

  // Sign in
  console.log('Signing in...')
  await page.getByLabel('Username').fill('demo-owner')
  await page.getByLabel('Password').fill('DemoPass123!')
  await page.getByRole('button', { name: 'Sign in' }).click()

  // 2. Workspace Page
  console.log('Verifying Workspace page...')
  await page.waitForURL(/\/workspace/)
  await page.waitForLoadState('networkidle')
  await page.screenshot({ path: path.join(SCREENSHOT_DIR, '02_workspace.png'), fullPage: true })

  // Select Business
  console.log('Navigating to Business Overview...')
  await page.locator('.workspace-card').first().click()
  await page.waitForURL(/\/business\/1\/overview/)
  await page.waitForLoadState('networkidle')
  await page.screenshot({ path: path.join(SCREENSHOT_DIR, '03_overview.png'), fullPage: true })

  // 3. Customers
  console.log('Navigating to Customers...')
  await page.goto('http://localhost:3000/business/1/customers')
  await page.waitForLoadState('networkidle')
  await page.screenshot({ path: path.join(SCREENSHOT_DIR, '04_customers.png'), fullPage: true })

  // 4. Products
  console.log('Navigating to Products...')
  await page.goto('http://localhost:3000/business/1/products')
  await page.waitForLoadState('networkidle')
  await page.screenshot({ path: path.join(SCREENSHOT_DIR, '05_products.png'), fullPage: true })

  // 5. Orders
  console.log('Navigating to Orders...')
  await page.goto('http://localhost:3000/business/1/orders')
  await page.waitForLoadState('networkidle')
  await page.screenshot({ path: path.join(SCREENSHOT_DIR, '06_orders.png'), fullPage: true })

  // 6. Business Insights
  console.log('Navigating to Insights...')
  await page.goto('http://localhost:3000/business/1/insights')
  await page.waitForLoadState('networkidle')
  await page.screenshot({ path: path.join(SCREENSHOT_DIR, '07_insights.png'), fullPage: true })

  // 7. Identity Review
  console.log('Navigating to Identity Review...')
  await page.goto('http://localhost:3000/business/1/identity')
  await page.waitForLoadState('networkidle')
  await page.screenshot({ path: path.join(SCREENSHOT_DIR, '08_identity.png'), fullPage: true })

  // 8. AI Assistant
  console.log('Navigating to AI Assistant...')
  await page.goto('http://localhost:3000/business/1/assistant')
  await page.waitForLoadState('networkidle')
  await page.screenshot({ path: path.join(SCREENSHOT_DIR, '09_assistant.png'), fullPage: true })

  // 9. Configuration
  console.log('Navigating to Configuration...')
  await page.goto('http://localhost:3000/business/1/configuration')
  await page.waitForLoadState('networkidle')
  await page.screenshot({ path: path.join(SCREENSHOT_DIR, '10_configuration.png'), fullPage: true })

  // 10. Observability
  console.log('Navigating to Observability...')
  await page.goto('http://localhost:3000/business/1/observability')
  await page.waitForLoadState('networkidle')
  await page.screenshot({ path: path.join(SCREENSHOT_DIR, '11_observability.png'), fullPage: true })

  // 11. Django Operational SSR UI
  console.log('Navigating to Django Operations UI...')
  const opsPage = await context.newPage()
  await opsPage.goto('http://127.0.0.1:8000/ops/business/1/overview/')
  await opsPage.waitForLoadState('networkidle')
  await opsPage.screenshot({ path: path.join(SCREENSHOT_DIR, '12_django_ops.png'), fullPage: true })

  await browser.close()
  console.log('All screenshots captured successfully.')
}

run().catch((err) => {
  console.error('Browser tour failed:', err)
  process.exit(1)
})
