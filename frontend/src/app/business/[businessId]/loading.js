import React from 'react'
import { Skeleton } from '@/components/ui/Skeleton'

export default function BusinessLoading() {
  return (
    <div className="workspace-loading-skeleton" aria-label="Loading workspace data" aria-busy="true">
      {/* Page Header Skeleton */}
      <div className="skeleton-header-section">
        <div className="skeleton-breadcrumbs">
          <Skeleton width="80px" height="14px" />
          <span className="text-muted">/</span>
          <Skeleton width="120px" height="14px" />
        </div>
        <div className="skeleton-title-row">
          <Skeleton width="240px" height="32px" />
          <div className="skeleton-actions">
            <Skeleton width="100px" height="36px" />
            <Skeleton width="120px" height="36px" />
          </div>
        </div>
        <Skeleton width="340px" height="18px" />
      </div>

      {/* KPI Tiles Skeleton */}
      <div className="skeleton-kpi-grid">
        {[1, 2, 3, 4].map((i) => (
          <div key={i} className="skeleton-kpi-card">
            <Skeleton width="90px" height="14px" />
            <Skeleton width="140px" height="28px" style={{ margin: '8px 0 4px' }} />
            <Skeleton width="110px" height="12px" />
          </div>
        ))}
      </div>

      {/* Filter Bar Skeleton */}
      <div className="skeleton-filter-bar">
        <Skeleton width="260px" height="36px" />
        <Skeleton width="120px" height="36px" />
        <Skeleton width="120px" height="36px" />
      </div>

      {/* Table Skeleton */}
      <div className="skeleton-table-card">
        <div className="skeleton-table-header">
          <Skeleton width="140px" height="16px" />
          <Skeleton width="180px" height="16px" />
          <Skeleton width="100px" height="16px" />
          <Skeleton width="90px" height="16px" />
          <Skeleton width="110px" height="16px" />
        </div>
        {[1, 2, 3, 4, 5, 6].map((row) => (
          <div key={row} className="skeleton-table-row">
            <Skeleton width="30%" height="16px" />
            <Skeleton width="25%" height="16px" />
            <Skeleton width="15%" height="16px" />
            <Skeleton width="10%" height="16px" />
            <Skeleton width="15%" height="16px" />
          </div>
        ))}
        <div className="skeleton-table-footer">
          <Skeleton width="120px" height="14px" />
          <Skeleton width="160px" height="28px" />
        </div>
      </div>
    </div>
  )
}
