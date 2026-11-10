'use client'

import { useState } from 'react'
import { Table, BarChart2 } from 'lucide-react'
import { Skeleton } from '../Skeleton.js'
import { EmptyState } from '../EmptyState.js'
import { UnavailableState } from '../UnavailableState.js'
import { Button } from '../Button.js'
import { DataTable } from '../DataTable.js'

export function ChartCard({
  title,
  subtitle,
  badge,
  action,
  loading = false,
  empty = false,
  emptyTitle = 'No data points available',
  emptyDescription = 'There is no metric telemetry for the selected period.',
  unavailable = false,
  unavailableReason,
  tableData,
  tableColumns,
  ariaLabel,
  children,
  className = '',
  ...props
}) {
  const [showTable, setShowTable] = useState(false)
  const canToggleTable = Boolean(tableData && tableData.length > 0 && tableColumns)

  return (
    <div className={`chart-card ${className}`.trim()} {...props}>
      <div className="chart-card-header">
        <div className="chart-card-heading">
          <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-2)' }}>
            <h3 className="chart-card-title">{title}</h3>
            {badge}
          </div>
          {subtitle && <p className="chart-card-subtitle">{subtitle}</p>}
        </div>

        <div className="chart-card-actions">
          {action}
          {canToggleTable && !loading && !empty && !unavailable && (
            <Button
              variant="secondary"
              size="sm"
              onClick={() => setShowTable((prev) => !prev)}
              aria-label={showTable ? `View ${title} as chart` : `View ${title} as accessible data table`}
              title={showTable ? 'Switch to graphical chart view' : 'Switch to tabular data view'}
            >
              {showTable ? (
                <>
                  <BarChart2 size={14} aria-hidden="true" />
                  <span>Chart view</span>
                </>
              ) : (
                <>
                  <Table size={14} aria-hidden="true" />
                  <span>View as table</span>
                </>
              )}
            </Button>
          )}
        </div>
      </div>

      <div
        className="chart-card-body chart-aspect-ratio"
        role="region"
        aria-label={ariaLabel || `${title} visualization`}
      >
        {loading ? (
          <div
            style={{
              height: '100%',
              display: 'flex',
              flexDirection: 'column',
              gap: 'var(--space-3)',
              justifyContent: 'center',
            }}
          >
            <Skeleton variant="rectangular" width="100%" height="80%" />
            <div style={{ display: 'flex', gap: 'var(--space-4)', justifyContent: 'space-between' }}>
              <Skeleton variant="text" width="20%" height={12} />
              <Skeleton variant="text" width="20%" height={12} />
              <Skeleton variant="text" width="20%" height={12} />
              <Skeleton variant="text" width="20%" height={12} />
            </div>
          </div>
        ) : unavailable ? (
          <UnavailableState
            owner="telemetry"
            reason={unavailableReason || 'Telemetry and time-series metrics service is not connected'}
          />
        ) : empty ? (
          <EmptyState title={emptyTitle} description={emptyDescription} />
        ) : showTable && canToggleTable ? (
          <div className="chart-table-view">
            <DataTable
              rows={tableData}
              columns={tableColumns}
              density="compact"
              ariaLabel={`${title} data table`}
            />
          </div>
        ) : (
          children
        )}
      </div>
    </div>
  )
}
