'use client'

import { useState, useEffect, useCallback, useRef } from 'react'
import Link from 'next/link'
import {
  Banner,
  Button,
  Checkbox,
  CopyableCode,
  Dialog,
  Field,
  Input,
  Select,
  StatusChip,
  Textarea,
  UnavailableState,
} from '@/components/ui'
import { clientApi } from '@/lib/clientApi'
import { businessPath } from '@/lib/catalog'
import { money } from '@/lib/format'
import {
  canManageSteadfast,
  providersPath,
  connectionsPath,
  createShipmentPath,
  steadfastProviderId,
  normalizeConnections,
  connectionAvailability,
  findSteadfastShipment,
  prefillShipmentForm,
  validateShipmentForm,
  confirmedAbsentBody,
  describeCreateError,
  normalizeCreateResult,
  invoiceFor,
} from '@/lib/shipping/steadfast'

export default function SteadfastSendOrder({ businessId, role, order, customer, shipments, onSent }) {
  const [dialogOpen, setDialogOpen] = useState(false)
  const [step, setStep] = useState('loading') // loading | unavailable | form | confirm
  const [loadError, setLoadError] = useState(null)
  const [availability, setAvailability] = useState({ state: 'none', live: [], message: '' })
  const [selectedConnectionId, setSelectedConnectionId] = useState('')

  const [formData, setFormData] = useState(() => prefillShipmentForm({ order, customer }))
  const [formErrors, setFormErrors] = useState({})
  const [serverError, setServerError] = useState(null)
  const [validatedBody, setValidatedBody] = useState(null)

  const [busy, setBusy] = useState(false)
  const busyRef = useRef(false)
  busyRef.current = busy

  const [uncertainError, setUncertainError] = useState(null)
  const [confirmedAbsent, setConfirmedAbsent] = useState(false)
  const [sent, setSent] = useState(null)

  const handleCloseDialog = useCallback(() => {
    if (busyRef.current) return
    setDialogOpen(false)
  }, [])

  const loadConnections = useCallback(async () => {
    setStep('loading')
    setLoadError(null)
    try {
      const provData = await clientApi(providersPath(businessId))
      const pId = steadfastProviderId(provData)
      if (!pId) {
        const avail = connectionAvailability([])
        setAvailability(avail)
        setStep('unavailable')
        return
      }

      const connData = await clientApi(connectionsPath(businessId, pId))
      const conns = normalizeConnections(connData)
      const avail = connectionAvailability(conns)
      setAvailability(avail)

      if (avail.state === 'ready') {
        setSelectedConnectionId(String(avail.live[0]?.id || ''))
        setStep('form')
      } else {
        setStep('unavailable')
      }
    } catch (err) {
      setLoadError(err?.detail || err?.message || 'Could not load connections.')
    }
  }, [businessId])

  useEffect(() => {
    if (dialogOpen) {
      loadConnections()
      setFormData(prefillShipmentForm({ order, customer }))
      setFormErrors({})
      setServerError(null)
      setUncertainError(null)
      setConfirmedAbsent(false)
      setValidatedBody(null)
    }
  }, [dialogOpen, loadConnections, order, customer])

  const handleOpenDialog = () => {
    setDialogOpen(true)
  }

  const updateField = (field, value) => {
    setFormData((prev) => ({ ...prev, [field]: value }))
    if (formErrors[field]) {
      setFormErrors((prev) => {
        const next = { ...prev }
        delete next[field]
        return next
      })
    }
  }

  const handleReviewShipment = () => {
    const res = validateShipmentForm(formData)
    if (!res.ok) {
      setFormErrors(res.errors)
      return
    }
    setFormErrors({})
    setValidatedBody(res.body)
    setUncertainError(null)
    setConfirmedAbsent(false)
    setStep('confirm')
  }

  const handleSendShipment = async () => {
    if (busy) return
    setBusy(true)
    setServerError(null)

    try {
      let bodyToSend = {
        order_id: order?.id,
        ...validatedBody,
      }
      if (uncertainError && confirmedAbsent) {
        bodyToSend = confirmedAbsentBody(bodyToSend)
      }

      const data = await clientApi(createShipmentPath(businessId, selectedConnectionId), {
        method: 'POST',
        body: bodyToSend,
      })

      const norm = normalizeCreateResult(data)
      if (!norm) {
        setServerError('Courier answered, but the response could not be read.')
        setStep('form')
        return
      }

      setSent(norm)
      setDialogOpen(false)
      onSent?.(norm)
    } catch (err) {
      const desc = describeCreateError(err, order?.id)
      if (desc.kind === 'validation') {
        setFormErrors(desc.fieldErrors || {})
        setServerError(desc.message)
        setStep('form')
      } else if (desc.kind === 'uncertain') {
        setUncertainError(desc.message)
        setConfirmedAbsent(false)
      } else {
        setServerError(desc.message)
      }
    } finally {
      setBusy(false)
    }
  }

  const existing = sent?.shipment || findSteadfastShipment(shipments)

  return (
    <section className="drawer-section">
      <h3 className="drawer-section-title">Courier (Steadfast)</h3>

      <div aria-live="polite" className="stack-sm">
        {sent && (
          <Banner variant="success" title="Sent to Steadfast">
            {sent.created
              ? `Shipment #${sent.shipment.id} was created with tracking code ${sent.shipment.trackingCode} (status ${sent.shipment.status}).`
              : 'This order had already been sent to Steadfast. No new parcel was created.'}
          </Banner>
        )}
      </div>

      {!canManageSteadfast(role) ? (
        <p className="muted">Only owners and managers can send orders to Steadfast.</p>
      ) : existing ? (
        <div className="stack-sm">
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: 'var(--space-2)',
            }}
          >
            <StatusChip status={existing.status} size="sm" />
            <span className="muted">Sent to Steadfast</span>
            <span className="font-mono">{invoiceFor(order?.id)}</span>
          </div>

          {existing.trackingCode && <CopyableCode value={existing.trackingCode} />}

          <p>
            <Link
              href={`${businessPath(businessId, 'commerce/deliveries')}?open=shipments:${existing.id}`}
              className="button button-secondary button-sm"
            >
              Open shipment
            </Link>
          </p>
        </div>
      ) : order?.currency && String(order.currency).toUpperCase() !== 'BDT' ? (
        <p className="muted">
          Steadfast cash on delivery must be in BDT. This order is in {order.currency}, so it cannot be sent.
        </p>
      ) : (
        <div className="stack-sm">
          <p className="muted">
            Books a parcel for this order with the Steadfast courier. Bizora does not change the order status.
          </p>
          <div>
            <Button variant="primary" size="sm" onClick={handleOpenDialog}>
              Send to Steadfast
            </Button>
          </div>
        </div>
      )}

      {dialogOpen && (
        <Dialog
          isOpen={dialogOpen}
          onClose={handleCloseDialog}
          title={`Send order #${order?.id} to Steadfast`}
          subtitle={`Invoice ${invoiceFor(order?.id)}`}
        >
          <div className="stack" style={{ gap: 'var(--space-4)' }}>
            <div aria-live="polite">
              {loadError && (
                <Banner variant="danger">
                  {loadError}
                  <Button size="sm" variant="secondary" onClick={loadConnections}>
                    Retry
                  </Button>
                </Banner>
              )}
            </div>

            {step === 'loading' && <p className="muted">Looking for the Steadfast connection…</p>}

            {step === 'unavailable' && (
              <div className="stack-sm">
                <UnavailableState
                  owner="Integrations"
                  title="Steadfast is not connected for sending"
                  reason={availability.message}
                />
                <div className="button-row">
                  <Button variant="secondary" onClick={handleCloseDialog}>
                    Close
                  </Button>
                </div>
              </div>
            )}

            {step === 'form' && (
              <div className="stack" style={{ gap: 'var(--space-3)' }}>
                <Banner variant="warning" title="This books a real parcel with the courier">
                  <p>
                    Sending creates a consignment at Steadfast under invoice {invoiceFor(order?.id)}. Bizora
                    cannot cancel it at Steadfast. The order status is not changed.
                  </p>
                </Banner>

                {serverError && <Banner variant="danger">{serverError}</Banner>}

                {availability.live.length > 1 && (
                  <Field label="Steadfast connection">
                    <Select
                      options={availability.live.map((c) => ({
                        value: String(c.id),
                        label: `${c.name} (#${c.id})`,
                      }))}
                      value={selectedConnectionId}
                      onChange={(e) => setSelectedConnectionId(e.target.value)}
                    />
                  </Field>
                )}

                <Field label="Recipient name" required error={formErrors.recipient_name}>
                  <Input
                    value={formData.recipient_name}
                    onChange={(e) => updateField('recipient_name', e.target.value)}
                  />
                </Field>

                <Field
                  label="Recipient phone"
                  required
                  hint="11 digits starting with 01"
                  error={formErrors.recipient_phone}
                >
                  <Input
                    value={formData.recipient_phone}
                    onChange={(e) => updateField('recipient_phone', e.target.value)}
                  />
                </Field>

                <Field label="Delivery address" required error={formErrors.recipient_address}>
                  <Textarea
                    rows={3}
                    value={formData.recipient_address}
                    onChange={(e) => updateField('recipient_address', e.target.value)}
                  />
                </Field>

                <Field
                  label="Cash on delivery amount (BDT)"
                  required
                  hint="Enter 0 if there is nothing to collect."
                  error={formErrors.cod_amount}
                >
                  <Input
                    value={formData.cod_amount}
                    onChange={(e) => updateField('cod_amount', e.target.value)}
                  />
                </Field>

                <Field label="Note (optional)" error={formErrors.note}>
                  <Textarea
                    rows={2}
                    value={formData.note}
                    onChange={(e) => updateField('note', e.target.value)}
                  />
                </Field>

                <div className="button-row">
                  <Button variant="secondary" onClick={handleCloseDialog}>
                    Cancel
                  </Button>
                  <Button variant="primary" onClick={handleReviewShipment}>
                    Review shipment
                  </Button>
                </div>
              </div>
            )}

            {step === 'confirm' && (
              <div className="stack" style={{ gap: 'var(--space-3)' }}>
                {serverError && <Banner variant="danger">{serverError}</Banner>}

                <dl className="drawer-prop-list">
                  <div className="drawer-prop-item">
                    <dt>Order</dt>
                    <dd className="font-mono">#{order?.id}</dd>
                  </div>
                  <div className="drawer-prop-item">
                    <dt>Recipient</dt>
                    <dd>{validatedBody?.recipient_name}</dd>
                  </div>
                  <div className="drawer-prop-item">
                    <dt>Phone</dt>
                    <dd>{validatedBody?.recipient_phone}</dd>
                  </div>
                  <div className="drawer-prop-item">
                    <dt>Address</dt>
                    <dd>{validatedBody?.recipient_address}</dd>
                  </div>
                  <div className="drawer-prop-item">
                    <dt>Cash on delivery</dt>
                    <dd className="font-mono">{money(validatedBody?.cod_amount, 'BDT')}</dd>
                  </div>
                  <div className="drawer-prop-item">
                    <dt>Connection</dt>
                    <dd>
                      {availability.live.find((c) => String(c.id) === String(selectedConnectionId))?.name ||
                        `#${selectedConnectionId}`}
                    </dd>
                  </div>
                </dl>

                <p className="font-semibold">Send this parcel to Steadfast now?</p>

                {uncertainError && (
                  <div className="stack-sm">
                    <Banner variant="warning" title="Steadfast may already have this parcel">
                      {uncertainError}
                    </Banner>
                    <Checkbox
                      label={`I checked the Steadfast portal and invoice ${invoiceFor(order?.id)} does not exist.`}
                      hint="If the parcel does exist, sending again books a duplicate."
                      checked={confirmedAbsent}
                      onChange={(e) => setConfirmedAbsent(e.target.checked)}
                    />
                  </div>
                )}

                <div className="button-row">
                  <Button variant="secondary" disabled={busy} onClick={() => setStep('form')}>
                    Back
                  </Button>
                  {uncertainError ? (
                    <Button
                      variant="danger"
                      disabled={!confirmedAbsent || busy}
                      loading={busy}
                      onClick={handleSendShipment}
                    >
                      Send again
                    </Button>
                  ) : (
                    <Button variant="primary" disabled={busy} loading={busy} onClick={handleSendShipment}>
                      Send to Steadfast
                    </Button>
                  )}
                </div>
              </div>
            )}
          </div>
        </Dialog>
      )}
    </section>
  )
}
