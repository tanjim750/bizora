'use client'

import React, { createContext, useContext, useState, useCallback } from 'react'
import { Info, CheckCircle2, AlertTriangle, AlertCircle, X } from 'lucide-react'

const ToastContext = createContext(null)

const TOAST_ICONS = {
  info: Info,
  success: CheckCircle2,
  warning: AlertTriangle,
  danger: AlertCircle,
}

/**
 * Enterprise Toast Notification Provider & System.
 */
export function ToastProvider({ children }) {
  const [toasts, setToasts] = useState([])

  const removeToast = useCallback((id) => {
    setToasts((prev) => prev.filter((t) => t.id !== id))
  }, [])

  const showToast = useCallback(
    ({ message, title, variant = 'info', duration = 4000 }) => {
      const id = `${Date.now()}-${Math.random().toString(36).slice(2, 7)}`
      const newToast = { id, message, title, variant, duration }

      setToasts((prev) => [...prev, newToast])

      if (duration > 0) {
        setTimeout(() => {
          removeToast(id)
        }, duration)
      }

      return id
    },
    [removeToast],
  )

  return (
    <ToastContext.Provider value={{ showToast, removeToast }}>
      {children}
      <div className="toast-container" aria-live="polite" aria-atomic="true">
        {toasts.map((toast) => {
          const Icon = TOAST_ICONS[toast.variant] || Info
          return (
            <div
              key={toast.id}
              role={toast.variant === 'danger' ? 'alert' : 'status'}
              className={`toast-item toast-${toast.variant}`}
            >
              <Icon className="toast-icon" size={16} aria-hidden="true" />
              <div className="toast-content">
                {toast.title && <strong className="toast-title">{toast.title}</strong>}
                <span className="toast-message">{toast.message}</span>
              </div>
              <button
                type="button"
                onClick={() => removeToast(toast.id)}
                className="toast-close"
                aria-label="Close notification"
              >
                <X size={14} aria-hidden="true" />
              </button>
            </div>
          )
        })}
      </div>
    </ToastContext.Provider>
  )
}

export function useToast() {
  const context = useContext(ToastContext)
  if (!context) {
    return {
      showToast: () => {},
      removeToast: () => {},
    }
  }
  return context
}

export default ToastProvider
