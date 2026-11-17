import type { ReactNode } from 'react'
import {
  DOCS_NAV_ITEMS,
  PLATFORM_LINKS,
  getVersionFromPath,
} from '../config/docsConfig'

type FooterProps = {
  pathname?: string
}

function FooterLinkList({ title, children }: { title: string; children: ReactNode }) {
  return (
    <div className="footer-link-group">
      <h2>{title}</h2>
      <ul>{children}</ul>
    </div>
  )
}

export function Footer({ pathname = window.location.pathname }: FooterProps) {
  const currentYear = new Date().getFullYear()
  const activeVersion = getVersionFromPath(pathname)

  return (
    <footer className="docs-footer">
      <div className="docs-footer-main">
        <div className="footer-brand">
          <a className="brand-link" href={`/${activeVersion}`} aria-label="Dialyra Docs home">
            <span className="dialyra-mark" aria-hidden="true">
              <span />
            </span>
            <span className="brand-title">Dialyra</span>
          </a>
          <p>Build, automate, and manage intelligent customer calls with Dialyra.</p>
          <span className="footer-version">Viewing API {activeVersion}</span>
        </div>

        <FooterLinkList title="Documentation">
          {DOCS_NAV_ITEMS.map((item) => (
            <li key={item.label}>
              <a href={item.href(activeVersion)}>{item.label}</a>
            </li>
          ))}
        </FooterLinkList>

        <FooterLinkList title="Platform">
          {PLATFORM_LINKS.map((item) => (
            <li key={item.label}>
              <a href={item.href}>{item.label}</a>
            </li>
          ))}
        </FooterLinkList>
      </div>

      <div className="docs-footer-bottom">
        <p>© {currentYear} Dialyra. All rights reserved.</p>
      </div>
    </footer>
  )
}
