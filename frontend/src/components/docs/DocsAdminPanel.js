'use client'

import React, { useState } from 'react'
import {
  X,
  Save,
  Clock,
  Calendar,
  Lock,
  Globe,
  Users,
  Edit3,
  RotateCcw,
  Check,
  AlertCircle,
  Plus,
  Trash2,
  ArrowUp,
  ArrowDown,
} from 'lucide-react'
import { SCHEDULE_PRESETS, OVERRIDE_MODES } from '@/lib/docs/config'

export function DocsAdminPanel({ isOpen, onClose, config, onUpdateConfig, content, onUpdateContent }) {
  const [activeTab, setActiveTab] = useState('visibility') // 'visibility' | 'content' | 'team'

  // Visibility & Scheduling form state
  const [enabled, setEnabled] = useState(config?.enabled ?? true)
  const [overrideMode, setOverrideMode] = useState(config?.overrideMode || 'SCHEDULE')
  const [startDate, setStartDate] = useState(config?.startDate?.slice(0, 16) || '2026-06-10T00:00')
  const [endDate, setEndDate] = useState(config?.endDate?.slice(0, 16) || '2026-06-14T23:59')
  const [timezone, setTimezone] = useState(config?.timezone || 'Asia/Dhaka')
  const [teamName, setTeamName] = useState(config?.teamName || 'The People Building Bizora')

  // Content form state
  const [pitchSections, setPitchSections] = useState(content?.pitchSections || [])
  const [selectedSectionIdx, setSelectedSectionIdx] = useState(0)
  const [teamMembers, setTeamMembers] = useState(content?.teamMembers || [])

  // Status flags
  const [isSaving, setIsSaving] = useState(false)
  const [statusNotice, setStatusNotice] = useState(null)

  if (!isOpen) return null

  const handleApplyPreset = (preset) => {
    if (preset.getDates) {
      const dates = preset.getDates()
      setStartDate(dates.startDate.slice(0, 16))
      setEndDate(dates.endDate.slice(0, 16))
      setOverrideMode(dates.overrideMode)
      setEnabled(dates.enabled)
    } else {
      if (preset.startDate) setStartDate(preset.startDate.slice(0, 16))
      if (preset.endDate) setEndDate(preset.endDate.slice(0, 16))
      if (preset.overrideMode) setOverrideMode(preset.overrideMode)
      if (preset.enabled !== undefined) setEnabled(preset.enabled)
    }
    setStatusNotice({ type: 'info', text: `Applied preset: "${preset.label}"` })
  }

  const handleSaveConfig = async () => {
    setIsSaving(true)
    setStatusNotice(null)
    try {
      const payload = {
        enabled,
        overrideMode,
        startDate: new Date(startDate).toISOString(),
        endDate: new Date(endDate).toISOString(),
        timezone,
        teamName,
      }
      const res = await fetch('/api/docs/config', {
        method: 'POST',
        headers: { 'content-type': 'application/json' },
        body: JSON.stringify(payload),
      })
      if (res.ok) {
        const json = await res.json()
        if (onUpdateConfig) onUpdateConfig(json.config)
        setStatusNotice({ type: 'success', text: 'Visibility & schedule settings updated successfully!' })
      } else {
        const err = await res.json().catch(() => ({}))
        setStatusNotice({ type: 'error', text: err.detail || 'Failed to update configuration.' })
      }
    } catch (err) {
      setStatusNotice({ type: 'error', text: err.message || 'Network error saving settings.' })
    } finally {
      setIsSaving(false)
    }
  }

  const handleSaveContent = async () => {
    setIsSaving(true)
    setStatusNotice(null)
    try {
      const payload = {
        pitchSections,
        teamMembers,
      }
      const res = await fetch('/api/docs/content', {
        method: 'POST',
        headers: { 'content-type': 'application/json' },
        body: JSON.stringify(payload),
      })
      if (res.ok) {
        const json = await res.json()
        if (onUpdateContent) onUpdateContent(json.content)
        setStatusNotice({ type: 'success', text: 'Content and team changes published successfully!' })
      } else {
        const err = await res.json().catch(() => ({}))
        setStatusNotice({ type: 'error', text: err.detail || 'Failed to save content.' })
      }
    } catch (err) {
      setStatusNotice({ type: 'error', text: err.message || 'Network error saving content.' })
    } finally {
      setIsSaving(false)
    }
  }

  const handleResetToFactory = async () => {
    if (!confirm('Reset all documentation content and team profiles to default factory settings?')) return
    setIsSaving(true)
    try {
      const res = await fetch('/api/docs/content', {
        method: 'POST',
        headers: { 'content-type': 'application/json' },
        body: JSON.stringify({ action: 'RESET_TO_DEFAULTS' }),
      })
      if (res.ok) {
        const json = await res.json()
        if (onUpdateContent) onUpdateContent(json.content)
        if (json.content?.pitchSections) setPitchSections(json.content.pitchSections)
        if (json.content?.teamMembers) setTeamMembers(json.content.teamMembers)
        setStatusNotice({ type: 'success', text: 'Reset to factory content complete.' })
      }
    } catch {
      setStatusNotice({ type: 'error', text: 'Failed to reset content.' })
    } finally {
      setIsSaving(false)
    }
  }

  const handleMoveSection = (fromIdx, toIdx) => {
    if (toIdx < 0 || toIdx >= pitchSections.length) return
    const updated = [...pitchSections]
    const item = updated.splice(fromIdx, 1)[0]
    updated.splice(toIdx, 0, item)
    setPitchSections(updated)
    setSelectedSectionIdx(toIdx)
  }

  const handleUpdateCurrentSection = (field, val) => {
    const updated = [...pitchSections]
    if (updated[selectedSectionIdx]) {
      updated[selectedSectionIdx] = { ...updated[selectedSectionIdx], [field]: val }
      setPitchSections(updated)
    }
  }

  const handleAddMember = () => {
    const newMember = {
      id: `member-${Date.now()}`,
      name: 'New Architect',
      role: 'Staff Engineer',
      email: 'engineer@bizora.app',
      avatar: '',
      initials: 'NA',
      bio: 'Core contributor to Bizora platform.',
      focusAreas: ['Core Systems'],
    }
    setTeamMembers([...teamMembers, newMember])
  }

  const handleRemoveMember = (id) => {
    setTeamMembers(teamMembers.filter((m) => m.id !== id))
  }

  const handleUpdateMember = (idx, field, val) => {
    const updated = [...teamMembers]
    updated[idx] = { ...updated[idx], [field]: val }
    setTeamMembers(updated)
  }

  return (
    <div className="docs-admin-modal-backdrop" onClick={onClose} role="dialog" aria-modal="true">
      <div className="docs-admin-panel" onClick={(e) => e.stopPropagation()}>
        {/* Header */}
        <div className="docs-admin-panel-header">
          <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-2)' }}>
            <Lock size={18} style={{ color: 'var(--color-primary)' }} aria-hidden="true" />
            <h3 style={{ margin: 0, fontSize: 'var(--text-body)', fontWeight: 600 }}>
              Documentation Administration & Publishing Console
            </h3>
          </div>
          <button
            type="button"
            className="docs-mode-tab"
            onClick={onClose}
            aria-label="Close Admin Panel"
            style={{ padding: 4 }}
          >
            <X size={18} aria-hidden="true" />
          </button>
        </div>

        {/* Tab Switcher */}
        <div
          style={{
            display: 'flex',
            gap: 'var(--space-2)',
            padding: 'var(--space-3) var(--space-6)',
            borderBottom: '1px solid var(--color-border)',
            background: 'var(--color-surface-subtle)',
          }}
        >
          <button
            type="button"
            className={`docs-mode-tab ${activeTab === 'visibility' ? 'active' : ''}`}
            onClick={() => setActiveTab('visibility')}
          >
            <Clock size={14} aria-hidden="true" />
            <span>Access Control & Scheduling</span>
          </button>
          <button
            type="button"
            className={`docs-mode-tab ${activeTab === 'content' ? 'active' : ''}`}
            onClick={() => setActiveTab('content')}
          >
            <Edit3 size={14} aria-hidden="true" />
            <span>Section Content & Reordering</span>
          </button>
          <button
            type="button"
            className={`docs-mode-tab ${activeTab === 'team' ? 'active' : ''}`}
            onClick={() => setActiveTab('team')}
          >
            <Users size={14} aria-hidden="true" />
            <span>Team Showcase ({teamMembers.length})</span>
          </button>
        </div>

        {/* Status Notice Banner */}
        {statusNotice && (
          <div
            style={{
              padding: 'var(--space-2) var(--space-6)',
              fontSize: 'var(--text-body-sm)',
              background:
                statusNotice.type === 'success'
                  ? 'var(--color-success-subtle)'
                  : statusNotice.type === 'error'
                    ? 'var(--color-danger-subtle)'
                    : 'var(--color-info-subtle)',
              color:
                statusNotice.type === 'success'
                  ? 'var(--color-success-text)'
                  : statusNotice.type === 'error'
                    ? 'var(--color-danger-text)'
                    : 'var(--color-info-text)',
              borderBottom: '1px solid var(--color-border)',
              display: 'flex',
              alignItems: 'center',
              gap: 'var(--space-2)',
            }}
          >
            {statusNotice.type === 'success' ? <Check size={14} /> : <AlertCircle size={14} />}
            <span>{statusNotice.text}</span>
          </div>
        )}

        {/* Body Tabs */}
        <div className="docs-admin-panel-body">
          {/* TAB 1: VISIBILITY & SCHEDULING */}
          {activeTab === 'visibility' && (
            <>
              {/* Master Visibility Switch */}
              <div
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  padding: 'var(--space-4)',
                  background: 'var(--color-surface-subtle)',
                  border: '1px solid var(--color-border)',
                  borderRadius: 'var(--radius-md)',
                }}
              >
                <div>
                  <strong
                    style={{ fontSize: 'var(--text-body)', color: 'var(--color-text)', display: 'block' }}
                  >
                    Master Documentation Visibility
                  </strong>
                  <span style={{ fontSize: 'var(--text-caption)', color: 'var(--color-text-muted)' }}>
                    When disabled, all public visitors are redirected to the Restricted Showcase page.
                  </span>
                </div>
                <label
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: 'var(--space-2)',
                    cursor: 'pointer',
                    fontWeight: 600,
                  }}
                >
                  <input
                    type="checkbox"
                    checked={enabled}
                    onChange={(e) => setEnabled(e.target.checked)}
                    style={{ width: 18, height: 18, accentColor: 'var(--color-primary)' }}
                  />
                  <span>{enabled ? 'ENABLED (ON)' : 'DISABLED (OFF)'}</span>
                </label>
              </div>

              {/* Override Controls */}
              <div className="docs-form-group">
                <label className="docs-form-label">
                  <span>Publishing Mode & Override Rules</span>
                </label>
                <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-2)' }}>
                  {OVERRIDE_MODES.map((mode) => (
                    <label
                      key={mode.id}
                      style={{
                        display: 'flex',
                        alignItems: 'flex-start',
                        gap: 'var(--space-3)',
                        padding: 'var(--space-3)',
                        border: '1px solid var(--color-border)',
                        borderRadius: 'var(--radius-sm)',
                        background:
                          overrideMode === mode.id ? 'var(--color-primary-subtle)' : 'var(--color-surface)',
                        cursor: 'pointer',
                      }}
                    >
                      <input
                        type="radio"
                        name="overrideMode"
                        value={mode.id}
                        checked={overrideMode === mode.id}
                        onChange={(e) => setOverrideMode(e.target.value)}
                        style={{ marginTop: 2, accentColor: 'var(--color-primary)' }}
                      />
                      <div>
                        <strong
                          style={{
                            fontSize: 'var(--text-body-sm)',
                            color: 'var(--color-text)',
                            display: 'block',
                          }}
                        >
                          {mode.label}
                        </strong>
                        <span style={{ fontSize: 'var(--text-caption)', color: 'var(--color-text-muted)' }}>
                          {mode.description}
                        </span>
                      </div>
                    </label>
                  ))}
                </div>
              </div>

              {/* Quick Presets */}
              <div className="docs-form-group">
                <label className="docs-form-label">
                  <span>Quick Schedule Presets</span>
                </label>
                <div className="docs-preset-btn-grid">
                  {SCHEDULE_PRESETS.map((p) => (
                    <button
                      key={p.id}
                      type="button"
                      className="docs-preset-btn"
                      onClick={() => handleApplyPreset(p)}
                    >
                      {p.label}
                    </button>
                  ))}
                </div>
              </div>

              {/* Scheduled Start & End DateTime */}
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 'var(--space-4)' }}>
                <div className="docs-form-group">
                  <label className="docs-form-label">
                    <span>Showcase Start Date & Time</span>
                  </label>
                  <input
                    type="datetime-local"
                    value={startDate}
                    onChange={(e) => setStartDate(e.target.value)}
                    style={{
                      padding: '8px 12px',
                      borderRadius: 'var(--radius-sm)',
                      border: '1px solid var(--color-border)',
                      background: 'var(--color-surface)',
                      color: 'var(--color-text)',
                      fontFamily: 'var(--font-plex-mono)',
                      fontSize: 'var(--text-body-sm)',
                    }}
                  />
                  <span className="docs-form-help">Timezone: {timezone}</span>
                </div>

                <div className="docs-form-group">
                  <label className="docs-form-label">
                    <span>Showcase End Date & Time</span>
                  </label>
                  <input
                    type="datetime-local"
                    value={endDate}
                    onChange={(e) => setEndDate(e.target.value)}
                    style={{
                      padding: '8px 12px',
                      borderRadius: 'var(--radius-sm)',
                      border: '1px solid var(--color-border)',
                      background: 'var(--color-surface)',
                      color: 'var(--color-text)',
                      fontFamily: 'var(--font-plex-mono)',
                      fontSize: 'var(--text-body-sm)',
                    }}
                  />
                  <span className="docs-form-help">Default: June 14, 2026, 23:59</span>
                </div>
              </div>

              <div className="docs-form-group">
                <label className="docs-form-label">
                  <span>Team Display Heading</span>
                </label>
                <input
                  type="text"
                  value={teamName}
                  onChange={(e) => setTeamName(e.target.value)}
                  style={{
                    padding: '8px 12px',
                    borderRadius: 'var(--radius-sm)',
                    border: '1px solid var(--color-border)',
                    background: 'var(--color-surface)',
                    color: 'var(--color-text)',
                    fontSize: 'var(--text-body-sm)',
                  }}
                />
              </div>
            </>
          )}

          {/* TAB 2: CONTENT & SECTION REORDERING */}
          {activeTab === 'content' && (
            <>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                <label className="docs-form-label">
                  <span>Select Pitch Deck Section to Edit</span>
                </label>
                <div style={{ display: 'flex', gap: 'var(--space-2)' }}>
                  <button
                    type="button"
                    className="docs-mode-tab"
                    onClick={() => handleMoveSection(selectedSectionIdx, selectedSectionIdx - 1)}
                    disabled={selectedSectionIdx === 0}
                    style={{ padding: '4px 8px' }}
                    title="Move section up"
                  >
                    <ArrowUp size={14} /> Move Up
                  </button>
                  <button
                    type="button"
                    className="docs-mode-tab"
                    onClick={() => handleMoveSection(selectedSectionIdx, selectedSectionIdx + 1)}
                    disabled={selectedSectionIdx === pitchSections.length - 1}
                    style={{ padding: '4px 8px' }}
                    title="Move section down"
                  >
                    <ArrowDown size={14} /> Move Down
                  </button>
                </div>
              </div>

              <select
                value={selectedSectionIdx}
                onChange={(e) => setSelectedSectionIdx(Number(e.target.value))}
                style={{
                  padding: '8px 12px',
                  borderRadius: 'var(--radius-sm)',
                  border: '1px solid var(--color-border)',
                  background: 'var(--color-surface)',
                  color: 'var(--color-text)',
                  fontSize: 'var(--text-body-sm)',
                }}
              >
                {pitchSections.map((sec, idx) => (
                  <option key={sec.id} value={idx}>
                    {idx + 1}. {sec.title} ({sec.id})
                  </option>
                ))}
              </select>

              {pitchSections[selectedSectionIdx] && (
                <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-3)' }}>
                  <div className="docs-form-group">
                    <label className="docs-form-label">Section Title</label>
                    <input
                      type="text"
                      value={pitchSections[selectedSectionIdx].title || ''}
                      onChange={(e) => handleUpdateCurrentSection('title', e.target.value)}
                      style={{
                        padding: '8px 12px',
                        borderRadius: 'var(--radius-sm)',
                        border: '1px solid var(--color-border)',
                        background: 'var(--color-surface)',
                        color: 'var(--color-text)',
                      }}
                    />
                  </div>

                  <div className="docs-form-group">
                    <label className="docs-form-label">Section Tagline / Subtitle</label>
                    <input
                      type="text"
                      value={pitchSections[selectedSectionIdx].tagline || ''}
                      onChange={(e) => handleUpdateCurrentSection('tagline', e.target.value)}
                      style={{
                        padding: '8px 12px',
                        borderRadius: 'var(--radius-sm)',
                        border: '1px solid var(--color-border)',
                        background: 'var(--color-surface)',
                        color: 'var(--color-text)',
                      }}
                    />
                  </div>

                  <div className="docs-form-group">
                    <label className="docs-form-label">Section Summary Narrative</label>
                    <textarea
                      rows={4}
                      value={pitchSections[selectedSectionIdx].summary || ''}
                      onChange={(e) => handleUpdateCurrentSection('summary', e.target.value)}
                      style={{
                        padding: '8px 12px',
                        borderRadius: 'var(--radius-sm)',
                        border: '1px solid var(--color-border)',
                        background: 'var(--color-surface)',
                        color: 'var(--color-text)',
                        fontSize: 'var(--text-body-sm)',
                        fontFamily: 'inherit',
                      }}
                    />
                  </div>
                </div>
              )}
            </>
          )}

          {/* TAB 3: TEAM MEMBERS */}
          {activeTab === 'team' && (
            <>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                <span style={{ fontSize: 'var(--text-body-sm)', fontWeight: 600 }}>
                  Manage Team Members List ({teamMembers.length} active)
                </span>
                <button
                  type="button"
                  className="docs-mode-tab active"
                  onClick={handleAddMember}
                  style={{ display: 'inline-flex', alignItems: 'center', gap: 4 }}
                >
                  <Plus size={14} /> Add Member
                </button>
              </div>

              <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-3)' }}>
                {teamMembers.map((member, idx) => (
                  <div
                    key={member.id}
                    style={{
                      background: 'var(--color-surface-subtle)',
                      border: '1px solid var(--color-border)',
                      borderRadius: 'var(--radius-md)',
                      padding: 'var(--space-3) var(--space-4)',
                      display: 'flex',
                      flexDirection: 'column',
                      gap: 'var(--space-2)',
                    }}
                  >
                    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                      <strong>{member.name}</strong>
                      <button
                        type="button"
                        onClick={() => handleRemoveMember(member.id)}
                        style={{
                          background: 'none',
                          border: 'none',
                          color: 'var(--color-danger)',
                          cursor: 'pointer',
                          padding: 4,
                        }}
                        title="Remove member"
                      >
                        <Trash2 size={14} />
                      </button>
                    </div>

                    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 'var(--space-2)' }}>
                      <input
                        type="text"
                        placeholder="Full Name"
                        value={member.name}
                        onChange={(e) => handleUpdateMember(idx, 'name', e.target.value)}
                        style={{
                          padding: '6px 10px',
                          border: '1px solid var(--color-border)',
                          borderRadius: 'var(--radius-sm)',
                          fontSize: 'var(--text-body-sm)',
                        }}
                      />
                      <input
                        type="text"
                        placeholder="Role in Application"
                        value={member.role}
                        onChange={(e) => handleUpdateMember(idx, 'role', e.target.value)}
                        style={{
                          padding: '6px 10px',
                          border: '1px solid var(--color-border)',
                          borderRadius: 'var(--radius-sm)',
                          fontSize: 'var(--text-body-sm)',
                        }}
                      />
                    </div>

                    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 'var(--space-2)' }}>
                      <input
                        type="email"
                        placeholder="Email Address"
                        value={member.email}
                        onChange={(e) => handleUpdateMember(idx, 'email', e.target.value)}
                        style={{
                          padding: '6px 10px',
                          border: '1px solid var(--color-border)',
                          borderRadius: 'var(--radius-sm)',
                          fontSize: 'var(--text-body-sm)',
                        }}
                      />
                      <input
                        type="url"
                        placeholder="Profile Picture URL (auto-resized)"
                        value={member.avatar || ''}
                        onChange={(e) => handleUpdateMember(idx, 'avatar', e.target.value)}
                        style={{
                          padding: '6px 10px',
                          border: '1px solid var(--color-border)',
                          borderRadius: 'var(--radius-sm)',
                          fontSize: 'var(--text-body-sm)',
                        }}
                      />
                    </div>
                  </div>
                ))}
              </div>
            </>
          )}
        </div>

        {/* Footer */}
        <div className="docs-admin-panel-footer">
          <button
            type="button"
            className="docs-mode-tab"
            onClick={handleResetToFactory}
            style={{ marginRight: 'auto', color: 'var(--color-danger-text)' }}
          >
            <RotateCcw size={14} style={{ marginRight: 4 }} />
            Reset to Defaults
          </button>

          <button type="button" className="docs-mode-tab" onClick={onClose}>
            Cancel
          </button>

          {activeTab === 'visibility' ? (
            <button
              type="button"
              className="docs-mode-tab active"
              onClick={handleSaveConfig}
              disabled={isSaving}
              style={{ padding: '8px 20px', fontWeight: 600 }}
            >
              <Save size={14} style={{ marginRight: 6 }} />
              {isSaving ? 'Applying...' : 'Save & Apply Schedule'}
            </button>
          ) : (
            <button
              type="button"
              className="docs-mode-tab active"
              onClick={handleSaveContent}
              disabled={isSaving}
              style={{ padding: '8px 20px', fontWeight: 600 }}
            >
              <Save size={14} style={{ marginRight: 6 }} />
              {isSaving ? 'Publishing...' : 'Publish Content Changes'}
            </button>
          )}
        </div>
      </div>
    </div>
  )
}
