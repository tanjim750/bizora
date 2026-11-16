import type { ApiVersion } from './docsConfig'

export type Endpoint = {
  method: 'GET' | 'POST' | 'PUT' | 'DELETE'
  path: string
  description: string
  details?: {
    title: string
    description?: string
    items?: string[]
    code?: string
    language?: string
  }[]
}

export type DocsPage = {
  title: string
  description: string
  href: string
  group: 'Start' | 'API Reference' | 'Guides' | 'Operations'
  hidden?: boolean
  status?: string
  highlights: string[]
  lifecycle?: {
    title: string
    steps: string[]
  }
  endpoints?: Endpoint[]
}

export const DOCS_PAGES: Record<ApiVersion, DocsPage[]> = {
  v2: [
    {
      title: 'Overview',
      description:
        'Base URL, authentication headers, common errors, and the main v2 product areas.',
      href: '/v2',
      group: 'Start',
      status: 'Base URL: /api/v2',
      highlights: [
        'JWT endpoints use Authorization: Bearer <jwt_token>.',
        'Runtime endpoints accept X-Dialyra-Access-Token or Authorization bearer access tokens.',
        'Errors return a minimal JSON object with an error string unless an endpoint documents more detail.',
      ],
      endpoints: [{ method: 'GET', path: '/api/v2/health', description: 'Health check.' }],
    },
    {
      title: 'Authentication',
      description:
        'Register users, issue tokens, manage sessions, and reset passwords.',
      href: '/v2/authentication',
      group: 'API Reference',
      highlights: [
        'Register accepts full_name, email, password, and role only.',
        'Password change and reset endpoints require client-provided idempotency keys.',
        'Forgot-password links are generated server-side and raw tokens are never stored in plaintext.',
      ],
      endpoints: [
        { method: 'POST', path: '/api/v2/auth/register', description: 'Register a new user.' },
        { method: 'POST', path: '/api/v2/auth/login', description: 'Issue access and refresh tokens.' },
        { method: 'POST', path: '/api/v2/auth/refresh', description: 'Refresh an access token.' },
        { method: 'POST', path: '/api/v2/auth/logout', description: 'Revoke a refresh token.' },
        { method: 'GET', path: '/api/v2/auth/me', description: 'Return the current user and business.' },
        { method: 'POST', path: '/api/v2/auth/users', description: 'Create users and optional memberships.' },
        { method: 'GET', path: '/api/v2/auth/users', description: 'List users by actor scope.' },
        { method: 'PUT', path: '/api/v2/auth/users', description: 'Update the authenticated user profile.' },
        { method: 'PUT', path: '/api/v2/auth/users/password', description: 'Change own password.' },
        {
          method: 'POST',
          path: '/api/v2/auth/forgot-password',
          description: 'Consume a reset token and set a new password.',
        },
      ],
    },
    {
      title: 'API Reference',
      description:
        'Browse the v2 API by product area. Each section summarizes the contract from the request and response schema.',
      href: '/v2/api-reference',
      group: 'Start',
      status: 'Base URL: /api/v2',
      highlights: [
        'Authentication, businesses, access tokens, flows, calls, TTS, SIP trunks, audio assets, agents, billing, and webhooks are available in v2.',
        'Use JWT auth for dashboard and management endpoints.',
        'Use runtime access tokens for call runtime endpoints when appropriate.',
      ],
    },
    {
      title: 'Businesses',
      description:
        'Create businesses, manage settings, inbound call configuration, members, ownership, and global SIP.',
      href: '/v2/businesses',
      group: 'API Reference',
      highlights: [
        'Business settings and inbound call config are business-scoped resources.',
        'Membership endpoints separate workspace access from account-level user state.',
        'Ownership transfer and global SIP controls are explicit actions.',
      ],
      endpoints: [
        { method: 'POST', path: '/api/v2/businesses', description: 'Create a business.' },
        { method: 'GET', path: '/api/v2/businesses', description: 'List visible businesses.' },
        { method: 'GET', path: '/api/v2/businesses/:business_id', description: 'Get one business.' },
        { method: 'PUT', path: '/api/v2/businesses/:business_id', description: 'Update a business.' },
        { method: 'DELETE', path: '/api/v2/businesses/:business_id', description: 'Delete a business.' },
        {
          method: 'GET',
          path: '/api/v2/businesses/:business_id/settings',
          description: 'Read business settings.',
        },
        {
          method: 'PUT',
          path: '/api/v2/businesses/:business_id/settings',
          description: 'Update business settings.',
        },
        {
          method: 'GET',
          path: '/api/v2/businesses/:business_id/inbound-call-config',
          description: 'Read inbound call configuration.',
        },
        {
          method: 'POST',
          path: '/api/v2/businesses/:business_id/inbound-call-config',
          description: 'Create inbound call configuration.',
        },
        {
          method: 'PUT',
          path: '/api/v2/businesses/:business_id/inbound-call-config',
          description: 'Update inbound call configuration.',
        },
        {
          method: 'POST',
          path: '/api/v2/businesses/:business_id/members',
          description: 'Add a business member.',
        },
        {
          method: 'GET',
          path: '/api/v2/businesses/:business_id/members',
          description: 'List business members.',
        },
        {
          method: 'POST',
          path: '/api/v2/businesses/:business_id/transfer-ownership',
          description: 'Transfer business ownership.',
        },
      ],
    },
    {
      title: 'Access Tokens',
      description: 'Create, list, inspect, revoke, and delete runtime access tokens.',
      href: '/v2/access-tokens',
      group: 'API Reference',
      highlights: [
        'Runtime access tokens can authenticate public runtime endpoints.',
        'Scopes define whether a token can originate calls, read events, or access webhooks.',
        'Revocation is separate from deletion so token lifecycle can be audited.',
      ],
      endpoints: [
        { method: 'POST', path: '/api/v2/access-tokens', description: 'Create an access token.' },
        { method: 'GET', path: '/api/v2/access-tokens', description: 'List access tokens.' },
        { method: 'GET', path: '/api/v2/access-tokens/:token_id', description: 'Inspect one token.' },
        { method: 'POST', path: '/api/v2/access-tokens/:token_id/revoke', description: 'Revoke a token.' },
        { method: 'DELETE', path: '/api/v2/access-tokens/:token_id', description: 'Delete a token.' },
      ],
    },
    {
      title: 'Flows',
      description: 'Create draft call flows, publish runtime versions, and manage nodes and edges.',
      href: '/v2/flows',
      group: 'API Reference',
      highlights: [
        'Flows support draft CRUD plus create-and-publish for one-step rollout.',
        'Validation and publish endpoints separate authoring from runtime deployment.',
        'Nodes and edges are managed independently for visual builders and automation tooling.',
      ],
      endpoints: [
        { method: 'POST', path: '/api/v2/flows', description: 'Create a draft flow.' },
        { method: 'POST', path: '/api/v2/flows/create-and-publish', description: 'Create and publish.' },
        { method: 'GET', path: '/api/v2/flows', description: 'List flows.' },
        { method: 'GET', path: '/api/v2/flows/:id', description: 'Get a flow.' },
        { method: 'PUT', path: '/api/v2/flows/:id', description: 'Update a flow.' },
        { method: 'DELETE', path: '/api/v2/flows/:id', description: 'Delete a flow.' },
        { method: 'POST', path: '/api/v2/flows/:id/validate', description: 'Validate a flow.' },
        { method: 'POST', path: '/api/v2/flows/:id/publish', description: 'Publish a flow.' },
        { method: 'POST', path: '/api/v2/flows/:id/duplicate', description: 'Duplicate a flow.' },
        { method: 'POST', path: '/api/v2/flows/:flow_id/nodes', description: 'Create a node.' },
        { method: 'POST', path: '/api/v2/flows/:flow_id/edges', description: 'Create an edge.' },
      ],
    },
    {
      title: 'Calls',
      description:
        'Originate, retry, hang up, inspect call events, query history, and observe webhook jobs.',
      href: '/v2/calls',
      group: 'API Reference',
      highlights: [
        'Public call creation and runtime call origination are documented separately.',
        'Call history includes events, DTMF, and audit surfaces for operations teams.',
        'Webhook job endpoints expose retry, health, summary, and per-call delivery state.',
      ],
      endpoints: [
        { method: 'POST', path: '/api/v2/call', description: 'Create a public call.' },
        { method: 'POST', path: '/api/v2/runtime/calls/originate', description: 'Originate a runtime call.' },
        { method: 'POST', path: '/api/v2/runtime/calls/:call_id/hangup', description: 'Hang up a call.' },
        { method: 'POST', path: '/api/v2/runtime/calls/:call_id/retry', description: 'Retry a call.' },
        { method: 'GET', path: '/api/v2/runtime/calls/events', description: 'List runtime call events.' },
        { method: 'GET', path: '/api/v2/calls', description: 'List calls.' },
        { method: 'GET', path: '/api/v2/calls/:call_id', description: 'Get a call.' },
        { method: 'GET', path: '/api/v2/calls/history', description: 'Query call history.' },
        { method: 'GET', path: '/api/v2/calls/:call_id/events', description: 'List call events.' },
        { method: 'GET', path: '/api/v2/calls/dtmf', description: 'List DTMF events.' },
        { method: 'GET', path: '/api/v2/calls/audit', description: 'List call audit records.' },
      ],
    },
    {
      title: 'TTS',
      description: 'Generate text-to-speech audio, list generated assets, voices, and languages.',
      href: '/v2/tts',
      group: 'API Reference',
      highlights: [
        'TTS generation creates managed audio records.',
        'Voice and language catalogs are queryable from the API.',
        'Worker health exposes operational readiness for generation jobs.',
      ],
      endpoints: [
        { method: 'POST', path: '/api/v2/tts/generate', description: 'Generate TTS audio.' },
        { method: 'GET', path: '/api/v2/tts', description: 'List TTS assets.' },
        { method: 'GET', path: '/api/v2/tts/:id', description: 'Get one TTS asset.' },
        { method: 'DELETE', path: '/api/v2/tts/:id', description: 'Delete a TTS asset.' },
        { method: 'GET', path: '/api/v2/tts/voices', description: 'List voices.' },
        { method: 'GET', path: '/api/v2/tts/languages', description: 'List languages.' },
        { method: 'GET', path: '/api/v2/tts/worker/health', description: 'Check worker health.' },
      ],
    },
    {
      title: 'SIP Trunks',
      description: 'Provision SIP trunks, test connectivity, apply realtime sync, and inspect status.',
      href: '/v2/sip-trunks',
      group: 'API Reference',
      hidden: true,
      highlights: [
        'Registration trunks require username, password, host, and port.',
        'IP trunks require host and port, with optional userpass auth.',
        'Apply, rollback, status, and realtime health endpoints support Asterisk operations.',
      ],
      endpoints: [
        { method: 'POST', path: '/api/v2/sip-trunks', description: 'Create a SIP trunk.' },
        { method: 'GET', path: '/api/v2/sip-trunks', description: 'List SIP trunks.' },
        { method: 'GET', path: '/api/v2/sip-trunks/:trunk_id', description: 'Get one trunk.' },
        { method: 'PUT', path: '/api/v2/sip-trunks/:trunk_id', description: 'Update a trunk.' },
        {
          method: 'PUT',
          path: '/api/v2/sip-trunks/:trunk_id/global-access',
          description: 'Toggle global access.',
        },
        { method: 'DELETE', path: '/api/v2/sip-trunks/:trunk_id', description: 'Delete a trunk.' },
        { method: 'POST', path: '/api/v2/sip-trunks/:trunk_id/test', description: 'Test a trunk.' },
        { method: 'POST', path: '/api/v2/sip-trunks/:trunk_id/reload', description: 'Reload trunk runtime.' },
        { method: 'POST', path: '/api/v2/sip-trunks/:trunk_id/apply', description: 'Apply realtime rows.' },
        { method: 'POST', path: '/api/v2/sip-trunks/:trunk_id/rollback', description: 'Rollback realtime rows.' },
        { method: 'GET', path: '/api/v2/sip-trunks/:trunk_id/status', description: 'Read apply status.' },
      ],
    },
    {
      title: 'Audio Assets',
      description: 'Upload, stream, download, update, delete, sync, and test audio assets.',
      href: '/v2/audio-assets',
      group: 'API Reference',
      highlights: [
        'Audio assets can be uploaded and managed independently from flows.',
        'Streaming and download endpoints support playback and asset inspection.',
        'Asterisk sync and playback testing help validate telephony readiness.',
      ],
      endpoints: [
        { method: 'POST', path: '/api/v2/audio-assets/upload', description: 'Upload an audio asset.' },
        { method: 'GET', path: '/api/v2/audio-assets', description: 'List audio assets.' },
        { method: 'GET', path: '/api/v2/audio-assets/:asset_id', description: 'Get one asset.' },
        { method: 'PUT', path: '/api/v2/audio-assets/:asset_id', description: 'Update metadata.' },
        { method: 'GET', path: '/api/v2/audio-assets/:asset_id/stream', description: 'Stream an asset.' },
        { method: 'GET', path: '/api/v2/audio-assets/:asset_id/download', description: 'Download an asset.' },
        { method: 'DELETE', path: '/api/v2/audio-assets/:asset_id', description: 'Delete an asset.' },
        {
          method: 'POST',
          path: '/api/v2/audio-assets/:asset_id/sync-to-asterisk',
          description: 'Sync asset to Asterisk.',
        },
        {
          method: 'POST',
          path: '/api/v2/audio-assets/:asset_id/test-playback',
          description: 'Test playback.',
        },
      ],
    },
    {
      title: 'Agents and Departments',
      description:
        'Admin APIs for live agents, departments, schedules, and transfer sessions.',
      href: '/v2/agents-departments',
      group: 'API Reference',
      highlights: [
        'Agents represent people or users who can receive transferred conversations.',
        'Department APIs include agents, schedules, dry runs, and live status.',
        'Transfer sessions expose connected transfer lifecycle and call handoff state.',
      ],
      endpoints: [
        { method: 'POST', path: '/api/v2/agents', description: 'Create an agent.' },
        { method: 'GET', path: '/api/v2/agents', description: 'List agents.' },
        { method: 'GET', path: '/api/v2/agents/:agent_id', description: 'Get an agent.' },
        { method: 'PUT', path: '/api/v2/agents/:agent_id', description: 'Update an agent.' },
        { method: 'DELETE', path: '/api/v2/agents/:agent_id', description: 'Delete an agent.' },
        {
          method: 'POST',
          path: '/api/v2/agents/:agent_id/availability',
          description: 'Update agent availability.',
        },
        { method: 'POST', path: '/api/v2/departments', description: 'Create a department.' },
        { method: 'GET', path: '/api/v2/departments', description: 'List departments.' },
        {
          method: 'GET',
          path: '/api/v2/departments/:department_id',
          description: 'Get a department.',
        },
        {
          method: 'PUT',
          path: '/api/v2/departments/:department_id',
          description: 'Update a department.',
        },
        {
          method: 'DELETE',
          path: '/api/v2/departments/:department_id',
          description: 'Delete a department.',
        },
        {
          method: 'GET',
          path: '/api/v2/departments/:department_id/agents',
          description: 'List department agents.',
        },
        {
          method: 'POST',
          path: '/api/v2/departments/:department_id/agents',
          description: 'Add department agents.',
        },
        {
          method: 'PUT',
          path: '/api/v2/departments/:department_id/agents',
          description: 'Replace department agents.',
        },
        {
          method: 'DELETE',
          path: '/api/v2/departments/:department_id/agents/:agent_id',
          description: 'Remove a department agent.',
        },
        {
          method: 'GET',
          path: '/api/v2/departments/:department_id/schedule',
          description: 'Read department schedule.',
        },
        {
          method: 'POST',
          path: '/api/v2/departments/:department_id/schedule',
          description: 'Create department schedule.',
        },
        {
          method: 'PUT',
          path: '/api/v2/departments/:department_id/schedule',
          description: 'Update department schedule.',
        },
        {
          method: 'POST',
          path: '/api/v2/departments/:department_id/schedule/:mode',
          description: 'Set schedule mode.',
        },
        {
          method: 'POST',
          path: '/api/v2/departments/:department_id/dry-run',
          description: 'Run department routing dry run.',
        },
        {
          method: 'GET',
          path: '/api/v2/departments/:department_id/live',
          description: 'Read live department state.',
        },
        {
          method: 'GET',
          path: '/api/v2/transfer-sessions',
          description: 'List transfer sessions.',
        },
        {
          method: 'GET',
          path: '/api/v2/transfer-sessions/:transfer_session_id',
          description: 'Get a transfer session.',
        },
      ],
    },
    {
      title: 'Agent Runtime Calls',
      description:
        'Originate agent-side calls from a local extension to another extension or to an external number.',
      href: '/v2/agent-runtime-calls',
      group: 'API Reference',
      highlights: [
        'Use this endpoint when a human agent starts a call from an assigned local extension.',
        'Extension targets connect one local extension to another local extension.',
        'External number targets place the call through a selected outbound route.',
      ],
      lifecycle: {
        title: 'Purpose',
        steps: [
          'Resolve the caller by business_id and from_extension.',
          'For extension targets, validate that from_extension and to are different.',
          'For external number targets, include sip_trunk_id when the call should use a specific outbound route.',
          'Dialyra resolves display extensions to managed runtime identities before origination.',
          'A successful response returns call tracking IDs, selected route metadata, timeout, auth type, and provider response.',
        ],
      },
      endpoints: [
        {
          method: 'POST',
          path: '/api/v2/agents/calls/originate',
          description: 'Originate an agent-side runtime call from a local extension.',
        },
      ],
    },
    {
      title: 'Extensions',
      description:
        'Create and manage agent phone extensions that connect human agents to Dialyra transfer workflows.',
      href: '/v2/extensions',
      group: 'API Reference',
      highlights: [
        'Extensions are the human-facing numbers agents use for receiving transferred calls.',
        'Dialyra derives the real tenant-safe login identity from the business prefix and extension.',
        'Extensions can be created, listed, bound to agents, reassigned, disabled, or deleted.',
      ],
      lifecycle: {
        title: 'Purpose',
        steps: [
          'Create an extension when an agent needs a reachable phone identity for call transfers.',
          'Optionally bind the extension to an active agent user in the same business.',
          'Use primary extension flags to choose which endpoint receives calls first for an agent.',
          'Transfer or rebind extensions when staff changes roles or ownership of a phone identity changes.',
          'Deactivate or delete extension mappings when an agent should no longer receive routed calls.',
        ],
      },
      endpoints: [
        {
          method: 'POST',
          path: '/api/v2/agents/extensions',
          description: 'Create or update an agent phone extension.',
        },
        {
          method: 'GET',
          path: '/api/v2/agents/extensions',
          description: 'List extension bindings for a business.',
        },
        {
          method: 'GET',
          path: '/api/v2/agents/extensions/:id',
          description: 'Get one extension binding.',
        },
        {
          method: 'PUT',
          path: '/api/v2/agents/:agent_id/extensions',
          description: 'Assign an existing extension to an agent.',
        },
        {
          method: 'POST',
          path: '/api/v2/agents/extensions/:id/bind',
          description: 'Bind an existing extension row to another agent user.',
        },
        {
          method: 'PUT',
          path: '/api/v2/agents/extensions/:id',
          description: 'Enable or disable an extension binding.',
        },
        {
          method: 'DELETE',
          path: '/api/v2/agents/extensions/:id',
          description: 'Soft-delete an extension binding and deprovision its phone identity.',
        },
      ],
    },
    {
      title: 'Billing',
      description:
        'Self-service billing visibility for the authenticated user and their visible billing account.',
      href: '/v2/billing',
      group: 'API Reference',
      highlights: [
        'Personal billing endpoints are controlled by BILLING_USER_VIEW_ALLOWED_ROLES.',
        'A business member sees the business owner wallet used for call billing.',
        'Management wallet endpoints remain excluded from public docs.',
      ],
      endpoints: [
        {
          method: 'GET',
          path: '/api/v2/billing/me/credits',
          description: 'Return the authenticated user visible billing account and available credit.',
        },
      ],
    },
    {
      title: 'Business Webhooks',
      description:
        'Configure business event webhooks, verify signatures, inspect deliveries, and retry failures.',
      href: '/v2/business-webhooks',
      group: 'API Reference',
      highlights: [
        'Webhook requests use HMAC signatures for verification.',
        'Delivery payloads include event metadata and business context.',
        'Delivery history, retry, pause, resume, test, and health endpoints are part of the contract.',
      ],
      endpoints: [
        { method: 'GET', path: '/api/v2/business-webhooks', description: 'List webhooks.' },
        { method: 'POST', path: '/api/v2/business-webhooks', description: 'Create a webhook.' },
        { method: 'GET', path: '/api/v2/business-webhooks/:id', description: 'Get a webhook.' },
        { method: 'PUT', path: '/api/v2/business-webhooks/:id', description: 'Update a webhook.' },
        { method: 'DELETE', path: '/api/v2/business-webhooks/:id', description: 'Delete a webhook.' },
        { method: 'POST', path: '/api/v2/business-webhooks/:id/pause', description: 'Pause delivery.' },
        { method: 'POST', path: '/api/v2/business-webhooks/:id/resume', description: 'Resume delivery.' },
        { method: 'POST', path: '/api/v2/business-webhooks/:id/test', description: 'Send a test event.' },
        {
          method: 'GET',
          path: '/api/v2/business-webhooks/:id/deliveries',
          description: 'List deliveries.',
        },
        {
          method: 'POST',
          path: '/api/v2/business-webhooks/deliveries/:delivery_id/retry',
          description: 'Retry a delivery.',
        },
      ],
    },
    {
      title: 'Authorization Matrix',
      description: 'Role and membership policy guidance for v2 account and business operations.',
      href: '/v2/authz-policy-matrix',
      group: 'Guides',
      highlights: [
        'Superusers manage platform-wide account-level operations.',
        'Stuff users are scoped to owned businesses and can create general users for those businesses.',
        'General users operate through business memberships such as admin, manager, agent, and viewer.',
      ],
    },
    {
      title: 'Guides',
      description: 'Implementation notes for building secure, reliable v2 integrations.',
      href: '/v2/guides',
      group: 'Start',
      highlights: [
        'Use the authorization matrix when deciding which role or membership can perform an action.',
        'Keep generated tokens, reset links, and customer data out of logs and client-side storage.',
        'Use idempotency keys for sensitive retryable actions such as password changes.',
      ],
    },
    {
      title: 'SIP Realtime Mapping',
      description: 'Implementation contract for mapping Dialyra SIP trunks into Asterisk realtime tables.',
      href: '/v2/sip-trunk-realtime-mapping',
      group: 'Guides',
      highlights: [
        'Realtime IDs are deterministic and stable for idempotent upserts.',
        'Registration trunks write endpoint, AOR, auth, and registration rows.',
        'IP trunks write endpoint, AOR, and identify rows, with optional auth.',
      ],
    },
    {
      title: 'Changelog',
      description: 'Release notes and compatibility notes for the v2 API.',
      href: '/v2/changelog',
      group: 'Start',
      highlights: [
        'Some v2 endpoints are deprecated where v3-compatible replacements are available.',
        'Deprecated: POST /api/v2/runtime/calls/originate. Use POST /api/v3/runtime/calls/originate for new runtime call origination.',
        'v2 remains available for existing integrations, but new work should prefer v3 routes when documented.',
      ],
    },
  ],
  v3: [
    {
      title: 'Overview',
      description:
        'Dialyra API v3 focuses on softphone-style SIP trunk setup, runtime origination, and business-scoped rollout controls.',
      href: '/v3',
      group: 'Start',
      status: 'Base URL: /api/v3',
      highlights: [
        'v3 SIP trunk behavior is gated by SIP_TRUNK_V3_ENABLED.',
        'Business allowlists can be controlled with SIP_TRUNK_V3_ALLOWED_BUSINESS_IDS.',
        'Remaining public modules are listed under v3 with schemas inherited from the v2 contract.',
      ],
      endpoints: [
        { method: 'GET', path: '/api/v3/businesses', description: 'List businesses for a user.' },
        { method: 'POST', path: '/api/v3/sip-trunks', description: 'Create a v3 SIP trunk.' },
        {
          method: 'POST',
          path: '/api/v3/runtime/calls/originate',
          description: 'Originate a runtime call with access-token auth.',
        },
      ],
    },
    {
      title: 'API Reference',
      description: 'Browse the v3 API by product area and inspect source-backed schemas.',
      href: '/v3/api-reference',
      group: 'API Reference',
      highlights: [
        'v3 management endpoints use JWT auth and business permissions.',
        'Runtime call origination uses business access-token auth with calls:originate scope.',
        'SIP trunk status endpoints report realtime row presence, registration state, and originate eligibility.',
        'Public endpoints not redefined by the v3 schema are shown with the /api/v3 prefix and v2-compatible schemas.',
      ],
    },
    {
      title: 'Businesses',
      description:
        'Return businesses bound to a user through active workspace membership or direct ownership.',
      href: '/v3/businesses',
      group: 'API Reference',
      highlights: [
        'If user_id is omitted, the endpoint follows normal business list behavior for the authenticated actor.',
        'Non-management callers can only query their own user_id.',
        'Responses include SIP rollout fields such as allow_global_sip_fallback and sip_login_prefix.',
      ],
      endpoints: [
        {
          method: 'GET',
          path: '/api/v3/businesses',
          description: 'List businesses for the requested or authenticated user.',
        },
      ],
    },
    {
      title: 'SIP Trunks',
      description:
        'Create, list, update, test, apply, rollback, reload, and inspect v3 SIP trunks.',
      href: '/v3/sip-trunks',
      group: 'API Reference',
      hidden: true,
      highlights: [
        'v3 trunks use normal SIP account/provider fields instead of provider_profile.',
        'Supported trunk modes are registration and ip_auth.',
        'enable_inbound is explicit and valid only for business-scoped trunks.',
      ],
      endpoints: [
        { method: 'POST', path: '/api/v3/sip-trunks', description: 'Create a v3 SIP trunk.' },
        { method: 'GET', path: '/api/v3/sip-trunks', description: 'List v3 SIP trunks.' },
        { method: 'GET', path: '/api/v3/sip-trunks/profiles', description: 'List SIP trunk profiles.' },
        { method: 'GET', path: '/api/v3/sip-trunks/:id', description: 'Get one SIP trunk.' },
        { method: 'PUT', path: '/api/v3/sip-trunks/:id', description: 'Update one SIP trunk.' },
        { method: 'DELETE', path: '/api/v3/sip-trunks/:id', description: 'Delete one SIP trunk.' },
        { method: 'POST', path: '/api/v3/sip-trunks/:id/test', description: 'Test SIP trunk connectivity.' },
        {
          method: 'GET',
          path: '/api/v3/sip-trunks/:id/status',
          description: 'Read database, realtime, readiness, and suggested-fix status.',
        },
        {
          method: 'POST',
          path: '/api/v3/sip-trunks/:id/reload',
          description: 'Reload and resync a trunk, optionally enabling inbound mapping.',
        },
        { method: 'POST', path: '/api/v3/sip-trunks/:id/apply', description: 'Apply realtime rows.' },
        { method: 'POST', path: '/api/v3/sip-trunks/:id/rollback', description: 'Rollback realtime rows.' },
        { method: 'GET', path: '/api/v3/sip-trunks/drift', description: 'Inspect SIP trunk drift.' },
      ],
    },
    {
      title: 'Runtime Calls',
      description:
        'Start outbound calls for the authenticated access-token business using v3 trunk selection.',
      href: '/v3/runtime-calls',
      group: 'API Reference',
      highlights: [
        'Requires a business access token with calls:originate scope.',
        'webhook_variables supports up to 100 keys and a 16 KB JSON payload.',
        'If sip_trunk_id is omitted, Dialyra selects the least-busy ready business trunk, with optional global fallback.',
      ],
      lifecycle: {
        title: 'Full Request and Response Cycle',
        steps: [
          'Authenticate with a business access token using X-Dialyra-Access-Token or Authorization: Bearer. JWT bearer tokens are not accepted for this runtime endpoint.',
          'Send POST /api/v3/runtime/calls/originate with phone and optional sip_trunk_id, flow_id, campaign_id, campaign_flow_id, and webhook_variables.',
          'Dialyra validates webhook_variables as an object with at most 100 keys, 64 characters per key, A-Za-z0-9_ key names, no reserved system variable overrides, and a maximum JSON payload size of 16 KB.',
          'If sip_trunk_id is provided, Dialyra verifies that the trunk belongs to the business or is an allowed global trunk. If omitted, Dialyra selects the least-busy ready business trunk, then optionally a ready global fallback trunk.',
          'Trunk readiness and capacity are checked before origination. Global trunks using global_access.version=v2 also enforce the matched allocation limit.',
          'Billing can reserve credit before paid work starts. If billing enforcement blocks the call, the endpoint returns 402 with insufficient-credit details.',
          'On success, Dialyra starts the outbound call and returns call identity, selected trunk and flow metadata, capacity counters, billing reservation details, auth_type=access_token, api_version_used=v3, and validation mode.',
          'Common failures include 400 for validation errors, 409 when the selected trunk is not ready, 409 when no SIP trunk is available, 402 for insufficient credit, and 502 for AMI connectivity errors.',
        ],
      },
      endpoints: [
        {
          method: 'POST',
          path: '/api/v3/runtime/calls/originate',
          description: 'Originate an outbound runtime call.',
          details: [
            {
              title: 'Authentication',
              description:
                'Runtime call originate uses business access-token auth with the calls:originate scope. JWT bearer tokens are not accepted on this endpoint.',
              code: `X-Dialyra-Access-Token: <token>

Authorization: Bearer <token>`,
            },
            {
              title: 'Request',
              description:
                'Provide the destination phone number and optionally pin the call to a SIP trunk or flow. webhook_variables are passed into flow and webhook templates.',
              items: [
                'phone is required.',
                'sip_trunk_id is optional. If omitted, Dialyra selects a ready trunk.',
                'flow_id, campaign_id, and campaign_flow_id are optional routing inputs.',
                'webhook_variables must be an object with at most 100 keys and a 16 KB JSON payload limit.',
              ],
              code: `{
  "phone": "01631596697",
  "sip_trunk_id": 20,
  "flow_id": 7,
  "campaign_id": null,
  "campaign_flow_id": null,
  "webhook_variables": {
    "customer_name": "Rahim",
    "invoice_id": "INV-1001"
  }
}`,
            },
            {
              title: 'Successful Response',
              description:
                'A successful response includes call identity, selected trunk and flow metadata, active call counters, billing reservation state, and v3 validation metadata.',
              code: `{
  "status": "initiated",
  "phone": "01631596697",
  "business_id": 1,
  "call_log_uuid": "3abaf575-5980-4db2-a2c3-1338ec44a4ee",
  "call_session_id": 170,
  "action_id": "102bae32-7661-4161-95e0-bd0b9d535af4",
  "sip_trunk_id": 20,
  "sip_endpoint": "dialyra_b1_t20_trizync_ep",
  "selected_by": "requested",
  "selected_flow_id": 7,
  "selected_flow_version_id": 12,
  "flow_selected_by": "explicit_flow_id",
  "active_calls_before": 0,
  "max_concurrent_calls": 50,
  "business_active_calls_before": 0,
  "business_max_concurrent_calls": 0,
  "system_active_calls_before": 0,
  "system_max_concurrent_calls": 0,
  "billing": {
    "status": "reserved",
    "reservation_key": "call-session-170",
    "reserved_amount": "2.000000"
  },
  "auth_type": "access_token",
  "response": "Response: Success...",
  "api_version_used": "v3",
  "validation_bypassed": false,
  "validation_mode": "strict"
}`,
            },
            {
              title: 'Global Allocation Metadata',
              description:
                'When v2 global allocation is used, the response also includes allocation scope and remaining capacity details.',
              code: `{
  "global_access_version": "v2",
  "global_allocation_scope": "business",
  "global_allocation_owner_id": 1,
  "global_allocation_active_calls_before": 0,
  "global_allocation_max_concurrent_calls": 1,
  "global_allocation_remaining_calls": 1
}`,
            },
            {
              title: 'Common Error Responses',
              description:
                'Validation, trunk readiness, SIP availability, billing, and AMI connectivity failures return structured errors.',
              code: `{
  "error": "Missing required field: phone"
}

{
  "status": "warning",
  "code": "TRUNK_NOT_READY",
  "message": "registration_not_ready"
}

{
  "status": "warning",
  "code": "NO_SIP_AVAILABLE",
  "message": "No ready business SIP trunk and global fallback is disabled"
}

{
  "error": "insufficient credits",
  "code": "INSUFFICIENT_CREDIT",
  "reason_code": "insufficient_credit",
  "required_credit": "2.000000",
  "available_credit": "1.000000",
  "billing_owner_user_id": 2
}

{
  "error": "Failed to connect to AMI",
  "details": "timed out"
}`,
            },
          ],
        },
      ],
    },
    {
      title: 'Operations',
      description:
        'Operational checks for realtime SIP rows, Asterisk runtime state, and inbound enablement.',
      href: '/v3/operations',
      group: 'Operations',
      highlights: [
        'For registration trunks, ps_registrations=true is expected.',
        'For IP-auth trunks, static contact and identify readiness are more important than registration.',
        'Inbound trunks should show enable_inbound=true and ps_endpoint_id_ips=true.',
      ],
    },
    {
      title: 'Guides',
      description: 'Implementation guides for API v3.',
      href: '/v3/guides',
      group: 'Guides',
      highlights: [
        'Use runtime call originate when calling with business access-token auth.',
        'Use inherited v2-compatible schemas for public modules not redefined by the v3 schema.',
        'Prefer scoped access tokens for runtime automation and JWT auth for management workflows.',
      ],
    },
    {
      title: 'Changelog',
      description: 'API v3 release notes and changes.',
      href: '/v3/changelog',
      group: 'Start',
      highlights: [
        'v3 introduces the preferred runtime call origination endpoint.',
        'Deprecated: POST /api/v2/runtime/calls/originate. Use POST /api/v3/runtime/calls/originate instead.',
        'Some v2 endpoints are deprecated as their v3 equivalents become available.',
      ],
    },
  ],
}

