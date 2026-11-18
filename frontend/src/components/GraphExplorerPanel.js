'use client'

import React, { useState } from 'react'
import { Tabs } from '@/components/ui'
import GraphPathFinder from './GraphPathFinder'

const EXPLORER_VIEWS = [{ id: 'paths', label: 'Find a path' }]

export default function GraphExplorerPanel({ businessId, timezone }) {
  const [view, setView] = useState('paths')
  return (
    <section className="surface card-padding stack" aria-labelledby="graph-explorer-title">
      <div className="section-header">
        <div>
          <h3 id="graph-explorer-title" className="section-title">
            Explore the graph
          </h3>
          <p className="section-desc">
            Read-only tools for exploring the stored business graph. Nothing here changes the graph.
          </p>
        </div>
      </div>
      <Tabs tabs={EXPLORER_VIEWS} activeTab={view} onChange={setView} ariaLabel="Graph exploration tools" />
      <div role="tabpanel" id={`tabpanel-${view}`} aria-labelledby={`tab-${view}`}>
        {view === 'paths' && <GraphPathFinder businessId={businessId} timezone={timezone} />}
      </div>
    </section>
  )
}
