import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'

const read = (rel) => readFileSync(new URL(rel, import.meta.url), 'utf8')

test('chart components use only CSS variables and zero hard-coded hex colors', () => {
  const chartCard = read('../src/components/ui/charts/ChartCard.js')
  const trendLine = read('../src/components/ui/charts/TrendLine.js')
  const barCompare = read('../src/components/ui/charts/BarCompare.js')
  const sparkline = read('../src/components/ui/charts/Sparkline.js')

  // Hex color regex (#fff, #123456, etc.)
  const hexRe = /#[0-9a-fA-F]{3,8}\b/
  assert.equal(hexRe.test(chartCard), false, 'ChartCard has hardcoded hex')
  assert.equal(hexRe.test(trendLine), false, 'TrendLine has hardcoded hex')
  assert.equal(hexRe.test(barCompare), false, 'BarCompare has hardcoded hex')
  assert.equal(hexRe.test(sparkline), false, 'Sparkline has hardcoded hex')

  // Verify chart tokens usage
  assert.match(trendLine, /var\(--chart-/)
  assert.match(barCompare, /var\(--chart-/)
  assert.match(sparkline, /var\(--chart-/)
})

test('ChartCard provides accessible table toggle and proper empty/unavailable states', () => {
  const chartCard = read('../src/components/ui/charts/ChartCard.js')
  assert.match(chartCard, /role="region"/)
  assert.match(chartCard, /View as table/)
  assert.match(chartCard, /DataTable/)
  assert.match(chartCard, /UnavailableState/)
  assert.match(chartCard, /EmptyState/)
  assert.match(chartCard, /Skeleton/)
})

test('TrendLine and BarCompare support responsive ticks and accessible role="img"', () => {
  const trendLine = read('../src/components/ui/charts/TrendLine.js')
  const barCompare = read('../src/components/ui/charts/BarCompare.js')

  assert.match(trendLine, /role="img"/)
  assert.match(trendLine, /font-mono/)
  assert.match(trendLine, /isMobile \? 4 : 5/)

  assert.match(barCompare, /role="img"/)
  assert.match(barCompare, /font-mono/)
  assert.match(barCompare, /radius=/)
})

test('chart barrel index exports all required components and aliases', () => {
  const chartIndex = read('../src/components/ui/charts/index.js')
  assert.match(chartIndex, /export \{ ChartCard \}/)
  assert.match(chartIndex, /export \{ TrendLine \}/)
  assert.match(chartIndex, /export \{ BarCompare \}/)
  assert.match(chartIndex, /export \{ Sparkline \}/)
  assert.match(chartIndex, /export \{ TrendLine as AreaChart \}/)
  assert.match(chartIndex, /export \{ TrendLine as LineChart \}/)
  assert.match(chartIndex, /export \{ BarCompare as BarChart \}/)

  const uiIndex = read('../src/components/ui/index.js')
  assert.match(uiIndex, /ChartCard/)
  assert.match(uiIndex, /TrendLine/)
  assert.match(uiIndex, /BarCompare/)
  assert.match(uiIndex, /Sparkline/)
  assert.match(uiIndex, /AreaChart/)
  assert.match(uiIndex, /LineChart/)
  assert.match(uiIndex, /BarChart/)
})
