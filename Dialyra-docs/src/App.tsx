import { useEffect } from 'react'
import { Footer } from './components/Footer'
import { Header } from './components/Header'
import { EndpointSchema } from './components/EndpointSchema'
import { DEFAULT_API_VERSION, getDocsHomePath, getVersionFromPath, hasVersionInPath } from './config/docsConfig'
import { DOCS_PAGES, getDocsPage, type DocsPage } from './config/docsPages'
import './App.css'

const sidebarGroups: DocsPage['group'][] = ['Start', 'API Reference', 'Operations']

function App() {
  const pathname = window.location.pathname
  const activeVersion = getVersionFromPath(pathname)
  const activePage = getDocsPage(pathname, activeVersion)
  const pages = DOCS_PAGES[activeVersion].filter((page) => !page.hidden)

  useEffect(() => {
    if (!hasVersionInPath(window.location.pathname)) {
      window.location.replace(getDocsHomePath(DEFAULT_API_VERSION))
    }
  }, [])

  return (
    <>
      <Header pathname={pathname} />

      <main className="docs-layout">
        <aside className="docs-sidebar" aria-label={`${activeVersion} documentation sections`}>
          <span className="sidebar-version">API {activeVersion}</span>
          {sidebarGroups.map((group) => {
            const groupPages = pages.filter((page) => page.group === group && group !== 'Guides')

            if (groupPages.length === 0) return null

            return (
              <div className="sidebar-group" key={group}>
                <h2>{group}</h2>
                {groupPages.map((page) => (
                  <a
                    key={page.href}
                    href={page.href}
                    aria-current={page.href === activePage.href ? 'page' : undefined}
                    data-active={page.href === activePage.href}
                  >
                    {page.title}
                  </a>
                ))}
              </div>
            )
          })}
        </aside>

        <article className="docs-content">
          <span className="eyebrow">Dialyra API {activeVersion}</span>
          <h1>{activePage.title}</h1>
          <p>{activePage.description}</p>

          {activePage.status ? <div className="status-pill">{activePage.status}</div> : null}

          <section className="doc-section" aria-labelledby="highlights-heading">
            <h2 id="highlights-heading">Highlights</h2>
            <ul className="highlight-list">
              {activePage.highlights.map((highlight) => (
                <li key={highlight}>{highlight}</li>
              ))}
            </ul>
          </section>

          {activePage.lifecycle ? (
            <section className="doc-section" aria-labelledby="lifecycle-heading">
              <h2 id="lifecycle-heading">{activePage.lifecycle.title}</h2>
              <ol className="cycle-list">
                {activePage.lifecycle.steps.map((step) => (
                  <li key={step}>{step}</li>
                ))}
              </ol>
            </section>
          ) : null}

          {activePage.endpoints ? (
            <section className="doc-section" aria-labelledby="endpoints-heading">
              <h2 id="endpoints-heading">Endpoints</h2>
              <div className="endpoint-list">
                {activePage.endpoints.map((endpoint) => (
                  <div className="endpoint-row" key={`${endpoint.method}-${endpoint.path}`}>
                    <div className="endpoint-summary">
                      <span className="method-badge" data-method={endpoint.method}>
                        {endpoint.method}
                      </span>
                      <code>{endpoint.path}</code>
                      <p>{endpoint.description}</p>
                    </div>
                    <EndpointSchema endpoint={endpoint} version={activeVersion} />
                  </div>
                ))}
              </div>
            </section>
          ) : null}
        </article>
      </main>

      <Footer pathname={pathname} />
    </>
  )
}

export default App
