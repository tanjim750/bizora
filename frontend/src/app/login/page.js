'use client'

import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import { clientApi } from '@/lib/clientApi'

export default function LoginPage() {
  const router = useRouter()
  const [ready, setReady] = useState(false)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [demoEnabled, setDemoEnabled] = useState(false)

  useEffect(() => {
    // The demo sign-in exists only in local development with an explicit server-side flag.
    fetch('/api/demo-login', { cache: 'no-store' })
      .then((response) => (response.ok ? response.json() : null))
      .then((data) => setDemoEnabled(Boolean(data?.enabled)))
      .catch(() => setDemoEnabled(false))
  }, [])

  useEffect(() => {
    clientApi('frontend/session')
      .then((session) => {
        if (session.authenticated) router.replace('/workspace')
        else setReady(true)
      })
      .catch(() => {
        setError('The backend is unavailable. Start Django and try again.')
        setReady(true)
      })
  }, [router])

  async function signIn(event) {
    event.preventDefault()
    setBusy(true)
    setError('')
    const form = new FormData(event.currentTarget)
    try {
      await clientApi('frontend/login', {
        method: 'POST',
        body: {
          username: form.get('username'),
          password: form.get('password'),
        },
      })
      router.replace('/workspace')
      router.refresh()
    } catch (failure) {
      setError(failure.message)
      setBusy(false)
    }
  }

  async function demoSignIn() {
    setBusy(true)
    setError('')
    try {
      const response = await fetch('/api/demo-login', {
        method: 'POST',
        credentials: 'same-origin',
        cache: 'no-store',
      })
      const data = await response.json().catch(() => null)
      if (!response.ok) throw new Error(data?.detail || `Request failed (${response.status})`)
      router.replace('/workspace')
      router.refresh()
    } catch (failure) {
      setError(failure.message)
      setBusy(false)
    }
  }

  return (
    <div className="auth-screen">
      <header className="auth-brand">
        <span className="brand-mark">B</span> bizora<span className="brand-dot">.</span>
      </header>
      <main className="auth-card">
        <p className="auth-context">Operations workspace</p>
        <h1>Welcome back</h1>
        <p>Sign in to work with your authorized businesses.</p>
        {error && (
          <div className="alert alert-danger" role="alert">
            {error}
          </div>
        )}
        <form onSubmit={signIn}>
          <label htmlFor="username">Username</label>
          <input id="username" name="username" autoComplete="username" required disabled={!ready || busy} />
          <label htmlFor="password">Password</label>
          <input
            id="password"
            name="password"
            type="password"
            autoComplete="current-password"
            required
            disabled={!ready || busy}
          />
          <button className="button button-primary" type="submit" disabled={!ready || busy}>
            {busy ? 'Signing in…' : 'Sign in'}
          </button>
        </form>
        {demoEnabled && (
          <>
            <button
              className="button button-secondary demo-login"
              type="button"
              onClick={demoSignIn}
              disabled={!ready || busy}
            >
              Continue as demo owner
            </button>
            <p className="muted">Development only. Signs in as the local demo user.</p>
          </>
        )}
      </main>
    </div>
  )
}
