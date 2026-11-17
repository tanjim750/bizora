export type ApiVersion = 'v2' | 'v3'

export type DocsNavItem = {
  label: string
  href: (version: ApiVersion) => string
  match: (pathname: string, version: ApiVersion) => boolean
}

export const API_VERSIONS: { label: string; value: ApiVersion }[] = [
  { label: 'v3', value: 'v3' },
  { label: 'v2', value: 'v2' },
]

export const DEFAULT_API_VERSION: ApiVersion = 'v3'

export const DOCS_ROUTES: Record<ApiVersion, string[]> = {
  v2: [
    '/v2',
    '/v2/authentication',
    '/v2/businesses',
    '/v2/access-tokens',
    '/v2/flows',
    '/v2/calls',
    '/v2/tts',
    '/v2/sip-trunks',
    '/v2/audio-assets',
    '/v2/agents-departments',
    '/v2/extensions',
    '/v2/agent-runtime-calls',
    '/v2/billing',
    '/v2/business-webhooks',
    '/v2/authz-policy-matrix',
    '/v2/sip-trunk-realtime-mapping',
    '/v2/api-reference',
    '/v2/guides',
    '/v2/changelog',
  ],
  v3: [
    '/v3',
    '/v3/api-reference',
    '/v3/authentication',
    '/v3/businesses',
    '/v3/access-tokens',
    '/v3/flows',
    '/v3/calls',
    '/v3/tts',
    '/v3/sip-trunks',
    '/v3/runtime-calls',
    '/v3/audio-assets',
    '/v3/agents-departments',
    '/v3/extensions',
    '/v3/agent-runtime-calls',
    '/v3/billing',
    '/v3/business-webhooks',
    '/v3/operations',
    '/v3/guides',
    '/v3/changelog',
  ],
}

export const DOCS_NAV_ITEMS: DocsNavItem[] = [
  {
    label: 'Documentation',
    href: (version) => `/${version}`,
    match: (pathname, version) => pathname === `/${version}`,
  },
  {
    label: 'API Reference',
    href: (version) => `/${version}/api-reference`,
    match: (pathname, version) =>
      pathname.startsWith(`/${version}/api-reference`) ||
      [
        'authentication',
        'businesses',
        'access-tokens',
        'flows',
        'calls',
        'tts',
        'sip-trunks',
        'audio-assets',
        'agents-departments',
        'extensions',
        'agent-runtime-calls',
        'billing',
        'business-webhooks',
        'runtime-calls',
      ].some((slug) => pathname === `/${version}/${slug}`),
  },
  {
    label: 'Changelog',
    href: (version) => `/${version}/changelog`,
    match: (pathname, version) => pathname.startsWith(`/${version}/changelog`),
  },
]

export const PLATFORM_LINKS = [
  { label: 'Dialyra', href: 'https://dialyra.com' },
  { label: 'Dashboard', href: 'https://dashboard.dialyra.com' },
  { label: 'GitHub', href: 'https://github.com/dialyra' },
]

export function getVersionFromPath(pathname: string): ApiVersion {
  const match = pathname.match(/^\/(v2|v3)(?=\/|$)/)

  return (match?.[1] as ApiVersion | undefined) ?? DEFAULT_API_VERSION
}

export function hasVersionInPath(pathname: string): boolean {
  return /^\/(v2|v3)(?=\/|$)/.test(pathname)
}

export function getDocsHomePath(version: ApiVersion): string {
  return `/${version}`
}

export function getPathForVersion(pathname: string, nextVersion: ApiVersion): string {
  const currentVersion = getVersionFromPath(pathname)
  const candidate = pathname.replace(`/${currentVersion}`, `/${nextVersion}`)

  if (DOCS_ROUTES[nextVersion].includes(candidate)) {
    return candidate
  }

  return getDocsHomePath(nextVersion)
}
