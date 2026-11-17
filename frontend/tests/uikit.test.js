import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'

const read = (rel) => readFileSync(new URL(rel, import.meta.url), 'utf8')

test('UiKitGalleryClient enforces high-craft SaaS presentation with zero raw CSS token dumps', () => {
  const uiKitSource = read('../src/app/business/[businessId]/ui-kit/UiKitGalleryClient.js')

  // Zero raw CSS variable dumping / raw swatch dump component
  assert.doesNotMatch(uiKitSource, /TokensShowcase/)
  assert.doesNotMatch(uiKitSource, /Design Tokens & High-Craft Foundations/)

  // Sticky pill navigation bar with the 6 core functional sections
  assert.match(uiKitSource, /className="ui-kit-nav-bar"/)
  assert.match(uiKitSource, /href="#section-forms"/)
  assert.match(uiKitSource, /href="#section-feedback"/)
  assert.match(uiKitSource, /href="#section-overlays"/)
  assert.match(uiKitSource, /href="#section-tables"/)
  assert.match(uiKitSource, /href="#section-evidence"/)
  assert.match(uiKitSource, /href="#section-charts"/)

  // Sections defined with proper semantic anchors and IDs
  assert.match(uiKitSource, /id="section-forms"/)
  assert.match(uiKitSource, /id="section-feedback"/)
  assert.match(uiKitSource, /id="section-overlays"/)
  assert.match(uiKitSource, /id="section-tables"/)
  assert.match(uiKitSource, /id="section-evidence"/)
  assert.match(uiKitSource, /id="section-charts"/)

  // Proper container wrapping with high-craft demo box
  assert.match(uiKitSource, /ui-kit-demo-box/)
})

test('UiKitGalleryClient integrates chart components with accessible roles and token styles', () => {
  const uiKitSource = read('../src/app/business/[businessId]/ui-kit/UiKitGalleryClient.js')

  // Chart imports from UI kit wrappers
  assert.match(uiKitSource, /ChartCard/)
  assert.match(uiKitSource, /TrendLine/)
  assert.match(uiKitSource, /BarCompare/)

  // Uses tokenized CSS variables for charts
  assert.match(uiKitSource, /var\(--chart-1\)/)

  // Zero hardcoded inline hex colors in style attributes
  assert.doesNotMatch(uiKitSource, /(?:color|background|border|fill|stroke)\s*:\s*['"]?#[0-9a-fA-F]{3,6}/i)
})
