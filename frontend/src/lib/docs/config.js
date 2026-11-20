/**
 * Bizora Live /docs Module — Access Control & Scheduling Configuration
 */

export const DEFAULT_SCHEDULE = {
  enabled: true,
  overrideMode: 'SCHEDULE', // 'SCHEDULE' | 'ALWAYS_PUBLIC' | 'FORCE_OFFLINE'
  startDate: '2026-06-10T00:00:00+06:00',
  endDate: '2026-06-14T23:59:59+06:00',
  timezone: 'Asia/Dhaka',
  title: 'Bizora — Autonomous Enterprise Business Brain',
  tagline: 'Live YC Pitch Deck & Technical Documentation System',
  teamName: 'Bizora Core Architecture & Engineering Team',
  contactEmail: 'founders@bizora.app',
  updatedAt: '2026-11-20T16:00:00+06:00',
  updatedBy: 'system-admin',
}

export const OVERRIDE_MODES = [
  {
    id: 'SCHEDULE',
    label: 'Follow Schedule',
    description: 'Public access is automatically governed by the start and end dates below.',
  },
  {
    id: 'ALWAYS_PUBLIC',
    label: 'Always Public (Override)',
    description: 'Docs are immediately public to all visitors regardless of dates.',
  },
  {
    id: 'FORCE_OFFLINE',
    label: 'Force Offline (Restricted)',
    description: 'Docs are locked and inaccessible to the public. Admins retain preview access.',
  },
]

export const SCHEDULE_PRESETS = [
  {
    id: 'judging-window',
    label: 'Default Judging Window (June 10 – June 14)',
    startDate: '2026-06-10T00:00:00+06:00',
    endDate: '2026-06-14T23:59:59+06:00',
    overrideMode: 'SCHEDULE',
    enabled: true,
  },
  {
    id: 'investor-48h',
    label: 'Investor Preview (Next 48 Hours)',
    getDates: () => {
      const now = new Date()
      const end = new Date(now.getTime() + 48 * 60 * 60 * 1000)
      return {
        startDate: now.toISOString(),
        endDate: end.toISOString(),
        overrideMode: 'SCHEDULE',
        enabled: true,
      }
    },
  },
  {
    id: 'unrestricted',
    label: 'Unrestricted Public Access',
    overrideMode: 'ALWAYS_PUBLIC',
    enabled: true,
  },
  {
    id: 'offline-locked',
    label: 'Emergency Lock / Maintenance',
    overrideMode: 'FORCE_OFFLINE',
    enabled: false,
  },
]

export function getDefaultDocsConfig() {
  return JSON.parse(JSON.stringify(DEFAULT_SCHEDULE))
}

/**
 * Check if a session belongs to an administrative user.
 */
export function isDocsAdmin(session) {
  if (!session || !session.authenticated) return false
  if (session.user?.is_staff || session.user?.is_superuser) return true
  if (Array.isArray(session.businesses)) {
    return session.businesses.some((b) => b.role === 'OWNER' || b.role === 'MANAGER' || b.role === 'ADMIN')
  }
  return false
}

/**
 * Evaluates whether /docs is currently accessible to the given user session.
 *
 * @param {Object} config - The schedule and visibility configuration
 * @param {Object} session - The current user session
 * @param {Date|string|number} [currentTime=new Date()] - Reference timestamp
 * @returns {Object} Evaluation result with access flags, reasons, and timing details
 */
export function evaluateDocsAccess(config, session, currentTime = new Date()) {
  const cfg = config || DEFAULT_SCHEDULE
  const now = new Date(currentTime)
  const nowMs = now.getTime()
  const isAdmin = isDocsAdmin(session)

  const startDate = new Date(cfg.startDate || DEFAULT_SCHEDULE.startDate)
  const endDate = new Date(cfg.endDate || DEFAULT_SCHEDULE.endDate)
  const startMs = startDate.getTime()
  const endMs = endDate.getTime()

  // Evaluate public access criteria
  let publicGranted = false
  let publicReason = 'UNKNOWN'
  let publicMessage = ''

  if (cfg.overrideMode === 'FORCE_OFFLINE') {
    publicGranted = false
    publicReason = 'FORCE_OFFLINE'
    publicMessage = 'Documentation portal has been temporarily locked by an administrator.'
  } else if (cfg.overrideMode === 'ALWAYS_PUBLIC') {
    publicGranted = true
    publicReason = 'ALWAYS_PUBLIC'
    publicMessage = 'Documentation is publicly accessible via admin override.'
  } else if (!cfg.enabled) {
    publicGranted = false
    publicReason = 'DISABLED'
    publicMessage = 'Documentation portal visibility is currently toggled OFF.'
  } else {
    // Scheduled window
    if (nowMs < startMs) {
      publicGranted = false
      publicReason = 'SCHEDULE_PENDING'
      publicMessage = `Showcase window opens on ${formatDateDisplay(startDate)}.`
    } else if (nowMs > endMs) {
      publicGranted = false
      publicReason = 'SCHEDULE_EXPIRED'
      publicMessage = `Showcase window closed on ${formatDateDisplay(endDate)}.`
    } else {
      publicGranted = true
      publicReason = 'SCHEDULE_ACTIVE'
      publicMessage = `Showcase window is active until ${formatDateDisplay(endDate)}.`
    }
  }

  // Final determination: Admins ALWAYS have access
  const granted = isAdmin || publicGranted

  return {
    granted,
    isAdmin,
    publicGranted,
    reason: isAdmin && !publicGranted ? 'ADMIN_OVERRIDE' : publicReason,
    publicReason,
    message: isAdmin && !publicGranted ? `Admin Preview: ${publicMessage}` : publicMessage,
    window: {
      startDate: cfg.startDate,
      endDate: cfg.endDate,
      timezone: cfg.timezone || 'Asia/Dhaka',
      isWithinWindow: nowMs >= startMs && nowMs <= endMs,
      startsInMs: Math.max(0, startMs - nowMs),
      remainingMs: Math.max(0, endMs - nowMs),
    },
    overrideMode: cfg.overrideMode,
    enabled: cfg.enabled,
    evaluatedAt: now.toISOString(),
  }
}

function formatDateDisplay(d) {
  try {
    return d.toLocaleString('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
      timeZoneName: 'short',
    })
  } catch {
    return d.toISOString()
  }
}
