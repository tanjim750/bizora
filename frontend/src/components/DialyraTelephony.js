'use client'

import React, { useState, useEffect, useCallback } from 'react'
import {
  PhoneCall,
  Activity,
  Server,
  RefreshCw,
  Plus,
  Play,
  ShieldCheck,
  CheckCircle2,
  AlertTriangle,
  Radio,
  FileCode,
  Settings,
} from 'lucide-react'
import {
  Button,
  DataTable,
  Dialog,
  Drawer,
  Field,
  Input,
  Select,
  Textarea,
  Banner,
  KpiTile,
  StatusChip,
  EmptyState,
} from '@/components/ui'
import { clientApi } from '@/lib/clientApi'
import { businessApiPath } from '@/lib/catalog'

export default function DialyraTelephony({ businessId }) {
  const [activeTab, setActiveTab] = useState('trunks')
  const [loading, setLoading] = useState(true)
  const [statusData, setStatusData] = useState(null)
  const [trunks, setTrunks] = useState([])
  const [flows, setFlows] = useState([])
  const [actionMessage, setActionMessage] = useState(null)

  // Trunk Status Drawer
  const [statusDrawerOpen, setStatusDrawerOpen] = useState(false)
  const [selectedTrunkStatus, setSelectedTrunkStatus] = useState(null)
  const [loadingTrunkStatus, setLoadingTrunkStatus] = useState(false)

  // Create Trunk Dialog
  const [createModalOpen, setCreateModalOpen] = useState(false)
  const [createBusy, setCreateBusy] = useState(false)
  const [createError, setCreateError] = useState('')
  const [trunkForm, setTrunkForm] = useState({
    name: '',
    provider_name: '',
    trunk_mode: 'registration',
    host: '',
    port: 5060,
    username: '',
    password: '',
    max_concurrent_calls: 10,
    is_active: true,
    enable_inbound: false,
    transport: 'udp',
    dtmf_mode: 'rfc4733',
  })

  // Originate Call Dialog
  const [originateModalOpen, setOriginateModalOpen] = useState(false)
  const [originateBusy, setOriginateBusy] = useState(false)
  const [originateError, setOriginateError] = useState('')
  const [originateSuccess, setOriginateSuccess] = useState(null)
  const [callForm, setCallForm] = useState({
    phone: '',
    sip_trunk_id: '',
    flow_id: '',
    customer_name: '',
    notes: '',
  })

  const loadData = useCallback(async () => {
    setLoading(true)
    try {
      const [stRes, trRes, flRes] = await Promise.allSettled([
        clientApi(businessApiPath(businessId, 'dialyra/status')),
        clientApi(businessApiPath(businessId, 'dialyra/trunks')),
        clientApi(businessApiPath(businessId, 'dialyra/flows')),
      ])

      if (stRes.status === 'fulfilled') setStatusData(stRes.value)
      if (trRes.status === 'fulfilled') {
        const tVal = trRes.value
        setTrunks(Array.isArray(tVal) ? tVal : tVal?.items || tVal?.results || [])
      }
      if (flRes.status === 'fulfilled') {
        const fVal = flRes.value
        setFlows(Array.isArray(fVal) ? fVal : fVal?.items || fVal?.results || [])
      }
    } catch {
      // Handled silently
    } finally {
      setLoading(false)
    }
  }, [businessId])

  useEffect(() => {
    loadData()
  }, [loadData])

  // View PJSIP Realtime Status
  const handleViewStatus = async (trunkId) => {
    setStatusDrawerOpen(true)
    setLoadingTrunkStatus(true)
    setSelectedTrunkStatus(null)
    try {
      const res = await clientApi(businessApiPath(businessId, `dialyra/trunks/${trunkId}/status`))
      setSelectedTrunkStatus(res)
    } catch (err) {
      setSelectedTrunkStatus({ error: err.message || 'Failed to fetch status' })
    } finally {
      setLoadingTrunkStatus(false)
    }
  }

  // Test SIP Trunk
  const handleTestTrunk = async (trunkId) => {
    setActionMessage({ tone: 'info', text: `Testing SIP trunk #${trunkId}…` })
    try {
      const res = await clientApi(businessApiPath(businessId, `dialyra/trunks/${trunkId}/test`), {
        method: 'POST',
      })
      setActionMessage({
        tone: 'success',
        text: `Trunk #${trunkId} test completed: ${res.message || res.status || 'Success'}`,
      })
      loadData()
    } catch (err) {
      setActionMessage({ tone: 'danger', text: `Trunk test failed: ${err.message}` })
    }
  }

  // Reload SIP Trunk in Asterisk
  const handleReloadTrunk = async (trunkId) => {
    setActionMessage({ tone: 'info', text: `Reloading PJSIP for trunk #${trunkId}…` })
    try {
      const res = await clientApi(businessApiPath(businessId, `dialyra/trunks/${trunkId}/reload`), {
        method: 'POST',
        body: { enable_inbound: false },
      })
      setActionMessage({
        tone: 'success',
        text: `Trunk #${trunkId} reloaded successfully (${res.reload?.status || 'Active'})`,
      })
      loadData()
    } catch (err) {
      setActionMessage({ tone: 'danger', text: `Reload failed: ${err.message}` })
    }
  }

  // Create Trunk Submit
  const handleCreateTrunk = async (e) => {
    e.preventDefault()
    setCreateBusy(true)
    setCreateError('')
    try {
      const payload = {
        name: trunkForm.name,
        provider_name: trunkForm.provider_name,
        trunk_mode: trunkForm.trunk_mode,
        host: trunkForm.host,
        port: Number(trunkForm.port) || 5060,
        max_concurrent_calls: Number(trunkForm.max_concurrent_calls) || 10,
        is_active: trunkForm.is_active,
        enable_inbound: trunkForm.enable_inbound,
        advanced: {
          transport: trunkForm.transport,
          dtmf_mode: trunkForm.dtmf_mode,
          codecs: ['ulaw', 'alaw'],
        },
      }
      if (trunkForm.trunk_mode === 'registration') {
        payload.username = trunkForm.username
        payload.password = trunkForm.password
      }
      await clientApi(businessApiPath(businessId, 'dialyra/trunks'), {
        method: 'POST',
        body: payload,
      })
      setCreateModalOpen(false)
      setActionMessage({ tone: 'success', text: `SIP Trunk '${trunkForm.name}' created and synced!` })
      loadData()
    } catch (err) {
      setCreateError(err.message || 'Failed to create SIP trunk.')
    } finally {
      setCreateBusy(false)
    }
  }

  // Originate Call Submit
  const handleOriginateCall = async (e) => {
    e.preventDefault()
    if (!callForm.phone) return
    setOriginateBusy(true)
    setOriginateError('')
    setOriginateSuccess(null)
    try {
      const body = {
        phone: callForm.phone.trim(),
      }
      if (callForm.sip_trunk_id) body.sip_trunk_id = Number(callForm.sip_trunk_id)
      if (callForm.flow_id) body.flow_id = Number(callForm.flow_id)
      if (callForm.customer_name || callForm.notes) {
        body.webhook_variables = {
          customer_name: callForm.customer_name || 'Valued Customer',
          notes: callForm.notes || 'Bizora Outbound',
        }
      }

      const res = await clientApi(businessApiPath(businessId, 'dialyra/calls/originate'), {
        method: 'POST',
        body,
      })

      setOriginateSuccess(res)
      setActionMessage({
        tone: 'success',
        text: `Call initiated to ${callForm.phone}! Call ID: #${res.call_id}`,
      })
      setCallForm({ phone: '', sip_trunk_id: '', flow_id: '', customer_name: '', notes: '' })
    } catch (err) {
      setOriginateError(err.message || 'Call origination failed.')
    } finally {
      setOriginateBusy(false)
    }
  }

  return (
    <div className="stack section-gap">
      {/* KPI Tiles */}
      <div className="grid-kpi">
        <KpiTile
          label="Dialyra Gateway"
          value={statusData?.configured ? 'CONNECTED' : 'NOT CONFIGURED'}
          subtext={statusData?.base_url || 'https://api.dialyra.com'}
          icon={Activity}
        />
        <KpiTile
          label="SIP Trunks"
          value={String(trunks.length)}
          subtext="Active telephony trunks"
          icon={Server}
        />
        <KpiTile label="IVR Flows" value={String(flows.length)} subtext="Voice journey flows" icon={Radio} />
        <KpiTile
          label="Runtime Engine"
          value="v3 Ready"
          subtext="Asterisk PJSIP Realtime"
          icon={ShieldCheck}
        />
      </div>

      {actionMessage && <Banner tone={actionMessage.tone} title={actionMessage.text} />}

      {/* Sub-nav buttons */}
      <div
        className="surface card-padding"
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          flexWrap: 'wrap',
          gap: 'var(--space-3)',
        }}
      >
        <div style={{ display: 'flex', gap: 'var(--space-2)' }}>
          <Button
            variant={activeTab === 'trunks' ? 'primary' : 'secondary'}
            size="sm"
            onClick={() => setActiveTab('trunks')}
          >
            <Server size={14} style={{ marginRight: '6px' }} />
            SIP Trunks ({trunks.length})
          </Button>
          <Button
            variant={activeTab === 'originate' ? 'primary' : 'secondary'}
            size="sm"
            onClick={() => setActiveTab('originate')}
          >
            <PhoneCall size={14} style={{ marginRight: '6px' }} />
            Originate Outbound Call
          </Button>
          <Button
            variant={activeTab === 'flows' ? 'primary' : 'secondary'}
            size="sm"
            onClick={() => setActiveTab('flows')}
          >
            <Radio size={14} style={{ marginRight: '6px' }} />
            IVR Flows ({flows.length})
          </Button>
        </div>

        <div style={{ display: 'flex', gap: 'var(--space-2)' }}>
          <Button variant="secondary" size="sm" onClick={loadData} disabled={loading}>
            <RefreshCw size={14} style={{ marginRight: '6px' }} className={loading ? 'animate-spin' : ''} />
            Refresh
          </Button>
          <Button variant="primary" size="sm" onClick={() => setCreateModalOpen(true)}>
            <Plus size={14} style={{ marginRight: '6px' }} />
            New SIP Trunk
          </Button>
        </div>
      </div>

      {/* TAB 1: SIP Trunks Table */}
      {activeTab === 'trunks' && (
        <div className="surface">
          <DataTable
            columns={[
              {
                key: 'name',
                label: 'Trunk Name',
                render: (row) => (
                  <div>
                    <span className="font-semibold text-body">{row.name}</span>
                    <div className="font-mono text-caption text-muted">
                      {row.provider_name || 'Generic SIP'}
                    </div>
                  </div>
                ),
              },
              {
                key: 'trunk_mode',
                label: 'Mode',
                render: (row) => (
                  <span className="badge badge-outline font-mono text-caption">
                    {row.trunk_mode || 'registration'}
                  </span>
                ),
              },
              {
                key: 'host',
                label: 'Host & Port',
                render: (row) => (
                  <span className="font-mono text-caption">
                    {row.host}:{row.port || 5060}
                  </span>
                ),
              },
              {
                key: 'max_concurrent_calls',
                label: 'Max Channels',
                render: (row) => (
                  <span className="font-mono text-caption">{row.max_concurrent_calls ?? '—'}</span>
                ),
              },
              {
                key: 'status',
                label: 'Status',
                render: (row) => <StatusChip status={row.status || 'ACTIVE'} size="sm" />,
              },
              {
                key: 'actions',
                label: 'Actions',
                render: (row) => (
                  <div style={{ display: 'flex', gap: 'var(--space-1)' }}>
                    <Button
                      variant="secondary"
                      size="sm"
                      onClick={() => handleViewStatus(row.id || row.trunk_id)}
                    >
                      Status
                    </Button>
                    <Button
                      variant="secondary"
                      size="sm"
                      onClick={() => handleTestTrunk(row.id || row.trunk_id)}
                    >
                      Test
                    </Button>
                    <Button
                      variant="secondary"
                      size="sm"
                      onClick={() => handleReloadTrunk(row.id || row.trunk_id)}
                    >
                      Reload
                    </Button>
                  </div>
                ),
              },
            ]}
            rows={trunks}
            businessId={businessId}
            emptyTitle="No SIP Trunks configured"
            emptyDescription="Add a SIP Trunk to enable voice calling via Dialyra."
            openInDrawer={false}
          />
        </div>
      )}

      {/* TAB 2: Originate Outbound Call Form */}
      {activeTab === 'originate' && (
        <div className="surface card-padding" style={{ maxWidth: '640px', margin: '0 auto' }}>
          <h2 style={{ fontSize: 'var(--text-h2)', marginBottom: 'var(--space-2)' }}>
            Originate Outbound Call (Dialyra v3)
          </h2>
          <p className="text-caption text-muted" style={{ marginBottom: 'var(--space-4)' }}>
            Trigger a live telephony call via Dialyra Asterisk softswitch. When answered, Dialyra executes the
            selected IVR flow.
          </p>

          {originateError && (
            <div style={{ marginBottom: 'var(--space-3)' }}>
              <Banner tone="danger" title={originateError} />
            </div>
          )}

          {originateSuccess && (
            <div style={{ marginBottom: 'var(--space-3)' }}>
              <Banner tone="success" title={`Call #${originateSuccess.call_id} successfully initiated!`}>
                <div style={{ marginTop: 'var(--space-1)', fontSize: 'var(--text-caption)' }}>
                  External UUID:{' '}
                  <span className="font-mono">{originateSuccess.dialyra?.call_log_uuid || '—'}</span>
                </div>
              </Banner>
            </div>
          )}

          <form onSubmit={handleOriginateCall} className="stack">
            <Field id="call-phone" label="Recipient Phone Number" required>
              <Input
                id="call-phone"
                placeholder="e.g. 01712345678 or +8801712345678"
                value={callForm.phone}
                onChange={(e) => setCallForm({ ...callForm, phone: e.target.value })}
                required
              />
            </Field>

            <Field id="call-trunk" label="SIP Trunk (Optional — auto-selects if empty)">
              <Select
                id="call-trunk"
                value={callForm.sip_trunk_id}
                onChange={(e) => setCallForm({ ...callForm, sip_trunk_id: e.target.value })}
              >
                <option value="">Auto-select ready trunk</option>
                {trunks.map((t) => (
                  <option key={t.id || t.trunk_id} value={t.id || t.trunk_id}>
                    {t.name} ({t.host})
                  </option>
                ))}
              </Select>
            </Field>

            <Field id="call-flow" label="IVR Voice Flow (Optional)">
              <Select
                id="call-flow"
                value={callForm.flow_id}
                onChange={(e) => setCallForm({ ...callForm, flow_id: e.target.value })}
              >
                <option value="">Default Business Flow</option>
                {flows.map((f) => (
                  <option key={f.id} value={f.id}>
                    {f.name || `Flow #${f.id}`}
                  </option>
                ))}
              </Select>
            </Field>

            <Field id="call-customer" label="Customer Name (Template Variable)">
              <Input
                id="call-customer"
                placeholder="e.g. Rahim Ahmed"
                value={callForm.customer_name}
                onChange={(e) => setCallForm({ ...callForm, customer_name: e.target.value })}
              />
            </Field>

            <div style={{ display: 'flex', justifyContent: 'flex-end', marginTop: 'var(--space-2)' }}>
              <Button variant="primary" type="submit" disabled={originateBusy} isLoading={originateBusy}>
                <Play size={14} style={{ marginRight: '6px' }} />
                Initiate Call Now
              </Button>
            </div>
          </form>
        </div>
      )}

      {/* TAB 3: IVR Flows */}
      {activeTab === 'flows' && (
        <div className="surface">
          <DataTable
            columns={[
              {
                key: 'name',
                label: 'Flow Name',
                render: (row) => (
                  <div>
                    <span className="font-semibold text-body">{row.name || `Flow #${row.id}`}</span>
                    <div className="font-mono text-caption text-muted">ID: {row.id}</div>
                  </div>
                ),
              },
              {
                key: 'type',
                label: 'Flow Type',
                render: (row) => (
                  <span className="badge badge-outline font-mono text-caption">
                    {row.type || 'OUTBOUND_VOICE'}
                  </span>
                ),
              },
              {
                key: 'status',
                label: 'Status',
                render: (row) => <StatusChip status={row.status || 'ACTIVE'} size="sm" />,
              },
            ]}
            rows={flows}
            businessId={businessId}
            emptyTitle="No IVR Flows found"
            emptyDescription="Configured Dialyra voice flows will appear here."
            openInDrawer={false}
          />
        </div>
      )}

      {/* PJSIP Status Drawer */}
      <Drawer
        isOpen={statusDrawerOpen}
        onClose={() => setStatusDrawerOpen(false)}
        title="Asterisk PJSIP Realtime Status"
      >
        {loadingTrunkStatus ? (
          <div className="card-padding text-muted">Loading live status from Asterisk…</div>
        ) : selectedTrunkStatus ? (
          <div className="stack card-padding">
            {selectedTrunkStatus.error ? (
              <Banner tone="danger" title={selectedTrunkStatus.error} />
            ) : (
              <>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <span className="text-caption text-muted">
                    Trunk ID: #{selectedTrunkStatus.trunk_id || selectedTrunkStatus.sip_trunk_id}
                  </span>
                  <StatusChip status={selectedTrunkStatus.status || 'ACTIVE'} size="sm" />
                </div>

                <div className="surface card-padding" style={{ background: 'var(--bg-subtle)' }}>
                  <div className="font-semibold text-body" style={{ marginBottom: 'var(--space-2)' }}>
                    Diagnostics & Readiness
                  </div>
                  <ul className="stack-sm text-caption">
                    <li>
                      Registration:{' '}
                      <strong>{selectedTrunkStatus.registration_status || 'not_required'}</strong>
                    </li>
                    <li>
                      Contact Status: <strong>{selectedTrunkStatus.contact_status || 'ok'}</strong>
                    </li>
                    <li>
                      Originate Eligible:{' '}
                      <strong>{selectedTrunkStatus.originate_eligible ? 'YES' : 'NO'}</strong>
                    </li>
                    <li>
                      Active Channels:{' '}
                      <strong>
                        {selectedTrunkStatus.active_calls ?? 0} /{' '}
                        {selectedTrunkStatus.max_concurrent_calls ?? '—'}
                      </strong>
                    </li>
                    <li>
                      PJSIP Endpoint:{' '}
                      <code className="font-mono">{selectedTrunkStatus.sip_endpoint || '—'}</code>
                    </li>
                  </ul>
                </div>

                {selectedTrunkStatus.realtime && (
                  <div>
                    <div
                      className="font-semibold text-caption text-secondary"
                      style={{ marginBottom: 'var(--space-1)' }}
                    >
                      Realtime Table Rows
                    </div>
                    <pre
                      className="font-mono text-caption"
                      style={{ padding: '8px', background: 'var(--bg-subtle)', borderRadius: '4px' }}
                    >
                      {JSON.stringify(
                        selectedTrunkStatus.realtime.rows || selectedTrunkStatus.realtime,
                        null,
                        2,
                      )}
                    </pre>
                  </div>
                )}
              </>
            )}
          </div>
        ) : null}
      </Drawer>

      {/* Create Trunk Dialog */}
      <Dialog
        isOpen={createModalOpen}
        onClose={() => setCreateModalOpen(false)}
        title="Create SIP Trunk (Dialyra v3)"
      >
        <form onSubmit={handleCreateTrunk} className="stack">
          {createError && <Banner tone="danger" title={createError} />}

          <Field id="trunk-name" label="Trunk Name" required>
            <Input
              id="trunk-name"
              placeholder="e.g. Primary Carrier Trunk"
              value={trunkForm.name}
              onChange={(e) => setTrunkForm({ ...trunkForm, name: e.target.value })}
              required
            />
          </Field>

          <Field id="trunk-provider" label="Provider Name" required>
            <Input
              id="trunk-provider"
              placeholder="e.g. Trizync / Twilio / Telnyx"
              value={trunkForm.provider_name}
              onChange={(e) => setTrunkForm({ ...trunkForm, provider_name: e.target.value })}
              required
            />
          </Field>

          <Field id="trunk-mode" label="Trunk Authentication Mode" required>
            <Select
              id="trunk-mode"
              value={trunkForm.trunk_mode}
              onChange={(e) => setTrunkForm({ ...trunkForm, trunk_mode: e.target.value })}
            >
              <option value="registration">Registration (SIP User & Secret)</option>
              <option value="ip_auth">IP Authentication (Static Contact)</option>
            </Select>
          </Field>

          <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr', gap: 'var(--space-2)' }}>
            <Field id="trunk-host" label="Host / Domain" required>
              <Input
                id="trunk-host"
                placeholder="sip.provider.com or IP"
                value={trunkForm.host}
                onChange={(e) => setTrunkForm({ ...trunkForm, host: e.target.value })}
                required
              />
            </Field>

            <Field id="trunk-port" label="Port" required>
              <Input
                id="trunk-port"
                type="number"
                value={trunkForm.port}
                onChange={(e) => setTrunkForm({ ...trunkForm, port: e.target.value })}
                required
              />
            </Field>
          </div>

          {trunkForm.trunk_mode === 'registration' && (
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 'var(--space-2)' }}>
              <Field id="trunk-user" label="Username" required>
                <Input
                  id="trunk-user"
                  placeholder="SIP Account Username"
                  value={trunkForm.username}
                  onChange={(e) => setTrunkForm({ ...trunkForm, username: e.target.value })}
                  required
                />
              </Field>
              <Field id="trunk-pass" label="Password" required>
                <Input
                  id="trunk-pass"
                  type="password"
                  placeholder="SIP Account Secret"
                  value={trunkForm.password}
                  onChange={(e) => setTrunkForm({ ...trunkForm, password: e.target.value })}
                  required
                />
              </Field>
            </div>
          )}

          <Field id="trunk-channels" label="Max Concurrent Channels" required>
            <Input
              id="trunk-channels"
              type="number"
              value={trunkForm.max_concurrent_calls}
              onChange={(e) => setTrunkForm({ ...trunkForm, max_concurrent_calls: e.target.value })}
              required
            />
          </Field>

          <div
            style={{
              display: 'flex',
              justifyContent: 'flex-end',
              gap: 'var(--space-2)',
              marginTop: 'var(--space-3)',
            }}
          >
            <Button variant="secondary" type="button" onClick={() => setCreateModalOpen(false)}>
              Cancel
            </Button>
            <Button variant="primary" type="submit" disabled={createBusy} isLoading={createBusy}>
              Save & Sync Trunk
            </Button>
          </div>
        </form>
      </Dialog>
    </div>
  )
}
