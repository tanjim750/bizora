'use client'

import React, { useState } from 'react'
import { Mail, Copy, Check, ShieldCheck } from 'lucide-react'

export function DocsTeamSection({ teamName, members = [] }) {
  const [copiedId, setCopiedId] = useState(null)
  const [imgErrors, setImgErrors] = useState({})

  const handleCopyEmail = async (id, email, e) => {
    e.preventDefault()
    e.stopPropagation()
    try {
      await navigator.clipboard.writeText(email)
      setCopiedId(id)
      setTimeout(() => setCopiedId(null), 2000)
    } catch {
      // clipboard fallback
    }
  }

  const handleImgError = (id) => {
    setImgErrors((prev) => ({ ...prev, [id]: true }))
  }

  return (
    <div className="docs-team-container">
      {teamName && (
        <div className="docs-team-header" style={{ marginBottom: 'var(--space-4)' }}>
          <span
            style={{
              fontSize: 'var(--text-overline)',
              fontWeight: 600,
              textTransform: 'uppercase',
              letterSpacing: 'var(--tracking-overline)',
              color: 'var(--color-primary)',
            }}
          >
            Core Engineering & Leadership
          </span>
          <h3
            style={{
              fontSize: 'var(--text-section)',
              fontWeight: 600,
              color: 'var(--color-text)',
              margin: 'var(--space-1) 0 0 0',
            }}
          >
            {teamName}
          </h3>
        </div>
      )}

      <div className="docs-team-grid">
        {members.map((member) => {
          const hasImageError = imgErrors[member.id] || !member.avatar
          const isCopied = copiedId === member.id

          return (
            <div key={member.id} className="docs-team-card">
              {/* Profile Picture with Uniform Frame & Fallback Avatar */}
              <div className="docs-team-avatar-frame" aria-label={`Profile photo of ${member.name}`}>
                {!hasImageError ? (
                  /* eslint-disable-next-line @next/next/no-img-element */
                  <img
                    src={member.avatar}
                    alt={member.name}
                    className="docs-team-avatar-img"
                    onError={() => handleImgError(member.id)}
                    loading="lazy"
                  />
                ) : (
                  <div className="docs-team-avatar-fallback" role="img" aria-label={member.name}>
                    {member.initials || member.name.slice(0, 2).toUpperCase()}
                  </div>
                )}
              </div>

              {/* Identity & Role */}
              <h4 className="docs-team-name">{member.name}</h4>
              <div className="docs-team-role">{member.role}</div>

              {/* Email Address with Copy Trigger */}
              <button
                type="button"
                className="docs-team-email"
                onClick={(e) => handleCopyEmail(member.id, member.email, e)}
                title="Click to copy email address"
                aria-label={`Copy email for ${member.name}`}
              >
                <Mail size={12} aria-hidden="true" />
                <span>{member.email}</span>
                {isCopied ? (
                  <Check size={12} style={{ color: 'var(--color-success)' }} aria-hidden="true" />
                ) : (
                  <Copy size={11} aria-hidden="true" />
                )}
              </button>

              {/* Bio & Focus Areas */}
              {member.bio && <p className="docs-team-bio">{member.bio}</p>}

              {Array.isArray(member.focusAreas) && member.focusAreas.length > 0 && (
                <div className="docs-team-tags">
                  {member.focusAreas.map((tag) => (
                    <span key={tag} className="docs-team-tag">
                      <ShieldCheck size={10} style={{ marginRight: 2 }} aria-hidden="true" />
                      {tag}
                    </span>
                  ))}
                </div>
              )}
            </div>
          )
        })}
      </div>
    </div>
  )
}
