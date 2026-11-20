'use client'

import React, { useState, useEffect } from 'react'
import Link from 'next/link'
import { Lock, Clock, Calendar, Mail, ShieldAlert, ArrowRight, ExternalLink } from 'lucide-react'
import BizoraLogo from '../ui/BizoraLogo'

export function DocsAccessRestricted({ access, config }) {
  const [timeLeft, setTimeLeft] = useState({
    days: 0,
    hours: 0,
    minutes: 0,
    seconds: 0,
  })

  const windowInfo = access?.window || {}
  const startDate = new Date(config?.startDate || windowInfo.startDate || '2026-06-10T00:00:00+06:00')
  const endDate = new Date(config?.endDate || windowInfo.endDate || '2026-06-14T23:59:59+06:00')

  useEffect(() => {
    function calculateCountdown() {
      const now = new Date().getTime()
      const startMs = startDate.getTime()
      const endMs = endDate.getTime()

      let targetMs = startMs
      if (now >= startMs && now <= endMs) {
        targetMs = endMs
      }

      const diff = Math.max(0, targetMs - now)
      const days = Math.floor(diff / (1000 * 60 * 60 * 24))
      const hours = Math.floor((diff % (1000 * 60 * 60 * 24)) / (1000 * 60 * 60))
      const minutes = Math.floor((diff % (1000 * 60 * 60)) / (1000 * 60))
      const seconds = Math.floor((diff % (1000 * 60)) / 1000)

      setTimeLeft({ days, hours, minutes, seconds })
    }

    calculateCountdown()
    const timer = setInterval(calculateCountdown, 1000)
    return () => clearInterval(timer)
  }, [startDate, endDate])

  const isPending = access?.publicReason === 'SCHEDULE_PENDING'
  const isExpired = access?.publicReason === 'SCHEDULE_EXPIRED'
  const isForceOffline = access?.publicReason === 'FORCE_OFFLINE' || access?.publicReason === 'DISABLED'

  return (
    <div className="docs-restricted-page">
      <div className="docs-restricted-card">
        {/* Brand Mark */}
        <div style={{ display: 'flex', justifyContent: 'center', marginBottom: 'var(--space-4)' }}>
          <BizoraLogo />
        </div>

        {/* Lock Icon Wrap */}
        <div className="docs-restricted-icon-wrap" aria-hidden="true">
          {isForceOffline ? <ShieldAlert size={28} /> : <Clock size={28} />}
        </div>

        {/* Heading */}
        <span
          style={{
            fontSize: 'var(--text-overline)',
            textTransform: 'uppercase',
            letterSpacing: 'var(--tracking-overline)',
            color: 'var(--color-primary)',
            fontWeight: 600,
          }}
        >
          {isForceOffline ? 'Access Restricted' : 'Scheduled Showcase Window'}
        </span>

        <h1 className="docs-restricted-h1">
          {isForceOffline
            ? 'Documentation Portal Offline'
            : isPending
              ? 'Documentation Portal Opens Soon'
              : isExpired
                ? 'Documentation Window Closed'
                : 'Controlled Showcase Period'}
        </h1>

        <p className="docs-restricted-lead">
          {isForceOffline
            ? 'The Bizora technical whitepaper and live pitch deck are temporarily restricted by administrators for scheduled maintenance.'
            : isPending
              ? 'The documentation portal is configured for judging and investor preview. It will automatically unlock when the showcase window begins.'
              : isExpired
                ? 'The scheduled judging showcase period for this documentation portal has concluded.'
                : 'Access to this system documentation is strictly governed by admin scheduling.'}
        </p>

        {/* Countdown Box */}
        {!isForceOffline && !isExpired && (
          <div className="docs-countdown-box">
            <span
              style={{
                fontSize: 'var(--text-caption)',
                color: 'var(--color-text-muted)',
                fontWeight: 600,
                textTransform: 'uppercase',
                letterSpacing: 'var(--tracking-overline)',
              }}
            >
              Time Remaining Until Launch
            </span>
            <div className="docs-countdown-grid">
              <div className="docs-countdown-unit">
                <span className="docs-countdown-number">{timeLeft.days}</span>
                <span className="docs-countdown-sub">Days</span>
              </div>
              <div className="docs-countdown-unit">
                <span className="docs-countdown-number">{timeLeft.hours}</span>
                <span className="docs-countdown-sub">Hours</span>
              </div>
              <div className="docs-countdown-unit">
                <span className="docs-countdown-number">{timeLeft.minutes}</span>
                <span className="docs-countdown-sub">Mins</span>
              </div>
              <div className="docs-countdown-unit">
                <span className="docs-countdown-number">{timeLeft.seconds}</span>
                <span className="docs-countdown-sub">Secs</span>
              </div>
            </div>
          </div>
        )}

        {/* Schedule Window Details */}
        <div
          style={{
            background: 'var(--color-surface-subtle)',
            border: '1px solid var(--color-border)',
            borderRadius: 'var(--radius-md)',
            padding: 'var(--space-3) var(--space-4)',
            marginBottom: 'var(--space-6)',
            fontSize: 'var(--text-body-sm)',
            color: 'var(--color-text-secondary)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            gap: 'var(--space-2)',
          }}
        >
          <Calendar size={16} style={{ color: 'var(--color-primary)' }} aria-hidden="true" />
          <span>
            <strong>Scheduled Window:</strong> June 10, 2026 (00:00) → June 14, 2026 (23:59 Asia/Dhaka)
          </span>
        </div>

        {/* Actions for Judges, Investors & Admins */}
        <div
          style={{
            display: 'flex',
            flexDirection: 'column',
            gap: 'var(--space-3)',
            alignItems: 'center',
          }}
        >
          <Link
            href="/login?next=/docs"
            className="docs-mode-tab active"
            style={{
              padding: '10px 24px',
              fontSize: 'var(--text-body)',
              display: 'inline-flex',
              alignItems: 'center',
              gap: 'var(--space-2)',
              textDecoration: 'none',
            }}
          >
            <Lock size={16} aria-hidden="true" />
            <span>Sign in as Admin to Unlock Preview</span>
            <ArrowRight size={16} aria-hidden="true" />
          </Link>

          <a
            href={`mailto:${config?.contactEmail || 'founders@bizora.app'}?subject=Bizora%20Docs%20Showcase%20Access%20Request`}
            style={{
              fontSize: 'var(--text-caption)',
              color: 'var(--color-text-muted)',
              display: 'inline-flex',
              alignItems: 'center',
              gap: 4,
              textDecoration: 'none',
              marginTop: 'var(--space-2)',
            }}
          >
            <Mail size={12} aria-hidden="true" />
            <span>Judging or investor inquiry? Contact {config?.contactEmail || 'founders@bizora.app'}</span>
          </a>
        </div>
      </div>
    </div>
  )
}
