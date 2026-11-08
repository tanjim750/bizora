import Link from 'next/link'
import { DataTable, StatusBadge } from './DataTable'
import { businessPath, MANAGER_ROLES } from '@/lib/catalog'

export default function Overview({ business, data, queueCount }) {
  const counts = data?.canonical_counts || {}
  return (
    <>
      <div className="page-heading">
        <div>
          <p className="page-context">Business overview</p>
          <h1>Overview</h1>
          <p>Stored activity for {business.name}. Counts are all time unless stated otherwise.</p>
        </div>
        <span className="count-chip">
          {business.currency} · {business.timezone}
        </span>
      </div>
      <div className="metric-grid">
        <section className="metric-card">
          <h2>Revenue</h2>
          <strong>—</strong>
          <p>
            <StatusBadge text="Unavailable" /> Analytics source not mounted
          </p>
        </section>
        <section className="metric-card">
          <h2>Orders</h2>
          <strong>{counts.orders ?? '—'}</strong>
          <p>Canonical records · all time</p>
        </section>
        <section className="metric-card">
          <h2>Customers</h2>
          <strong>{counts.customers ?? '—'}</strong>
          <p>Canonical records · all time</p>
        </section>
        <section className="metric-card">
          <h2>Open cases</h2>
          <strong>{queueCount ?? '—'}</strong>
          <p>Open or pending conversations</p>
        </section>
      </div>
      <div className="overview-columns">
        <section className="surface">
          <div className="section-header">
            <div>
              <h2>Analytics</h2>
              <p>Revenue and trend data</p>
            </div>
            <StatusBadge text="Not mounted" />
          </div>
          <div className="empty-state">
            <strong>Analytics unavailable</strong>
            <p>
              The separate Overview &amp; Monitoring API is not mounted. No revenue or trend is inferred from
              raw orders.
            </p>
          </div>
        </section>
        <section className="surface">
          <div className="section-header">
            <div>
              <h2>Operations snapshot</h2>
              <p>Canonical record counts</p>
            </div>
          </div>
          <dl className="snapshot-list">
            {[
              ['Conversations', counts.conversations],
              ['Shipments', counts.shipments],
              ['Calls', counts.calls],
              ['Campaigns', counts.campaigns],
            ].map(([name, count]) => (
              <div key={name}>
                <dt>{name}</dt>
                <dd>{count ?? '—'}</dd>
              </div>
            ))}
          </dl>
          <Link className="text-link" href={businessPath(business.id, 'queue')}>
            Open support queue →
          </Link>
        </section>
      </div>
      <section className="surface">
        <div className="section-header">
          <div>
            <h2>Recent activity</h2>
            <p>Stored audit events, newest first</p>
          </div>
        </div>
        <DataTable rows={data?.recent_activity?.results || []} businessId={business.id} resource="audits" />
      </section>
      <section className="advisory">
        <StatusBadge text="AI suggestion" />
        <div>
          <h2>Advice requires human review</h2>
          <p>
            Suggestions do not establish business facts or execute provider actions. Review evidence before
            approving any proposal.
          </p>
        </div>
        {MANAGER_ROLES.has(business.role) && (
          <Link className="button button-secondary" href={businessPath(business.id, 'actions')}>
            View proposals
          </Link>
        )}
      </section>
    </>
  )
}
