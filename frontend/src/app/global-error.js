'use client'

import React, { useEffect } from 'react'

export default function GlobalError({ error, retry, reset }) {
  useEffect(() => {
    // Log unexpected fatal app error
    console.error('Fatal application error in RootLayout:', error)
  }, [error])

  const handleRetry = () => {
    if (typeof retry === 'function') {
      retry()
    } else if (typeof reset === 'function') {
      reset()
    } else {
      window.location.reload()
    }
  }

  return (
    <html lang="en">
      <head>
        <title>Application Error · Bizora</title>
        <meta name="viewport" content="width=device-width, initial-scale=1" />
        <style>{`
          :root {
            color-scheme: light dark;
            --bg: #0F172A;
            --surface: #1E293B;
            --text: #F1F5F9;
            --text-muted: #94A3B8;
            --primary: #3B82F6;
            --primary-hover: #2563EB;
            --danger: #EF4444;
            --border: #334155;
          }
          * { box-sizing: border-box; margin: 0; padding: 0; }
          body {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            background: var(--bg);
            color: var(--text);
            min-height: 100vh;
            display: grid;
            place-items: center;
            padding: 24px;
          }
          .error-card {
            background: var(--surface);
            border: 1px solid var(--border);
            border-radius: 12px;
            max-width: 480px;
            width: 100%;
            padding: 32px;
            display: flex;
            flex-direction: column;
            gap: 16px;
            box-shadow: 0 10px 25px rgba(0,0,0,0.5);
          }
          .brand-mark {
            display: inline-grid;
            place-items: center;
            width: 36px;
            height: 36px;
            border-radius: 8px;
            background: var(--primary);
            color: #fff;
            font-size: 20px;
            font-weight: 700;
          }
          h1 {
            font-size: 22px;
            font-weight: 700;
            color: var(--text);
          }
          p {
            font-size: 14px;
            line-height: 1.5;
            color: var(--text-muted);
          }
          .error-digest {
            font-family: monospace;
            font-size: 12px;
            background: #0B1220;
            padding: 8px 12px;
            border-radius: 6px;
            border: 1px solid var(--border);
            color: #94A3B8;
            word-break: break-all;
          }
          .btn-group {
            display: flex;
            gap: 12px;
            margin-top: 8px;
          }
          .btn {
            display: inline-flex;
            align-items: center;
            justify-content: center;
            padding: 10px 16px;
            border-radius: 8px;
            font-size: 14px;
            font-weight: 600;
            cursor: pointer;
            text-decoration: none;
            border: 0;
            transition: background 150ms ease;
          }
          .btn-primary {
            background: var(--primary);
            color: #FFFFFF;
          }
          .btn-primary:hover {
            background: var(--primary-hover);
          }
          .btn-secondary {
            background: transparent;
            color: var(--text);
            border: 1px solid var(--border);
          }
          .btn-secondary:hover {
            background: rgba(255,255,255,0.05);
          }
        `}</style>
      </head>
      <body>
        <main className="error-card" role="alert">
          <div className="brand-mark" aria-hidden="true">
            B
          </div>
          <h1>System Encountered an Error</h1>
          <p>
            An unrecoverable error occurred while initializing the application. Your data has not been
            compromised.
          </p>
          {error?.digest && <div className="error-digest">Reference code: {error.digest}</div>}
          <div className="btn-group">
            <button type="button" onClick={handleRetry} className="btn btn-primary">
              Reload application
            </button>
            <a href="/login" className="btn btn-secondary">
              Return to sign-in
            </a>
          </div>
        </main>
      </body>
    </html>
  )
}
