'use client'

import React, { useState, useEffect, useMemo } from 'react'
import Link from 'next/link'
import { useRouter, useSearchParams, usePathname } from 'next/navigation'
import {
  MessageSquare,
  ListOrdered,
  PhoneCall,
  Search,
  User,
  Users,
  Send,
  FileText,
  Clock,
  CheckCircle2,
  AlertTriangle,
  ArrowRight,
  ShieldAlert,
  Sparkles,
  Phone,
  Mail,
  Globe,
  Radio,
  ExternalLink,
  Calendar,
  Layers,
  ChevronRight,
} from 'lucide-react'
import {
  DataTable,
  StatusChip,
  SeverityChip,
  EmptyState,
  UnavailableState,
  SimulatedBadge,
  Button,
  Dialog,
  Drawer,
  Input,
  Field,
  Select,
  Textarea,
  CopyableCode,
  Timeline,
  Banner,
  KpiTile,
  Tabs,
} from '@/components/ui'
import { businessPath, businessApiPath, WRITER_ROLES } from '@/lib/catalog'
import { dateTime, relativeTime, duration, stripUntrusted } from '@/lib/format'
import { clientApi } from '@/lib/clientApi'
import { newIdempotencyKey } from '@/lib/api/idempotency'

const CHANNELS = [
  { id: 'ALL', label: 'All Channels' },
  { id: 'WHATSAPP', label: 'WhatsApp', icon: MessageSquare },
  { id: 'MESSENGER', label: 'Messenger', icon: MessageSquare },
  { id: 'EMAIL', label: 'Email', icon: Mail },
  { id: 'WEB_CHAT', label: 'Web Chat', icon: Globe },
  { id: 'SMS', label: 'SMS', icon: Radio },
]

