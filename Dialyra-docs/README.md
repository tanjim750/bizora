# Dialyra Documentation

Official developer documentation for **Dialyra** — API references, integration guides, and resources for building with the Dialyra platform.

## Overview

This repository contains the source code and content for the Dialyra documentation website.

The documentation helps developers understand and integrate Dialyra features, including:

* Authentication
* Call management
* Call flows
* SIP trunks
* Agents and queues
* Audio and TTS
* Billing
* Webhooks
* API integration guides

## API Versions

The documentation supports multiple Dialyra API versions:

* **v2**
* **v3**

Users can switch between API versions directly from the documentation header.

Versioned documentation follows a structure similar to:

```text
/docs/v2/...
/docs/v3/...
```

Each API version should remain isolated so updates to newer APIs do not affect documentation for existing integrations.

## Documentation Structure

```text
Dialyra Docs
├── Getting Started
├── Guides
├── API Reference
│   ├── v2
│   └── v3
└── Changelog
```

Only externally supported APIs should be included in the public documentation. Platform-level superuser, operational, and internal endpoints should remain in private/internal documentation.

## Development

Install dependencies:

```bash
npm install
```

Start the development server:

```bash
npm run dev
```

Create a production build:

```bash
npm run build
```

## Contributing

When updating the documentation:

1. Keep API documentation aligned with the actual backend behavior.
2. Add changes to the correct API version.
3. Avoid introducing breaking documentation changes into older API versions.
4. Keep examples concise and production-oriented.
5. Never expose secrets, credentials, or internal-only API details.

## About Dialyra

Dialyra is a programmable communication platform for designing, automating, and managing intelligent customer call experiences.

---

© Dialyra. All rights reserved.
