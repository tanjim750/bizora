'use client'

import {
  Banner,
  CopyableCode,
  DataTable,
  EmptyState,
  KpiTile,
  SimulatedBadge,
  StatusChip,
} from '@/components/ui'
import {
  SERVER_ONLY_NOTICE,
  SIMULATION_COMMANDS,
  COMMAND_EFFECTS,
  COMMAND_FLAGS_NOTE,
  simulatedConnections,
  sandboxSummary,
} from '@/lib/simulation/sandbox'

export default function SimulationSandbox({ connections = [], title = 'Prototype Simulation & Sandbox' }) {
  const summary = sandboxSummary(connections)
  const rows = simulatedConnections(connections)

  const columns = [
    {
      key: 'name',
      label: 'Connection',
      render: (row) => (
        <div>
          <strong>{row.name || row.provider || 'Unnamed connection'}</strong> <SimulatedBadge size="sm" />
        </div>
      ),
    },
    {
      key: 'provider',
      label: 'Provider',
      render: (row) => row.provider || '—',
    },
    {
      key: 'lifecycle',
      label: 'Lifecycle',
      render: (row) => <StatusChip size="sm" status={row.lifecycle_status} />,
    },
    {
      key: 'health',
      label: 'Health',
      render: (row) => (
        <div>
          <StatusChip size="sm" status={row.health_status || 'UNKNOWN'} />
          {row.health_reason && (
            <div>
              <span className="muted">{row.health_reason}</span>
            </div>
          )}
        </div>
      ),
    },
  ]

  const emptyTitle = summary.total === 0 ? 'No connections yet' : 'No simulated connections'
  const emptyDescription =
    summary.total === 0
      ? 'This business has no integration connections, so nothing here is simulated.'
      : 'No connection of this business is marked as simulated.'

  return (
    <div className="stack">
      <Banner variant="info" title="Read-only page">
        There is no what-if simulation engine or scenario sandbox in this application. Here, simulation means
        sample data that engineers create with three commands on the server. This page only lists connections
        that are already marked as simulated and explains those commands. It never starts a simulation and
        never changes data.
      </Banner>

      <h2 style={{ margin: 0, fontSize: 'var(--text-section)' }}>{title}</h2>

      <div className="stack-sm">
        <h3 style={{ margin: 0, fontSize: 'var(--text-section)' }}>Simulated connections</h3>
        <p className="muted">
          A simulated connection is marked as a mock connection. Data from it is Sample data (SIMULATED), not
          data from a real provider.
        </p>

        <div className="grid-kpi">
          <KpiTile title="Connections checked" value={summary.total} />
          <KpiTile title="Simulated" value={summary.simulated} />
          <KpiTile title="Not marked simulated" value={summary.notSimulated} />
        </div>

        {summary.maybeMore && <p className="muted">Only the first 50 connections are checked here.</p>}

        <DataTable
          title="Simulated connections"
          ariaLabel="Simulated connections"
          showDensityToggle={false}
          rows={rows}
          columns={columns}
          emptyTitle={emptyTitle}
          emptyDescription={emptyDescription}
        />
      </div>

      <div className="stack-sm">
        <h3 style={{ margin: 0, fontSize: 'var(--text-section)' }}>Commands that create sample data</h3>
        <p>{SERVER_ONLY_NOTICE}</p>
        <p>Nothing on this page starts a simulation or changes data.</p>

        {SIMULATION_COMMANDS.map((cmd) => (
          <div key={cmd.key} className="journey-card stack-sm">
            <div>
              <strong>{cmd.title}</strong> <span className="font-mono">{cmd.name}</span>
            </div>
            <p>{cmd.summary}</p>
            <CopyableCode inline={false} value={cmd.command} label={`${cmd.name} command`} />
            <ul>
              {COMMAND_EFFECTS.map((effect, idx) => (
                <li key={idx}>{effect}</li>
              ))}
            </ul>
            <p>{`Demo business slug starts with ${cmd.demoPrefix}`}</p>
          </div>
        ))}

        <p className="muted">{COMMAND_FLAGS_NOTE}</p>
      </div>
    </div>
  )
}
