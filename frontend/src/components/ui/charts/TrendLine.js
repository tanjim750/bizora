'use client'

import { useState, useEffect } from 'react'
import {
  ResponsiveContainer,
  AreaChart,
  Area,
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
} from 'recharts'

function CustomChartTooltip({ active, payload, label, valueFormatter }) {
  if (!active || !payload || !payload.length) return null

  return (
    <div className="chart-tooltip">
      <div className="chart-tooltip-label">{label}</div>
      {payload.map((item, idx) => {
        const val = valueFormatter ? valueFormatter(item.value) : item.value
        return (
          <div key={`tip-${idx}`} className="chart-tooltip-item">
            <span className="chart-tooltip-key">
              <span
                className="chart-tooltip-indicator"
                style={{ backgroundColor: item.color || item.stroke || 'var(--chart-1)' }}
              />
              {item.name || item.dataKey}:
            </span>
            <span className="chart-tooltip-value">{val}</span>
          </div>
        )
      })}
    </div>
  )
}

export function TrendLine({
  data = [],
  xKey = 'date',
  yKey = 'value',
  series,
  variant = 'area', // 'area' | 'line'
  height = '100%',
  valueFormatter,
  showGrid = true,
  showLegend = false,
  showTooltip = true,
  ariaLabel,
  className = '',
}) {
  const [mounted, setMounted] = useState(false)
  const [isMobile, setIsMobile] = useState(false)

  useEffect(() => {
    setMounted(true)
    const checkMobile = () => setIsMobile(window.innerWidth <= 640)
    checkMobile()
    window.addEventListener('resize', checkMobile)
    return () => window.removeEventListener('resize', checkMobile)
  }, [])

  if (!mounted) {
    return (
      <div
        className={`chart-aspect-ratio ${className}`.trim()}
        style={{ height, display: 'flex', alignItems: 'center', justifyContent: 'center' }}
      >
        <span className="sr-only">Loading visualization...</span>
      </div>
    )
  }

  const seriesList = series || [
    {
      key: yKey,
      name: 'Value',
      color: 'var(--chart-1)',
    },
  ]

  const ChartComponent = variant === 'line' ? LineChart : AreaChart

  return (
    <div
      role="img"
      aria-label={
        ariaLabel ||
        `Time series chart showing ${seriesList.map((s) => s.name || s.key).join(', ')} across ${data.length} periods`
      }
      style={{ width: '100%', height }}
      className={className}
    >
      <ResponsiveContainer width="100%" height="100%">
        <ChartComponent data={data} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
          <defs>
            {seriesList.map((s, idx) => {
              const color = s.color || `var(--chart-${(idx % 8) + 1})`
              const gradientId = `trend-gradient-${s.key}-${idx}`
              return (
                <linearGradient key={gradientId} id={gradientId} x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor={color} stopOpacity={0.25} />
                  <stop offset="95%" stopColor={color} stopOpacity={0.0} />
                </linearGradient>
              )
            })}
          </defs>

          {showGrid && (
            <CartesianGrid strokeDasharray="3 3" stroke="var(--color-border-subtle)" vertical={false} />
          )}

          <XAxis
            dataKey={xKey}
            stroke="var(--color-border)"
            tickLine={false}
            tick={{
              fill: 'var(--color-text-muted)',
              fontSize: 12,
              fontFamily: 'var(--font-mono)',
            }}
            interval={isMobile ? 'preserveStartEnd' : 'equidistantPreserveStart'}
            minTickGap={isMobile ? 32 : 16}
          />

          <YAxis
            stroke="var(--color-border)"
            tickLine={false}
            axisLine={false}
            tickCount={isMobile ? 4 : 5}
            tick={{
              fill: 'var(--color-text-muted)',
              fontSize: 12,
              fontFamily: 'var(--font-mono)',
            }}
            tickFormatter={valueFormatter}
          />

          {showTooltip && (
            <Tooltip
              content={<CustomChartTooltip valueFormatter={valueFormatter} />}
              cursor={{ stroke: 'var(--color-border)', strokeWidth: 1 }}
            />
          )}

          {showLegend && (
            <Legend
              wrapperStyle={{
                paddingTop: 12,
                fontSize: 12,
                fontFamily: 'var(--font-body)',
                color: 'var(--color-text-secondary)',
              }}
            />
          )}

          {seriesList.map((s, idx) => {
            const color = s.color || `var(--chart-${(idx % 8) + 1})`
            const gradientId = `trend-gradient-${s.key}-${idx}`

            if (variant === 'line') {
              return (
                <Line
                  key={s.key}
                  type="monotone"
                  dataKey={s.key}
                  name={s.name || s.key}
                  stroke={color}
                  strokeWidth={2}
                  dot={false}
                  activeDot={{ r: 4, stroke: 'var(--color-surface)', strokeWidth: 2 }}
                />
              )
            }

            return (
              <Area
                key={s.key}
                type="monotone"
                dataKey={s.key}
                name={s.name || s.key}
                stroke={color}
                strokeWidth={2}
                fillOpacity={1}
                fill={`url(#${gradientId})`}
                dot={false}
                activeDot={{ r: 4, stroke: 'var(--color-surface)', strokeWidth: 2 }}
              />
            )
          })}
        </ChartComponent>
      </ResponsiveContainer>
    </div>
  )
}
