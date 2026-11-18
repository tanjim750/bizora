'use client'

import { useState } from 'react'
import { RULES_RESOURCE } from '@/lib/configuration/rules'
import { POLICIES_RESOURCE } from '@/lib/configuration/policies'
import ConfigResourceManager from './ConfigResourceManager'

export default function ConfigRulesPolicies({ businessId, role, timezone }) {
  const [kind, setKind] = useState('rules')

  return (
    <div className="stack" style={{ gap: 'var(--space-4, 16px)' }}>
      <div className="admin-subnav" role="group" aria-label="Record kind">
        <button
          type="button"
          aria-pressed={kind === 'rules'}
          className={`admin-subnav-btn ${kind === 'rules' ? 'is-active' : ''}`}
          onClick={() => setKind('rules')}
        >
          Rules
        </button>
        <button
          type="button"
          aria-pressed={kind === 'policies'}
          className={`admin-subnav-btn ${kind === 'policies' ? 'is-active' : ''}`}
          onClick={() => setKind('policies')}
        >
          Policies
        </button>
      </div>

      <ConfigResourceManager
        key={kind}
        resource={kind === 'rules' ? RULES_RESOURCE : POLICIES_RESOURCE}
        businessId={businessId}
        role={role}
        timezone={timezone}
      />
    </div>
  )
}
