'use client'

import { useState } from 'react'
import { RefreshCw } from 'lucide-react'
import { Banner, Button, CopyableCode, StatusChip } from '@/components/ui'
import { clientApi } from '@/lib/clientApi'
import { dateTime } from '@/lib/format'
import {
  isSteadfastShipment,
  canManageSteadfast,
  canRefreshShipment,
  refreshShipmentPath,
  normalizeRefreshResult,
  describeRefresh,
  describeRefreshError,
} from '@/lib/shipping/steadfast'

export default function SteadfastRefreshShipment({ businessId, role, shipment, timezone, onRefreshed }) {
  const [busy, setBusy] = useState(false)
  const [notice, setNotice] = useState(null)

  if (!isSteadfastShipment(shipment)) {
    return null
  }

  const isManager = canManageSteadfast(role)
  const isRefreshable = canRefreshShipment(shipment, role)

  const handleRefresh = async () => {
    if (busy) return
    setBusy(true)
    setNotice(null)

    const prevStatus = shipment?.status
    try {
      const data = await clientApi(
        refreshShipmentPath(businessId, shipment.integration_connection, shipment.id),
        { method: 'POST' },
      )

      const norm = normalizeRefreshResult(data)
      if (!norm) {
        setNotice({
          variant: 'danger',
          title: 'Steadfast answered, but the answer could not be read.',
          lastChecked: null,
        })
        return
      }

      const desc = describeRefresh(prevStatus, norm)
      setNotice({
        variant: desc.tone,
        title: desc.message,
        lastChecked: new Date().toISOString(),
      })

      onRefreshed?.(norm.shipment, norm.changed)
    } catch (err) {
      setNotice({
        variant: 'danger',
        title: describeRefreshError(err),
        lastChecked: null,
      })
    } finally {
      setBusy(false)
    }
  }

  return (
    <section className="drawer-section">
      <h3 className="drawer-section-title">Courier status (Steadfast)</h3>

      <dl className="drawer-prop-list">
        <div className="drawer-prop-item">
          <dt>Status in Bizora</dt>
          <dd>
            <StatusChip status={shipment?.status} size="sm" />
          </dd>
        </div>
        <div className="drawer-prop-item">
          <dt>Tracking code</dt>
          <dd>{shipment?.tracking_code ? <CopyableCode value={shipment.tracking_code} /> : '—'}</dd>
        </div>
      </dl>

      <div aria-live="polite" className="stack-sm">
        {notice && (
          <Banner variant={notice.variant} title={notice.title}>
            {notice.lastChecked && (
              <p className="font-mono" style={{ margin: 0 }}>
                Last checked {dateTime(notice.lastChecked, timezone || 'Asia/Dhaka')}
              </p>
            )}
          </Banner>
        )}
      </div>

      {!isManager ? (
        <p className="muted">Only owners and managers can check courier status.</p>
      ) : !isRefreshable ? (
        <p className="muted">
          {!shipment?.integration_connection || !/^[1-9]\d*$/.test(String(shipment.integration_connection))
            ? 'This shipment is not linked to a Steadfast connection, so its status cannot be checked from Bizora.'
            : 'This shipment has no tracking code, so its status cannot be checked from Bizora.'}
        </p>
      ) : (
        <div className="stack-sm">
          <p className="muted">
            Asks Steadfast for the current status of this parcel and records any change.{' '}
            {'This only reads from Steadfast.'}
          </p>
          <div>
            <Button
              variant="secondary"
              size="sm"
              icon={RefreshCw}
              loading={busy}
              disabled={busy}
              onClick={handleRefresh}
            >
              Check status with Steadfast
            </Button>
          </div>
        </div>
      )}
    </section>
  )
}