export default function Support({
  business = {},
  businessId,
  activeTab = 'inbox',
  conversationsData,
  queueData,
  callsData,
}) {
  const router = useRouter()
  const pathname = usePathname()
  const searchParams = useSearchParams()

  const currency = business?.currency || 'BDT'
  const timezone = business?.timezone || 'Asia/Dhaka'
  const canWrite = WRITER_ROLES.has(business?.role)

  // Sub-tabs navigation
  const supportTabs = [
    {
      id: 'inbox',
      label: 'Unified Inbox',
      icon: MessageSquare,
      href: `/business/${businessId}/support/inbox`,
    },
    { id: 'queue', label: 'Support Queue', icon: ListOrdered, href: `/business/${businessId}/support/queue` },
    { id: 'calls', label: 'Calls & Logs', icon: PhoneCall, href: `/business/${businessId}/support/calls` },
  ]

  // ==========================================
  // INBOX STATE
  // ==========================================
  const allConversations =
    conversationsData?.results || (Array.isArray(conversationsData) ? conversationsData : [])
  const [selectedChannel, setSelectedChannel] = useState('ALL')
  const [inboxSearch, setInboxSearch] = useState('')
  const [selectedConvId, setSelectedConvId] = useState(allConversations[0]?.id || null)

  const [convContext, setConvContext] = useState(null)
  const [loadingContext, setLoadingContext] = useState(false)
  const [contextError, setContextError] = useState('')

  // Composer state
  const [composerMode, setComposerMode] = useState('message') // 'message' | 'note'
  const [composerContent, setComposerContent] = useState('')
  const [sendingComposer, setSendingComposer] = useState(false)
  const [composerBanner, setComposerBanner] = useState({ type: '', text: '' })
  const [idempotencyKey, setIdempotencyKey] = useState(newIdempotencyKey())

  // Assign Dialog (D11)
  const [assignModalOpen, setAssignModalOpen] = useState(false)
  const [assigneeType, setAssigneeType] = useState('AGENT')
  const [assigneeId, setAssigneeId] = useState('')
  const [assignReason, setAssignReason] = useState('')
  const [assigning, setAssigning] = useState(false)

  // Handover Dialog (D12)
  const [handoverModalOpen, setHandoverModalOpen] = useState(false)
  const [handoverTarget, setHandoverTarget] = useState('HUMAN')
  const [handoverAssigneeId, setHandoverAssigneeId] = useState('')
  const [handoverReason, setHandoverReason] = useState('')
  const [handoverSummary, setHandoverSummary] = useState('')
  const [handoverError, setHandoverError] = useState('')
  const [handingOver, setHandingOver] = useState(false)

  // Priority Dialog (D17)
  const [priorityModalOpen, setPriorityModalOpen] = useState(false)
  const [selectedPriority, setSelectedPriority] = useState('HIGH')
  const [priorityReason, setPriorityReason] = useState('')
  const [updatingPriority, setUpdatingPriority] = useState(false)

  // Mobile navigation between conversation list & thread
  const [mobileThreadOpen, setMobileThreadOpen] = useState(false)

  // Load conversation context when selected
  useEffect(() => {
    if (!selectedConvId) {
      setConvContext(null)
      return
    }

    setLoadingContext(true)
    setContextError('')

    clientApi(`businesses/${businessId}/conversations/${selectedConvId}/context`)
      .then((data) => {
        setConvContext(data)
      })
      .catch((err) => {
        setContextError(err.message || 'Failed to load conversation context.')
      })
      .finally(() => {
        setLoadingContext(false)
      })
  }, [businessId, selectedConvId])

  // Filter conversations in inbox
  const filteredConversations = useMemo(() => {
    return allConversations.filter((conv) => {
      if (selectedChannel !== 'ALL' && conv.channel !== selectedChannel) return false
      if (inboxSearch) {
        const q = inboxSearch.toLowerCase()
        const custName = conv.customer_display_name || conv.customer?.display_name || ''
        const subject = conv.subject || ''
        const extId = conv.external_conversation_id || ''
        if (
          !custName.toLowerCase().includes(q) &&
          !subject.toLowerCase().includes(q) &&
          !extId.toLowerCase().includes(q)
        ) {
          return false
        }
      }
      return true
    })
  }, [allConversations, selectedChannel, inboxSearch])

  const activeConversation = useMemo(() => {
    return (
      allConversations.find((c) => String(c.id) === String(selectedConvId)) || allConversations[0] || null
    )
  }, [allConversations, selectedConvId])

  // Handle Send Message / Note
  const handleSendDraft = async (e) => {
    e.preventDefault()
    if (!composerContent.trim() || !activeConversation) return

    setSendingComposer(true)
    setComposerBanner({ type: '', text: '' })

    try {
      const endpoint =
        composerMode === 'message' ? `businesses/${businessId}/messages` : `businesses/${businessId}/notes`
      const payload =
        composerMode === 'message'
          ? {
              conversation: activeConversation.id,
              direction: 'OUTBOUND',
              content: composerContent.trim(),
              delivery_status: 'PENDING',
            }
          : {
              conversation: activeConversation.id,
              content: composerContent.trim(),
            }

      await clientApi(endpoint, {
        method: 'POST',
        headers: { 'Idempotency-Key': idempotencyKey },
        body: { data: payload },
      })

      setComposerBanner({
        type: 'success',
        text: composerMode === 'message' ? 'Draft saved — not sent to customer.' : 'Internal note saved.',
      })
      setComposerContent('')
      setIdempotencyKey(newIdempotencyKey())

      // Refresh context
      clientApi(`businesses/${businessId}/conversations/${activeConversation.id}/context`)
        .then((data) => setConvContext(data))
        .catch(() => {})
    } catch (err) {
      setComposerBanner({
        type: 'danger',
        text: err.detail || err.message || 'Failed to save message.',
      })
    } finally {
      setSendingComposer(false)
    }
  }

  // Handle Assign (D11)
  const handleAssignSubmit = async (e) => {
    e.preventDefault()
    if (!activeConversation) return
    setAssigning(true)
    try {
      await clientApi(`businesses/${businessId}/conversations/${activeConversation.id}/assign`, {
        method: 'POST',
        body: {
          assignee_type: assigneeType,
          assignee_id: assigneeId ? parseInt(assigneeId, 10) : null,
          reason: assignReason || undefined,
        },
      })
      setAssignModalOpen(false)
      setAssignReason('')
      router.refresh()
    } catch (err) {
      alert(err.detail || err.message || 'Assignment failed.')
    } finally {
      setAssigning(false)
    }
  }

  // Handle Handover (D12)
  const handleHandoverSubmit = async (e) => {
    e.preventDefault()
    if (!activeConversation) return
    setHandingOver(true)
    setHandoverError('')
    try {
      await clientApi(`businesses/${businessId}/conversations/${activeConversation.id}/handover`, {
        method: 'POST',
        body: {
          target: handoverTarget,
          assignee_id:
            handoverTarget === 'HUMAN' && handoverAssigneeId ? parseInt(handoverAssigneeId, 10) : null,
          reason: handoverReason,
          summary: handoverSummary || undefined,
        },
      })
      setHandoverModalOpen(false)
      setHandoverReason('')
      setHandoverSummary('')
      router.refresh()
    } catch (err) {
      setHandoverError(err.detail || err.message || 'Handover failed.')
    } finally {
      setHandingOver(false)
    }
  }

  // Handle Priority Update (D17)
  const handlePrioritySubmit = async (e) => {
    e.preventDefault()
    if (!activeConversation) return
    setUpdatingPriority(true)
    try {
      await clientApi(`businesses/${businessId}/conversations/${activeConversation.id}/priority`, {
        method: 'POST',
        body: {
          priority: selectedPriority,
          reason: priorityReason || 'Manual priority adjustment',
        },
      })
      setPriorityModalOpen(false)
      setPriorityReason('')
      router.refresh()
    } catch (err) {
      alert(err.detail || err.message || 'Priority update failed.')
    } finally {
      setUpdatingPriority(false)
    }
  }

  // ==========================================
  // QUEUE STATE (D10)
  // ==========================================
  const queueResults = queueData?.results || (Array.isArray(queueData) ? queueData : [])
  const [queuePriorityFilter, setQueuePriorityFilter] = useState('ALL')
  const [queueAssignFilter, setQueueAssignFilter] = useState('all')

  const filteredQueue = useMemo(() => {
    return queueResults.filter((item) => {
      if (queuePriorityFilter !== 'ALL' && item.priority !== queuePriorityFilter) return false
      if (queueAssignFilter === 'unassigned' && item.assigned_to) return false
      return true
    })
  }, [queueResults, queuePriorityFilter, queueAssignFilter])

  // ==========================================
  // CALLS STATE (D23)
  // ==========================================
  const callsResults = callsData?.results || (Array.isArray(callsData) ? callsData : [])
  const [callStatusFilter, setCallStatusFilter] = useState('ALL')
  const [selectedCall, setSelectedCall] = useState(null)
  const [callDrawerOpen, setCallDrawerOpen] = useState(false)

  // Schedule Callback Dialog state (D23)
  const [callbackModalOpen, setCallbackModalOpen] = useState(false)
  const [callbackDateTime, setCallbackDateTime] = useState('')
  const [callbackReason, setCallbackReason] = useState('')
  const [schedulingCallback, setSchedulingCallback] = useState(false)

  // Dialyra Outbound Call state
  const [dialyraCallOpen, setDialyraCallOpen] = useState(false)
  const [dialyraPhone, setDialyraPhone] = useState('')
  const [dialyraCustomerName, setDialyraCustomerName] = useState('')
  const [dialyraOriginateBusy, setDialyraOriginateBusy] = useState(false)
  const [dialyraError, setDialyraError] = useState('')
  const [dialyraSuccess, setDialyraSuccess] = useState('')

  const filteredCalls = useMemo(() => {
    return callsResults.filter((call) => {
      if (callStatusFilter !== 'ALL' && call.status !== callStatusFilter) return false
      return true
    })
  }, [callsResults, callStatusFilter])

  const handleOpenCall = (call) => {
    setSelectedCall(call)
    setCallDrawerOpen(true)
  }

  const handleScheduleCallback = async (e) => {
    e.preventDefault()
    if (!selectedCall || !callbackDateTime) return
    setSchedulingCallback(true)
    try {
      await clientApi(`businesses/${businessId}/callbacks/${selectedCall.id}/schedule`, {
        method: 'POST',
        body: {
          scheduled_at: new Date(callbackDateTime).toISOString(),
        },
      })
      setCallbackModalOpen(false)
      setCallbackDateTime('')
      setCallbackReason('')
      alert('Callback scheduled successfully.')
      router.refresh()
    } catch (err) {
      alert(err.detail || err.message || 'Failed to schedule callback.')
    } finally {
      setSchedulingCallback(false)
    }
  }

  const handleDialyraOriginate = async (e) => {
    e.preventDefault()
    if (!dialyraPhone) return
    setDialyraOriginateBusy(true)
    setDialyraError('')
    setDialyraSuccess('')
    try {
      const res = await clientApi(`businesses/${businessId}/dialyra/calls/originate`, {
        method: 'POST',
        body: {
          phone: dialyraPhone.trim(),
          webhook_variables: dialyraCustomerName ? { customer_name: dialyraCustomerName } : undefined,
        },
      })
      setDialyraSuccess(`Call successfully initiated! Call ID: #${res.call_id}`)
      setDialyraPhone('')
      setDialyraCustomerName('')
      router.refresh()
    } catch (err) {
      setDialyraError(err.message || 'Call origination failed.')
    } finally {
      setDialyraOriginateBusy(false)
    }
  }

  return (
    <div className="workspace-page stack-lg">
      {/* Workspace Tabs */}
      <Tabs tabs={supportTabs} activeTab={activeTab} ariaLabel="Support Workspace Navigation" />

      {/* ============================================================== */}
      {/* TAB 1: UNIFIED INBOX                                          */}
      {/* ============================================================== */}
      {activeTab === 'inbox' && (
        <div className={`inbox-workspace ${mobileThreadOpen ? 'mobile-thread-open' : ''}`}>
          {/* PANE 1: CONVERSATION LIST */}
          <div className="inbox-sidebar">
            <div className="inbox-search-header">
              <Input
                type="search"
                placeholder="Search conversations..."
                value={inboxSearch}
                onChange={(e) => setInboxSearch(e.target.value)}
                icon={Search}
                aria-label="Filter inbox conversations"
              />

              {/* Channel Tabs */}
              <div className="inbox-channel-tabs" role="tablist" aria-label="Channels">
                {CHANNELS.map((ch) => {
                  const isActive = selectedChannel === ch.id
                  return (
                    <button
                      key={ch.id}
                      type="button"
                      role="tab"
                      aria-selected={isActive}
                      onClick={() => setSelectedChannel(ch.id)}
                      className={`badge ${isActive ? 'badge-primary' : 'badge-outline'}`}
                      style={{ cursor: 'pointer', padding: '4px 8px', fontSize: 'var(--text-caption)' }}
                    >
                      {ch.label}
                    </button>
                  )
                })}
              </div>
            </div>

            <div className="inbox-conv-list" role="list" aria-label="Customer conversations">
              {filteredConversations.length > 0 ? (
                filteredConversations.map((conv) => {
                  const isSelected = String(conv.id) === String(selectedConvId)
                  const custName =
                    conv.customer_display_name ||
                    conv.customer?.display_name ||
                    `Customer #${conv.customer?.id || conv.customer || '—'}`

                  return (
                    <div
                      key={conv.id}
                      role="listitem"
                      tabIndex={0}
                      onClick={() => {
                        setSelectedConvId(conv.id)
                        setMobileThreadOpen(true)
                      }}
                      onKeyDown={(e) => {
                        if (e.key === 'Enter' || e.key === ' ') {
                          setSelectedConvId(conv.id)
                          setMobileThreadOpen(true)
                        }
                      }}
                      className={`inbox-conv-item ${isSelected ? 'is-selected' : ''}`}
                    >
                      <div className="inbox-conv-item-top">
                        <span className="font-semibold text-body truncate" style={{ maxWidth: '180px' }}>
                          {custName}
                        </span>
                        <span className="text-caption font-mono text-muted">
                          {conv.started_at ? relativeTime(conv.started_at) : '—'}
                        </span>
                      </div>

                      <div
                        style={{
                          display: 'flex',
                          alignItems: 'center',
                          flexWrap: 'wrap',
                          gap: 'var(--space-2)',
                        }}
                      >
                        <span
                          className="badge badge-outline font-mono text-caption"
                          style={{ padding: '1px 6px' }}
                        >
                          {conv.channel || 'INBOX'}
                        </span>
                        {conv.priority && (
                          <span
                            className="text-caption font-semibold"
                            style={{
                              color:
                                conv.priority === 'URGENT'
                                  ? 'var(--color-danger)'
                                  : conv.priority === 'HIGH'
                                    ? 'var(--color-warning)'
                                    : 'var(--color-text-muted)',
                            }}
                          >
                            {conv.priority}
                          </span>
                        )}
                        <span
                          className="text-caption font-mono text-secondary"
                          style={{ marginLeft: 'auto' }}
                        >
                          {conv.status}
                        </span>
                      </div>

                      <p className="text-caption text-secondary truncate" style={{ margin: 0, marginTop: 2 }}>
                        {conv.subject || 'Direct customer thread'}
                      </p>
                    </div>
                  )
                })
              ) : (
                <div style={{ padding: 'var(--space-4)' }}>
                  <EmptyState
                    title="No conversations found"
                    description="No conversations match your active filter."
                  />
                </div>
              )}
            </div>
          </div>

          {/* PANE 2: ACTIVE THREAD */}
          <div className="inbox-thread">
            {activeConversation ? (
              <>
                {/* Thread Header */}
                <div className="inbox-thread-header">
                  <div
                    style={{ display: 'flex', alignItems: 'center', flexWrap: 'wrap', gap: 'var(--space-2)' }}
                  >
                    {/* Back button on mobile */}
                    <button
                      type="button"
                      className="btn btn-ghost btn-sm"
                      onClick={() => setMobileThreadOpen(false)}
                      style={{ display: 'inline-flex', padding: '4px' }}
                      aria-label="Back to conversations list"
                    >
                      <ChevronRight size={18} style={{ transform: 'rotate(180deg)' }} />
                    </button>

                    <div>
                      <div
                        style={{
                          display: 'flex',
                          alignItems: 'center',
                          flexWrap: 'wrap',
                          gap: 'var(--space-2)',
                        }}
                      >
                        <h2 className="font-semibold text-card" style={{ margin: 0 }}>
                          {activeConversation.customer_display_name ||
                            activeConversation.customer?.display_name ||
                            `Customer #${activeConversation.customer?.id || activeConversation.customer || '—'}`}
                        </h2>
                        <span className="badge badge-outline font-mono text-caption">
                          {activeConversation.channel || 'CHANNEL'}
                        </span>
                        <StatusChip status={activeConversation.status || 'OPEN'} size="sm" />
                      </div>
                      <span className="text-caption text-secondary">
                        Started{' '}
                        {activeConversation.started_at
                          ? dateTime(activeConversation.started_at, timezone)
                          : '—'}
                      </span>
                    </div>
                  </div>

                  {/* Actions Toolbar */}
                  <div
                    style={{ display: 'flex', alignItems: 'center', flexWrap: 'wrap', gap: 'var(--space-2)' }}
                  >
                    <Button
                      variant="secondary"
                      size="sm"
                      icon={User}
                      onClick={() => setAssignModalOpen(true)}
                      disabled={!canWrite}
                      title={!canWrite ? 'Requires Operator role' : 'Assign conversation'}
                    >
                      Assign
                    </Button>
                    <Button
                      variant="secondary"
                      size="sm"
                      icon={ArrowRight}
                      onClick={() => setHandoverModalOpen(true)}
                      disabled={!canWrite}
                      title={!canWrite ? 'Requires Operator role' : 'Hand over to human or AI'}
                    >
                      Handover
                    </Button>
                    <Button
                      variant="secondary"
                      size="sm"
                      icon={AlertTriangle}
                      onClick={() => {
                        setSelectedPriority(activeConversation.priority || 'NORMAL')
                        setPriorityModalOpen(true)
                      }}
                      disabled={!canWrite}
                      title={!canWrite ? 'Requires Operator role' : 'Change priority'}
                    >
                      Priority
                    </Button>
                  </div>
                </div>

                {/* Messages & Events Stream */}
                <div className="inbox-thread-messages">
                  {loadingContext ? (
                    <div
                      style={{ padding: 'var(--space-4)', textAlign: 'center' }}
                      className="text-secondary"
                    >
                      Loading conversation messages...
                    </div>
                  ) : contextError ? (
                    <Banner variant="danger">{contextError}</Banner>
                  ) : convContext?.messages?.results?.length > 0 ? (
                    convContext.messages.results.map((msg) => {
                      const isCustomer = msg.direction === 'INBOUND' || msg.sender_type === 'CUSTOMER'
                      const cleanContent = stripUntrusted(msg.content || '')

                      return (
                        <div key={msg.id} className={`inbox-msg-bubble ${isCustomer ? 'customer' : 'agent'}`}>
                          <div
                            style={{
                              display: 'flex',
                              alignItems: 'center',
                              justifyContent: 'space-between',
                              gap: 'var(--space-2)',
                              marginBottom: 4,
                            }}
                          >
                            <span className="font-semibold text-caption">
                              {isCustomer
                                ? activeConversation.customer_display_name || 'Customer'
                                : msg.sender_name || 'Support Agent'}
                            </span>
                            <span className="font-mono text-caption text-muted">
                              {msg.created_at ? relativeTime(msg.created_at) : '—'}
                            </span>
                          </div>
                          <div style={{ whiteSpace: 'pre-wrap' }}>{cleanContent}</div>
                          {!isCustomer && (
                            <div style={{ textAlign: 'right', marginTop: 4 }}>
                              <span className="text-caption font-mono text-muted">
                                {msg.delivery_status || 'Saved — not sent'}
                              </span>
                            </div>
                          )}
                        </div>
                      )
                    })
                  ) : (
                    <EmptyState
                      title="No messages in thread"
                      description="Compose a customer message below to begin recording support notes."
                    />
                  )}

                  {/* Internal Notes from Context */}
                  {convContext?.internal_notes?.results?.map((note) => (
                    <div key={note.id} className="inbox-note-card">
                      <div
                        style={{
                          display: 'flex',
                          alignItems: 'center',
                          justifyContent: 'space-between',
                          marginBottom: 4,
                        }}
                      >
                        <span
                          className="font-semibold text-caption"
                          style={{ color: 'var(--color-warning)' }}
                        >
                          Internal Staff Note
                        </span>
                        <span className="font-mono text-caption text-muted">
                          {note.created_at ? dateTime(note.created_at, timezone) : '—'}
                        </span>
                      </div>
                      <div className="text-body" style={{ whiteSpace: 'pre-wrap' }}>
                        {note.content}
                      </div>
                    </div>
                  ))}

                  {/* AI Suggested Reply Tile (Calm UnavailableState per spec) */}
                  <div style={{ marginTop: 'var(--space-2)' }}>
                    <UnavailableState
                      owner="AI Intelligence"
                      reason="Automated suggested reply requires an active grounded inference adapter."
                    />
                  </div>
                </div>

                {/* Composer (Honest "Saved — not sent" label) */}
                <form className="inbox-composer-box" onSubmit={handleSendDraft}>
                  {composerBanner.text && (
                    <Banner variant={composerBanner.type}>{composerBanner.text}</Banner>
                  )}

                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                    <div
                      style={{
                        display: 'flex',
                        alignItems: 'center',
                        flexWrap: 'wrap',
                        gap: 'var(--space-2)',
                      }}
                    >
                      <button
                        type="button"
                        onClick={() => setComposerMode('message')}
                        className={`badge ${composerMode === 'message' ? 'badge-primary' : 'badge-outline'}`}
                        style={{ cursor: 'pointer', padding: '4px 8px', fontSize: 'var(--text-caption)' }}
                      >
                        Customer Message
                      </button>
                      <button
                        type="button"
                        onClick={() => setComposerMode('note')}
                        className={`badge ${composerMode === 'note' ? 'badge-primary' : 'badge-outline'}`}
                        style={{ cursor: 'pointer', padding: '4px 8px', fontSize: 'var(--text-caption)' }}
                      >
                        Internal Note
                      </button>
                    </div>

                    <span className="font-mono text-caption text-muted" style={{ fontWeight: 600 }}>
                      Saved — not sent
                    </span>
                  </div>

                  <Textarea
                    placeholder={
                      composerMode === 'message'
                        ? 'Draft message (recorded for omnichannel record, not transmitted)...'
                        : 'Record confidential team note regarding this customer...'
                    }
                    value={composerContent}
                    onChange={(e) => setComposerContent(e.target.value)}
                    rows={3}
                    aria-label="Composer input"
                  />

                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                    <span className="text-caption text-muted">
                      Execution status: <span className="font-mono">SIMULATED / PREPARED</span>
                    </span>
                    <Button
                      type="submit"
                      variant="primary"
                      size="sm"
                      icon={Send}
                      loading={sendingComposer}
                      disabled={!composerContent.trim() || !canWrite}
                      title={!canWrite ? 'Requires Operator role' : 'Save draft record'}
                    >
                      {composerMode === 'message' ? 'Save Draft' : 'Record Note'}
                    </Button>
                  </div>
                </form>
              </>
            ) : (
              <div style={{ padding: 'var(--space-6)' }}>
                <EmptyState
                  title="No conversation selected"
                  description="Choose a conversation from the left panel to read the thread."
                />
              </div>
            )}
          </div>

          {/* PANE 3: CUSTOMER CONTEXT (D18) */}
          <div className="inbox-context">
            <h3 className="section-title">Customer Context</h3>

            {activeConversation?.customer ? (
              <div className="stack-sm">
                <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-3)' }}>
                  <div
                    style={{
                      width: 44,
                      height: 44,
                      borderRadius: '50%',
                      background: 'var(--color-surface-subtle)',
                      border: '1px solid var(--color-border)',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      fontWeight: 600,
                      fontSize: 'var(--text-card)',
                      color: 'var(--color-primary)',
                    }}
                  >
                    {(activeConversation.customer_display_name || 'C').charAt(0).toUpperCase()}
                  </div>
                  <div>
                    <h4 className="font-semibold text-body" style={{ margin: 0 }}>
                      {activeConversation.customer_display_name ||
                        `Customer #${activeConversation.customer?.id || activeConversation.customer}`}
                    </h4>
                    <span className="text-caption font-mono text-muted">
                      ID: {activeConversation.customer?.id || activeConversation.customer}
                    </span>
                  </div>
                </div>

                <div style={{ marginTop: 'var(--space-3)' }}>
                  <Link
                    href={`/business/${businessId}/customers/360?id=${activeConversation.customer?.id || activeConversation.customer}`}
                    className="btn btn-secondary btn-sm"
                    style={{ width: '100%', display: 'inline-flex', justifyContent: 'center' }}
                  >
                    <ExternalLink size={14} style={{ marginRight: 6 }} />
                    View Customer 360
                  </Link>
                </div>

                <div className="divider" style={{ margin: 'var(--space-3) 0' }} />

                <div className="stack-sm">
                  <span className="font-semibold text-caption text-secondary">METADATA &amp; STATUS</span>
                  <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                    <span className="text-caption text-muted">Channel</span>
                    <span className="font-mono text-caption">{activeConversation.channel || '—'}</span>
                  </div>
                  <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                    <span className="text-caption text-muted">Priority</span>
                    <span className="font-mono text-caption font-semibold">
                      {activeConversation.priority || 'NORMAL'}
                    </span>
                  </div>
                  <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                    <span className="text-caption text-muted">Assigned</span>
                    <span className="font-mono text-caption">
                      {activeConversation.assigned_to || 'UNASSIGNED'}
                    </span>
                  </div>
                </div>

                <div className="divider" style={{ margin: 'var(--space-3) 0' }} />

                <div className="stack-sm">
                  <span className="font-semibold text-caption text-secondary">COMPLIANCE &amp; POLICY</span>
                  <UnavailableState
                    owner="Business Memory & Knowledge"
                    reason="Customer policy context registry is unmounted."
                  />
                </div>
              </div>
            ) : (
              <EmptyState
                title="Anonymous Visitor"
                description="This conversation has no linked customer profile record."
              />
            )}
          </div>
        </div>
      )}

      {/* ============================================================== */}
      {/* TAB 2: SUPPORT QUEUE (D10)                                     */}
      {/* ============================================================== */}
      {activeTab === 'queue' && (
        <div className="stack-lg">
          {/* Capabilities Grid (D10 UNAVAILABLE stubs) */}
          <div className="queue-capabilities-grid">
            <UnavailableState
              owner="SLA Monitor"
              reason="Real-time overdue SLA detection engine is unmounted."
            />
            <UnavailableState
              owner="AI Support Agent"
              reason="Automated escalation classifier requires active provider pipeline."
            />
            <UnavailableState
              owner="Business Intelligence"
              reason="Analytical queue throughput aggregation is unavailable."
            />
          </div>

          {/* Queue Filter Bar */}
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
            <div style={{ display: 'flex', alignItems: 'center', flexWrap: 'wrap', gap: 'var(--space-2)' }}>
              <span className="font-semibold text-caption text-secondary">Priority:</span>
              {['ALL', 'URGENT', 'HIGH', 'NORMAL', 'LOW'].map((p) => (
                <button
                  key={p}
                  type="button"
                  onClick={() => setQueuePriorityFilter(p)}
                  className={`badge ${queuePriorityFilter === p ? 'badge-primary' : 'badge-outline'}`}
                  style={{ cursor: 'pointer', padding: '4px 8px', fontSize: 'var(--text-caption)' }}
                >
                  {p}
                </button>
              ))}
            </div>

            <div style={{ display: 'flex', alignItems: 'center', flexWrap: 'wrap', gap: 'var(--space-2)' }}>
              <span className="font-semibold text-caption text-secondary">Assignment:</span>
              <button
                type="button"
                onClick={() => setQueueAssignFilter('all')}
                className={`badge ${queueAssignFilter === 'all' ? 'badge-primary' : 'badge-outline'}`}
                style={{ cursor: 'pointer', padding: '4px 8px', fontSize: 'var(--text-caption)' }}
              >
                All
              </button>
              <button
                type="button"
                onClick={() => setQueueAssignFilter('unassigned')}
                className={`badge ${queueAssignFilter === 'unassigned' ? 'badge-primary' : 'badge-outline'}`}
                style={{ cursor: 'pointer', padding: '4px 8px', fontSize: 'var(--text-caption)' }}
              >
                Unassigned Only
              </button>
            </div>
          </div>

          {/* Queue Table */}
          <div className="surface">
            <DataTable
              columns={[
                {
                  key: 'priority',
                  label: 'Priority',
                  render: (row) => (
                    <span
                      className="font-mono text-caption font-semibold"
                      style={{
                        color:
                          row.priority === 'URGENT'
                            ? 'var(--color-danger)'
                            : row.priority === 'HIGH'
                              ? 'var(--color-warning)'
                              : 'var(--color-text-secondary)',
                      }}
                    >
                      {row.priority || 'NORMAL'}
                    </span>
                  ),
                },
                {
                  key: 'customer',
                  label: 'Customer',
                  render: (row) => (
                    <span className="font-semibold text-body">
                      {row.customer_display_name ||
                        (row.customer ? `Customer #${row.customer.id || row.customer}` : '—')}
                    </span>
                  ),
                },
                {
                  key: 'channel',
                  label: 'Channel',
                  className: 'table-col-priority-low',
                  render: (row) => (
                    <span className="badge badge-outline font-mono text-caption">{row.channel}</span>
                  ),
                },
                {
                  key: 'subject',
                  label: 'Subject / Summary',
                  render: (row) => (
                    <span className="text-body">{row.subject || 'Omnichannel support issue'}</span>
                  ),
                },
                {
                  key: 'started_at',
                  label: 'Started At',
                  className: 'table-col-priority-low',
                  render: (row) => (
                    <span className="font-mono text-caption">
                      {row.started_at ? dateTime(row.started_at, timezone) : '—'}
                    </span>
                  ),
                },
                {
                  key: 'status',
                  label: 'Status',
                  render: (row) => <StatusChip status={row.status} size="sm" />,
                },
                {
                  key: 'actions',
                  label: 'Action',
                  render: (row) => (
                    <Link href={`/business/${businessId}/support/inbox`} className="btn btn-secondary btn-sm">
                      Open in Inbox
                    </Link>
                  ),
                },
              ]}
              rows={filteredQueue}
              businessId={businessId}
              emptyTitle="Queue is clear"
              emptyDescription="No urgent or pending customer cases currently require attention."
              openInDrawer={false}
            />
          </div>
        </div>
      )}

      {/* ============================================================== */}
      {/* TAB 3: CALLS & LOGS (D23)                                      */}
      {/* ============================================================== */}
      {activeTab === 'calls' && (
        <div className="stack-lg">
          {/* Status Filter Bar */}
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
            <div style={{ display: 'flex', alignItems: 'center', flexWrap: 'wrap', gap: 'var(--space-2)' }}>
              <span className="font-semibold text-caption text-secondary">Call Status:</span>
              {['ALL', 'COMPLETED', 'MISSED', 'FAILED', 'SCHEDULED'].map((st) => (
                <button
                  key={st}
                  type="button"
                  onClick={() => setCallStatusFilter(st)}
                  className={`badge ${callStatusFilter === st ? 'badge-primary' : 'badge-outline'}`}
                  style={{ cursor: 'pointer', padding: '4px 8px', fontSize: 'var(--text-caption)' }}
                >
                  {st}
                </button>
              ))}
            </div>

            <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-2)' }}>
              <span className="text-caption text-muted">
                Gateway: <span className="font-mono text-success">Dialyra v3</span>
              </span>
              <Button
                variant="primary"
                size="sm"
                onClick={() => {
                  setDialyraError('')
                  setDialyraSuccess('')
                  setDialyraCallOpen(true)
                }}
              >
                <PhoneCall size={14} style={{ marginRight: '6px' }} />
                Start Call (Dialyra)
              </Button>
            </div>
          </div>

          {/* Calls Table */}
          <div className="surface">
            <DataTable
              columns={[
                {
                  key: 'direction',
                  label: 'Direction',
                  render: (row) => (
                    <span className="badge badge-outline font-mono text-caption">
                      {row.direction || 'INBOUND'}
                    </span>
                  ),
                },
                {
                  key: 'customer',
                  label: 'Customer / Number',
                  render: (row) => (
                    <div>
                      <div className="font-semibold text-body">
                        {row.customer_display_name ||
                          (row.customer
                            ? `Customer #${row.customer.id || row.customer}`
                            : 'Anonymous Caller')}
                      </div>
                      <span className="font-mono text-caption text-muted">
                        {row.caller_number || row.recipient_number || '—'}
                      </span>
                    </div>
                  ),
                },
                {
                  key: 'duration_seconds',
                  label: 'Duration',
                  className: 'table-col-priority-low',
                  render: (row) => (
                    <span className="font-mono text-caption">
                      {row.duration_seconds != null ? duration(row.duration_seconds) : '—'}
                    </span>
                  ),
                },
                {
                  key: 'started_at',
                  label: 'Date & Time',
                  className: 'table-col-priority-low',
                  render: (row) => (
                    <span className="font-mono text-caption">
                      {row.started_at ? dateTime(row.started_at, timezone) : '—'}
                    </span>
                  ),
                },
                {
                  key: 'status',
                  label: 'Status',
                  render: (row) => <StatusChip status={row.status} size="sm" />,
                },
                {
                  key: 'actions',
                  label: 'Action',
                  render: (row) => (
                    <Button variant="secondary" size="sm" onClick={() => handleOpenCall(row)}>
                      View Call
                    </Button>
                  ),
                },
              ]}
              rows={filteredCalls}
              businessId={businessId}
              emptyTitle="No call records"
              emptyDescription="Inbound phone calls and scheduled callbacks will appear here."
              openInDrawer={false}
            />
          </div>
        </div>
      )}

      {/* ============================================================== */}
      {/* CALL DETAIL DRAWER                                             */}
      {/* ============================================================== */}
      <Drawer
        open={callDrawerOpen}
        onClose={() => setCallDrawerOpen(false)}
        title={selectedCall ? `Call #${selectedCall.id} Log` : 'Call Details'}
      >
        {selectedCall && (
          <div className="stack-lg">
            {/* Header info */}
            <div className="surface card-padding stack-sm">
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                <span className="badge badge-outline font-mono text-caption">{selectedCall.direction}</span>
                <StatusChip status={selectedCall.status} />
              </div>

              <div>
                <h3 className="section-title">
                  {selectedCall.customer_display_name ||
                    `Customer #${selectedCall.customer?.id || selectedCall.customer || '—'}`}
                </h3>
                <span className="font-mono text-caption text-secondary">
                  Caller: {selectedCall.caller_number || 'Unknown'} &rarr; Recipient:{' '}
                  {selectedCall.recipient_number || 'Unknown'}
                </span>
              </div>

              <div style={{ display: 'flex', gap: 'var(--space-4)', marginTop: 'var(--space-2)' }}>
                <div>
                  <span className="text-caption text-muted">Duration</span>
                  <div className="font-mono font-semibold text-body">
                    {selectedCall.duration_seconds != null ? duration(selectedCall.duration_seconds) : '—'}
                  </div>
                </div>
                <div>
                  <span className="text-caption text-muted">Started At</span>
                  <div className="font-mono text-caption">
                    {selectedCall.started_at ? dateTime(selectedCall.started_at, timezone) : '—'}
                  </div>
                </div>
              </div>
            </div>

            {/* Audio Recording (Calm UnavailableState per D23) */}
            <div className="stack-sm">
              <h4 className="section-title">Audio Recording</h4>
              <UnavailableState
                owner="Voice & Audio Services"
                reason="Audio recording storage and streaming pipeline is not mounted."
              />
            </div>

            {/* Transcript */}
            <div className="stack-sm">
              <h4 className="section-title">Call Transcript</h4>
              {selectedCall.transcript ? (
                <div className="call-transcript-bubble" style={{ whiteSpace: 'pre-wrap' }}>
                  {stripUntrusted(selectedCall.transcript)}
                </div>
              ) : (
                <EmptyState
                  title="No transcript available"
                  description="Real-time speech-to-text transcript was not recorded for this call."
                />
              )}
            </div>

            {/* Structured Summary */}
            <div className="stack-sm">
              <h4 className="section-title">Summary &amp; Outcomes</h4>
              <p className="text-body" style={{ margin: 0 }}>
                {selectedCall.summary || 'No call summary provided.'}
              </p>
            </div>

            {/* Actions: Schedule Callback & Prepare Outbound Call */}
            <div className="stack-sm">
              <Button
                variant="primary"
                icon={Calendar}
                onClick={() => setCallbackModalOpen(true)}
                disabled={!canWrite}
                title={!canWrite ? 'Requires Operator role' : 'Schedule follow-up callback'}
                style={{ width: '100%' }}
              >
                Schedule Callback
              </Button>

              <div className="surface card-padding" style={{ borderStyle: 'dashed' }}>
                <span className="font-mono text-caption text-muted">
                  Carrier Telephony: <strong>Prepared — not executed</strong>
                </span>
              </div>
            </div>
          </div>
        )}
      </Drawer>

      {/* ============================================================== */}
      {/* DIALOG 1: ASSIGN CONVERSATION (D11)                            */}
      {/* ============================================================== */}
      <Dialog open={assignModalOpen} onClose={() => setAssignModalOpen(false)} title="Assign Support Case">
        <form onSubmit={handleAssignSubmit} className="stack">
          <Field label="Assignee Type" htmlFor="assignee-type">
            <Select id="assignee-type" value={assigneeType} onChange={(e) => setAssigneeType(e.target.value)}>
              <option value="AGENT">Human Support Agent</option>
              <option value="TEAM">Support Team Queue</option>
              <option value="AI">AI Support Worker</option>
              <option value="UNASSIGNED">Unassigned</option>
            </Select>
          </Field>

          {assigneeType === 'AGENT' && (
            <Field label="Agent Member ID" htmlFor="assignee-id" hint="Active team member numeric ID">
              <Input
                id="assignee-id"
                type="number"
                placeholder="e.g. 1"
                value={assigneeId}
                onChange={(e) => setAssigneeId(e.target.value)}
              />
            </Field>
          )}

          <Field
            label="Assignment Reason"
            htmlFor="assign-reason"
            hint="Optional rationale for case routing audit"
          >
            <Input
              id="assign-reason"
              placeholder="e.g. Specialized technical inquiry"
              value={assignReason}
              onChange={(e) => setAssignReason(e.target.value)}
            />
          </Field>

          <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 'var(--space-2)' }}>
            <Button variant="secondary" type="button" onClick={() => setAssignModalOpen(false)}>
              Cancel
            </Button>
            <Button variant="primary" type="submit" loading={assigning}>
              Confirm Assignment
            </Button>
          </div>
        </form>
      </Dialog>

      {/* ============================================================== */}
      {/* DIALOG 2: HANDOVER TO HUMAN OR AI (D12)                        */}
      {/* ============================================================== */}
      <Dialog
        open={handoverModalOpen}
        onClose={() => setHandoverModalOpen(false)}
        title="Hand Over Conversation"
      >
        <form onSubmit={handleHandoverSubmit} className="stack">
          {handoverError && <Banner variant="danger">{handoverError}</Banner>}

          <Banner variant="info">Notice: The customer is not notified automatically of this handover.</Banner>

          <Field label="Handover Target" htmlFor="handover-target">
            <Select
              id="handover-target"
              value={handoverTarget}
              onChange={(e) => setHandoverTarget(e.target.value)}
            >
              <option value="HUMAN">Human Support Agent</option>
              <option value="AI">AI Automated Assistant</option>
            </Select>
          </Field>

          {handoverTarget === 'HUMAN' && (
            <Field
              label="Target Agent User ID"
              htmlFor="handover-agent"
              hint="Numeric user ID of responsible agent"
              required
            >
              <Input
                id="handover-agent"
                type="number"
                placeholder="e.g. 1"
                value={handoverAssigneeId}
                onChange={(e) => setHandoverAssigneeId(e.target.value)}
                required
              />
            </Field>
          )}

          <Field
            label="Handover Reason"
            htmlFor="handover-reason"
            hint="Detailed justification required for audit"
            required
          >
            <Input
              id="handover-reason"
              placeholder="e.g. Escalating complex refund dispute to manager"
              value={handoverReason}
              onChange={(e) => setHandoverReason(e.target.value)}
              required
            />
          </Field>

          <Field
            label="Handover Summary"
            htmlFor="handover-summary"
            hint="Optional synopsis for the next handler"
          >
            <Textarea
              id="handover-summary"
              rows={3}
              placeholder="Brief summary of discussion so far..."
              value={handoverSummary}
              onChange={(e) => setHandoverSummary(e.target.value)}
            />
          </Field>

          <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 'var(--space-2)' }}>
            <Button variant="secondary" type="button" onClick={() => setHandoverModalOpen(false)}>
              Cancel
            </Button>
            <Button variant="primary" type="submit" loading={handingOver}>
              Execute Handover
            </Button>
          </div>
        </form>
      </Dialog>

      {/* ============================================================== */}
      {/* DIALOG 3: UPDATE PRIORITY (D17)                                */}
      {/* ============================================================== */}
      <Dialog
        open={priorityModalOpen}
        onClose={() => setPriorityModalOpen(false)}
        title="Adjust Case Priority"
      >
        <form onSubmit={handlePrioritySubmit} className="stack">
          <Field label="Priority Level" htmlFor="conv-priority">
            <Select
              id="conv-priority"
              value={selectedPriority}
              onChange={(e) => setSelectedPriority(e.target.value)}
            >
              <option value="URGENT">URGENT (Immediate SLA escalation)</option>
              <option value="HIGH">HIGH (Elevated queue priority)</option>
              <option value="NORMAL">NORMAL (Standard queue routing)</option>
              <option value="LOW">LOW (Deferred background resolution)</option>
            </Select>
          </Field>

          <Field
            label="Adjustment Reason"
            htmlFor="priority-reason"
            hint="Reason for SLA priority change"
            required
          >
            <Input
              id="priority-reason"
              placeholder="e.g. VIP client critical fulfillment delay"
              value={priorityReason}
              onChange={(e) => setPriorityReason(e.target.value)}
              required
            />
          </Field>

          <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 'var(--space-2)' }}>
            <Button variant="secondary" type="button" onClick={() => setPriorityModalOpen(false)}>
              Cancel
            </Button>
            <Button variant="primary" type="submit" loading={updatingPriority}>
              Update Priority
            </Button>
          </div>
        </form>
      </Dialog>

      {/* ============================================================== */}
      {/* DIALOG 4: SCHEDULE CALLBACK (D23)                              */}
      {/* ============================================================== */}
      <Dialog
        open={callbackModalOpen}
        onClose={() => setCallbackModalOpen(false)}
        title="Schedule Telephone Callback"
      >
        <form onSubmit={handleScheduleCallback} className="stack">
          <Field
            label="Callback Time"
            htmlFor="callback-datetime"
            hint="Must be a future date and time"
            required
          >
            <Input
              id="callback-datetime"
              type="datetime-local"
              value={callbackDateTime}
              onChange={(e) => setCallbackDateTime(e.target.value)}
              required
            />
          </Field>

          <Field
            label="Reason &amp; Agenda"
            htmlFor="callback-reason"
            hint="Purpose of scheduled telephone outreach"
          >
            <Input
              id="callback-reason"
              placeholder="e.g. Follow-up on bulk order delivery confirmation"
              value={callbackReason}
              onChange={(e) => setCallbackReason(e.target.value)}
            />
          </Field>

          <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 'var(--space-2)' }}>
            <Button variant="secondary" type="button" onClick={() => setCallbackModalOpen(false)}>
              Cancel
            </Button>
            <Button variant="primary" type="submit" loading={schedulingCallback}>
              Confirm Callback
            </Button>
          </div>
        </form>
      </Dialog>

      {/* ============================================================== */}
      {/* DIALOG 5: DIALYRA OUTBOUND CALL                                */}
      {/* ============================================================== */}
      <Dialog
        open={dialyraCallOpen}
        onClose={() => setDialyraCallOpen(false)}
        title="Start Outbound Call (Dialyra v3 Gateway)"
      >
        <form onSubmit={handleDialyraOriginate} className="stack">
          {dialyraError && <Banner tone="danger" title={dialyraError} />}
          {dialyraSuccess && <Banner tone="success" title={dialyraSuccess} />}

          <Field
            label="Recipient Phone Number"
            htmlFor="dialyra-phone"
            hint="E.164 or national phone format"
            required
          >
            <Input
              id="dialyra-phone"
              placeholder="e.g. 01712345678 or +8801712345678"
              value={dialyraPhone}
              onChange={(e) => setDialyraPhone(e.target.value)}
              required
            />
          </Field>

          <Field label="Customer Name" htmlFor="dialyra-customer" hint="Passed as webhook template variable">
            <Input
              id="dialyra-customer"
              placeholder="e.g. Rahim Ahmed"
              value={dialyraCustomerName}
              onChange={(e) => setDialyraCustomerName(e.target.value)}
            />
          </Field>

          <p className="text-caption text-muted">
            The call will be originated through Dialyra Asterisk softswitch and automatically logged in
            Bizora.
          </p>

          <div
            style={{
              display: 'flex',
              justifyContent: 'flex-end',
              gap: 'var(--space-2)',
              marginTop: 'var(--space-2)',
            }}
          >
            <Button variant="secondary" type="button" onClick={() => setDialyraCallOpen(false)}>
              Close
            </Button>
            <Button
              variant="primary"
              type="submit"
              disabled={dialyraOriginateBusy}
              isLoading={dialyraOriginateBusy}
            >
              <PhoneCall size={14} style={{ marginRight: '6px' }} />
              Originate Call
            </Button>
          </div>
        </form>
      </Dialog>
    </div>
  )
}
