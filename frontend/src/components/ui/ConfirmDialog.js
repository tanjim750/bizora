'use client'

import React from 'react'
import { AlertCircle, AlertTriangle, HelpCircle } from 'lucide-react'
import { Dialog } from './Dialog.js'
import { Button } from './Button.js'

/**
 * Enterprise confirmation dialog for destructive or state-changing actions.
 */
export function ConfirmDialog({
  isOpen,
  onClose,
  onConfirm,
  title = 'Confirm action',
  message,
  confirmLabel = 'Confirm',
  cancelLabel = 'Cancel',
  variant = 'primary', // 'primary' | 'danger'
  isLoading = false,
  children,
  className = '',
}) {
  const Icon = variant === 'danger' ? AlertCircle : HelpCircle

  const footer = (
    <div className="button-row" style={{ justifyContent: 'flex-end', width: '100%' }}>
      <Button variant="ghost" onClick={onClose} disabled={isLoading}>
        {cancelLabel}
      </Button>
      <Button variant={variant === 'danger' ? 'danger' : 'primary'} onClick={onConfirm} isLoading={isLoading}>
        {confirmLabel}
      </Button>
    </div>
  )

  return (
    <Dialog
      isOpen={isOpen}
      onClose={onClose}
      title={title}
      footer={footer}
      maxWidth="460px"
      className={`confirm-dialog ${className}`.trim()}
    >
      <div className="confirm-dialog-content">
        <div className={`confirm-icon-wrap confirm-icon-${variant}`} aria-hidden="true">
          <Icon size={24} />
        </div>
        <div className="confirm-text-wrap">
          {message && <p className="confirm-message">{message}</p>}
          {children}
        </div>
      </div>
    </Dialog>
  )
}

export default ConfirmDialog
