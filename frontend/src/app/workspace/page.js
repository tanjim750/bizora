import Link from 'next/link'
import { redirect } from 'next/navigation'
import { getSession } from '@/lib/serverApi'
import { businessPath } from '@/lib/catalog'

export default async function WorkspacePage() {
  const session = await getSession()
  if (!session.authenticated) redirect('/login')
  return (
    <div className="workspace-screen">
      <header className="workspace-top">
        <strong>
          <span className="brand-mark">B</span> bizora<span className="brand-dot">.</span>
        </strong>
        <span>{session.username}</span>
      </header>
      <main className="workspace-content">
        <p className="page-context">Workspaces</p>
        <h1>Choose a business</h1>
        <p className="lead">Open a workspace to review its records and operational work.</p>
        <div className="workspace-grid">
          {session.businesses.map((business) => (
            <Link key={business.id} className="workspace-card" href={businessPath(business.id)}>
              <span className="workspace-monogram">{business.name.slice(0, 1).toUpperCase()}</span>
              <span>
                <strong>{business.name}</strong>
                <small>
                  {business.role.toLowerCase()} access · {business.currency}
                </small>
              </span>
              <span aria-hidden="true">→</span>
            </Link>
          ))}
        </div>
        {session.businesses.length === 0 && (
          <div className="empty-state">
            <h2>No active business access</h2>
            <p>Ask a business owner to grant you membership.</p>
          </div>
        )}
      </main>
    </div>
  )
}