const v3NativeEndpointPaths = new Set([
  '/api/v3/businesses',
  '/api/v3/sip-trunks',
  '/api/v3/sip-trunks/profiles',
  '/api/v3/sip-trunks/:id',
  '/api/v3/sip-trunks/:id/test',
  '/api/v3/sip-trunks/:id/status',
  '/api/v3/sip-trunks/:id/reload',
  '/api/v3/sip-trunks/:id/apply',
  '/api/v3/sip-trunks/:id/rollback',
  '/api/v3/sip-trunks/drift',
  '/api/v3/runtime/calls/originate',
])

const carriedV2PageSlugs = new Set([
  'authentication',
  'access-tokens',
  'flows',
  'calls',
  'tts',
  'audio-assets',
  'agents-departments',
  'extensions',
  'agent-runtime-calls',
  'billing',
  'business-webhooks',
])

function toV3Endpoint(endpoint: Endpoint): Endpoint {
  return {
    ...endpoint,
    path: endpoint.path.replace('/api/v2', '/api/v3'),
    details: endpoint.details?.map((detail) => ({
      ...detail,
      code: detail.code?.replaceAll('/api/v2', '/api/v3'),
      items: detail.items?.map((item) => item.replaceAll('/api/v2', '/api/v3')),
    })),
  }
}

