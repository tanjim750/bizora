'use client'

import { Suspense, useEffect, useState } from 'react'
import { useRouter, useSearchParams } from 'next/navigation'
import { clientApi } from '@/lib/clientApi'
import { isSafeRelativePath } from '@/lib/api'
import { Banner } from '@/components/ui/Banner'
import { Field } from '@/components/ui/Field'
import { Input } from '@/components/ui/Input'
import { Button } from '@/components/ui/Button'
import { Skeleton } from '@/components/ui/Skeleton'
import { BizoraLogo } from '@/components/ui/BizoraLogo'

function LoginForm() {
  const router = useRouter()
  const searchParams = useSearchParams()
  const [ready, setReady] = useState(false)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [demoActive, setDemoActive] = useState(false)

  const nextParam = searchParams.get('next')
  const redirectTarget = nextParam && isSafeRelativePath(nextParam) ? nextParam : '/workspace'

  useEffect(() => {
    // The demo sign-in exists only in local development with an explicit server-side flag.
    fetch('/api/demo-login', { cache: 'no-store' })
      .then((response) => (response.ok ? response.json() : null))
      .then((data) => setDemoActive(Boolean(data?.enabled)))
      .catch(() => setDemoActive(false))
  }, [])

  useEffect(() => {
    clientApi('frontend/session')
      .then((session) => {
        if (session.authenticated) router.replace(redirectTarget)
        else setReady(true)
      })
      .catch(() => {
        setError('The backend is unavailable. Start Django and try again.')
        setReady(true)
      })
  }, [router, redirectTarget])

  async function handleSignIn(event) {
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
      router.replace(redirectTarget)
      router.refresh()
    } catch (failure) {
      setError(failure.message || 'Invalid username or password.')
      setBusy(false)
    }
  }

  async function handleDemoSignIn() {
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
      router.replace(redirectTarget)
      router.refresh()
    } catch (failure) {
      setError(failure.message)
      setBusy(false)
    }
  }

  return (
    <main className="auth-card">
      <p className="auth-context">Operations workspace</p>
      <h1>Welcome back</h1>
      <p>Sign in to work with your authorized businesses.</p>

      {error && (
        <div style={{ marginBottom: 'var(--space-4)' }}>
          <Banner variant="danger" title={error} />
        </div>
      )}

      <form onSubmit={handleSignIn}>
        <Field id="username" label="Username" htmlFor="username">
          <Input
            id="username"
            name="username"
            autoComplete="username"
            required
            disabled={!ready || busy}
            placeholder="e.g. operator"
          />
        </Field>

        <Field id="password" label="Password" htmlFor="password">
          <Input
            id="password"
            name="password"
            type="password"
            autoComplete="current-password"
            required
            disabled={!ready || busy}
            placeholder="••••••••"
          />
        </Field>

        <Button
          variant="primary"
          type="submit"
          disabled={!ready || busy}
          isLoading={busy}
          style={{ width: '100%', marginTop: 'var(--space-2)' }}
        >
          {busy ? 'Signing in…' : 'Sign in'}
        </Button>
      </form>

      {demoActive && (
        <div style={{ marginTop: 'var(--space-4)' }}>
          <Button
            variant="secondary"
            type="button"
            className="demo-login"
            onClick={handleDemoSignIn}
            disabled={!ready || busy}
            style={{ width: '100%' }}
          >
            Continue as demo owner
          </Button>
          <p className="text-caption text-muted" style={{ textAlign: 'center', marginTop: 'var(--space-2)' }}>
            Development only. Signs in as the local demo user.
          </p>
        </div>
      )}
    </main>
  )
}

function LoginFormFallback() {
  return (
    <div className="auth-card">
      <Skeleton variant="text" width="40%" height={14} />
      <Skeleton variant="text" width="70%" height={26} style={{ marginTop: 'var(--space-2)' }} />
      <Skeleton variant="rectangular" width="100%" height={40} style={{ marginTop: 'var(--space-4)' }} />
      <Skeleton variant="rectangular" width="100%" height={40} style={{ marginTop: 'var(--space-4)' }} />
      <Skeleton variant="rectangular" width="100%" height={40} style={{ marginTop: 'var(--space-6)' }} />
    </div>
  )
}

export default function LoginPage() {
  return (
    <div className="auth-screen">
      <header className="auth-brand">
        <BizoraLogo size={36} showText={true} />
      </header>
      <Suspense fallback={<LoginFormFallback />}>
        <LoginForm />
      </Suspense>
    </div>
  )
}
