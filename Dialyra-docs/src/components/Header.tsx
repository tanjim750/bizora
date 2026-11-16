import { useMemo, useState } from 'react'
import {
  API_VERSIONS,
  DOCS_NAV_ITEMS,
  type ApiVersion,
  getDocsHomePath,
  getPathForVersion,
  getVersionFromPath,
} from '../config/docsConfig'

type HeaderProps = {
  pathname?: string
}

function SearchIcon() {
  return (
    <svg className="search-icon" viewBox="0 0 20 20" aria-hidden="true">
      <path
        d="m14.2 14.2 3.05 3.05M8.85 15.15a6.3 6.3 0 1 1 0-12.6 6.3 6.3 0 0 1 0 12.6Z"
        fill="none"
        stroke="currentColor"
        strokeLinecap="round"
        strokeWidth="1.7"
      />
    </svg>
  )
}

export function Header({ pathname = window.location.pathname }: HeaderProps) {
  const [isMobileOpen, setIsMobileOpen] = useState(false)
  const activeVersion = useMemo(() => getVersionFromPath(pathname), [pathname])

  function handleVersionChange(nextVersion: ApiVersion) {
    if (nextVersion === activeVersion) return

    window.location.assign(getPathForVersion(window.location.pathname, nextVersion))
  }

  return (
    <header className="docs-header">
      <div className="docs-header-inner">
        <a className="brand-link" href={getDocsHomePath(activeVersion)} aria-label="Dialyra Docs home">
          <span className="dialyra-mark" aria-hidden="true">
            <span />
          </span>
          <span className="brand-title">Dialyra Docs</span>
        </a>

        <nav className="desktop-nav" aria-label="Documentation">
          {DOCS_NAV_ITEMS.map((item) => {
            const isActive = item.match(pathname, activeVersion)

            return (
              <a
                key={item.label}
                className="nav-link"
                href={item.href(activeVersion)}
                aria-current={isActive ? 'page' : undefined}
                data-active={isActive}
              >
                {item.label}
              </a>
            )
          })}
        </nav>

        <div className="header-actions">
          <label className="version-switcher">
            <span className="version-label">API</span>
            <select
              aria-label="Select API version"
              value={activeVersion}
              onChange={(event) => handleVersionChange(event.target.value as ApiVersion)}
            >
              {API_VERSIONS.map((version) => (
                <option key={version.value} value={version.value}>
                  {version.label}
                </option>
              ))}
            </select>
          </label>

          <button className="search-trigger" type="button" aria-label="Search documentation">
            <SearchIcon />
            <span>Search docs</span>
            <kbd>/</kbd>
          </button>

          <div className="future-actions" aria-hidden="true" />

          <button
            className="mobile-menu-button"
            type="button"
            aria-label="Toggle documentation navigation"
            aria-controls="mobile-docs-nav"
            aria-expanded={isMobileOpen}
            onClick={() => setIsMobileOpen((current) => !current)}
          >
            <span />
            <span />
          </button>
        </div>
      </div>

      <div className="mobile-search">
        <button className="search-trigger" type="button" aria-label="Search documentation">
          <SearchIcon />
          <span>Search docs</span>
          <kbd>/</kbd>
        </button>
      </div>

      <nav
        id="mobile-docs-nav"
        className="mobile-nav"
        aria-label="Documentation"
        data-open={isMobileOpen}
      >
        {DOCS_NAV_ITEMS.map((item) => {
          const isActive = item.match(pathname, activeVersion)

          return (
            <a
              key={item.label}
              className="nav-link"
              href={item.href(activeVersion)}
              aria-current={isActive ? 'page' : undefined}
              data-active={isActive}
            >
              {item.label}
            </a>
          )
        })}
      </nav>
    </header>
  )
}
