'use client'

import { useState } from 'react'
import { clientApi } from '@/lib/clientApi'
import { businessApiPath } from '@/lib/catalog'
import { fieldValue, label } from '@/lib/format'
import { StatusBadge } from './DataTable'

const CONTRACTS = {
  integrations: { capability: 'prepare_operation', fields: ['operation', 'entity_type', 'entity_id'] },
  bi: { capability: 'entity_context', fields: ['entity_type', 'entity_id'] },
  graph: { capability: 'entity_context', fields: ['entity_type', 'entity_id'] },
  ai: { capability: 'entity_context', fields: ['entity_type', 'entity_id'] },
  memory: { capability: 'policy_context', fields: ['query'] },
  configuration: { capability: 'policy', fields: ['policy_key'] },
  monitoring: { capability: 'freshness', fields: ['resource'] },
}

const OPERATION_ENTITY = {
  MESSAGE_SEND: 'MESSAGE',
  CALL_INITIATE: 'CALL',
  SHIPMENT_SUBMIT: 'SHIPMENT',
  SHIPMENT_CANCEL: 'SHIPMENT',
}

export default function ContractTools({ business }) {
  const [owner, setOwner] = useState('monitoring')
  const [operation, setOperation] = useState('MESSAGE_SEND')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [result, setResult] = useState(null)
  const contract = CONTRACTS[owner]
  async function submit(event) {
    event.preventDefault()
    setBusy(true)
    setError('')
    setResult(null)
    const values = Object.fromEntries(new FormData(event.currentTarget).entries())
    if (owner === 'integrations') values.entity_type = OPERATION_ENTITY[values.operation]
    if (values.entity_id) values.entity_id = Number(values.entity_id)
    try {
      setResult(
        await clientApi(businessApiPath(business.id, `contracts/${owner}/${contract.capability}`), {
          method: 'POST',
          body: { request_id: crypto.randomUUID(), payload: values },
        }),
      )
    } catch (failure) {
      setError(failure.message)
    } finally {
      setBusy(false)
    }
  }
  return (
    <>
      <div className="page-heading">
        <div>
          <p className="page-context">Administration</p>
          <h1>Service contracts</h1>
          <p>Inspect mounted domain contracts and their adapter availability for {business.name}.</p>
        </div>
        <StatusBadge text="Partial" />
      </div>
      <div className="alert alert-warning">
        <strong>Diagnostic only.</strong> A prepared request or simulated response is not live provider
        execution.
      </div>
      <section className="surface contract-panel">
        <label htmlFor="contract-owner">Service owner</label>
        <select
          id="contract-owner"
          value={owner}
          onChange={(event) => {
            setOwner(event.target.value)
            setOperation('MESSAGE_SEND')
            setResult(null)
            setError('')
          }}
        >
          {Object.keys(CONTRACTS).map((key) => (
            <option key={key} value={key}>
              {label(key)}
            </option>
          ))}
        </select>
        <p className="helptext">Capability: {label(contract.capability)}</p>
        <form onSubmit={submit} key={owner}>
          {contract.fields.map((field) => (
            <div className="form-field" key={field}>
              <label htmlFor={`contract-${field}`}>{label(field)}</label>
              {field === 'operation' ? (
                <select
                  name={field}
                  id={`contract-${field}`}
                  value={operation}
                  onChange={(event) => setOperation(event.target.value)}
                  required
                >
                  <option value="MESSAGE_SEND">Message send</option>
                  <option value="CALL_INITIATE">Call initiate</option>
                  <option value="SHIPMENT_SUBMIT">Shipment submit</option>
                  <option value="SHIPMENT_CANCEL">Shipment cancel</option>
                </select>
              ) : owner === 'integrations' && field === 'entity_type' ? (
                <input name={field} id={`contract-${field}`} value={OPERATION_ENTITY[operation]} readOnly />
              ) : (
                <input
                  name={field}
                  id={`contract-${field}`}
                  required
                  inputMode={field === 'entity_id' ? 'numeric' : undefined}
                  pattern={field === 'entity_id' ? '[1-9][0-9]*' : undefined}
                />
              )}
            </div>
          ))}
          <button className="button button-primary" disabled={busy}>
            {busy ? 'Checking…' : 'Check contract'}
          </button>
        </form>
        {error && (
          <p className="form-error" role="alert">
            {error}
          </p>
        )}
        {result && (
          <div className="plan-result" role="status">
            <StatusBadge text={result.simulated ? 'Simulation' : result.status || 'Unavailable'} />
            <pre>{fieldValue(result)}</pre>
          </div>
        )}
      </section>
    </>
  )
}
