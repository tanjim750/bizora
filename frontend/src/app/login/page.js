'use client'

import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import { clientApi } from '@/lib/clientApi'

export default function LoginPage() {
  const router = useRouter()
  const [ready, setReady] = useState(false)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')

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
      </main>
    </div>
  )
}
