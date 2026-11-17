'use client'

import { useState, useEffect, useId } from 'react'
import { ResponsiveContainer, AreaChart, Area, LineChart, Line } from 'recharts'

export function Sparkline({
  data = [],
  dataKey = 'value',
  color = 'var(--chart-1)',
  variant = 'area', // 'area' | 'line'
  height = 40,
  ariaLabel,
  className = '',
}) {
  const [mounted, setMounted] = useState(false)

  useEffect(() => {
    setMounted(true)
  }, [])

  if (!mounted || !data || data.length === 0) {
    return (
      <div
        className={`chart-sparkline-wrap ${className}`.trim()}
        style={{ height, opacity: 0.3 }}
        aria-hidden="true"
      />
    )
  }

  // Normalize data if passed as array of numbers
  const chartData = typeof data[0] === 'number' ? data.map((v, i) => ({ id: i, value: v })) : data

  const reactId = useId()
  const key = typeof data[0] === 'number' ? 'value' : dataKey
  const gradientId = `sparkline-grad-${reactId.replace(/:/g, '')}`
  const ChartComponent = variant === 'line' ? LineChart : AreaChart

  return (
    <div
      role="img"
      aria-label={ariaLabel || `Sparkline trend chart with ${chartData.length} data points`}
      className={`chart-sparkline-wrap ${className}`.trim()}
      style={{ height }}
    >
      <ResponsiveContainer width="100%" height="100%">
        <ChartComponent data={chartData} margin={{ top: 2, right: 2, left: 2, bottom: 2 }}>
          {variant === 'area' && (
            <defs>
              <linearGradient id={gradientId} x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor={color} stopOpacity={0.3} />
                <stop offset="100%" stopColor={color} stopOpacity={0.0} />
              </linearGradient>
            </defs>
          )}

          {variant === 'line' ? (
            <Line
              type="monotone"
              dataKey={key}
              stroke={color}
              strokeWidth={1.5}
              dot={false}
              isAnimationActive={false}
            />
          ) : (
            <Area
              type="monotone"
              dataKey={key}
              stroke={color}
              strokeWidth={1.5}
              fillOpacity={1}
              fill={`url(#${gradientId})`}
              dot={false}
              isAnimationActive={false}
            />
          )}
        </ChartComponent>
      </ResponsiveContainer>
    </div>
  )
}