function toV3CarryoverPage(page: DocsPage): DocsPage {
  return {
    ...page,
    description: `${page.description} These endpoints follow the v2 contract under the v3 prefix unless a native v3 page overrides them.`,
    href: page.href.replace('/v2', '/v3'),
    status: 'v2 contract, v3 prefix',
    highlights: [
      ...page.highlights,
      'Request and response schemas are inherited from the v2 contract and shown with /api/v3 paths.',
    ],
    endpoints: page.endpoints
      ?.map(toV3Endpoint)
      .filter((endpoint) => !v3NativeEndpointPaths.has(endpoint.path)),
  }
}

const v2BusinessPage = DOCS_PAGES.v2.find((page) => page.href === '/v2/businesses')
const v3BusinessPage = DOCS_PAGES.v3.find((page) => page.href === '/v3/businesses')

if (v2BusinessPage?.endpoints && v3BusinessPage) {
  const carriedBusinessEndpoints = v2BusinessPage.endpoints
    .map(toV3Endpoint)
    .filter((endpoint) => endpoint.path !== '/api/v3/businesses')

  v3BusinessPage.endpoints = [...(v3BusinessPage.endpoints ?? []), ...carriedBusinessEndpoints]
  v3BusinessPage.highlights = [
    ...v3BusinessPage.highlights,
    'Business CRUD, settings, inbound-call config, members, and ownership endpoints inherit the v2 contract under /api/v3.',
  ]
}

DOCS_PAGES.v3.splice(
  2,
  0,
  ...DOCS_PAGES.v2
    .filter((page) => carriedV2PageSlugs.has(page.href.split('/').at(-1) ?? ''))
    .map(toV3CarryoverPage)
    .filter((page) => page.endpoints && page.endpoints.length > 0),
)

export function getDocsPage(pathname: string, version: ApiVersion): DocsPage {
  const pages = DOCS_PAGES[version]

  return pages.find((page) => page.href === pathname) ?? pages[0]
}
