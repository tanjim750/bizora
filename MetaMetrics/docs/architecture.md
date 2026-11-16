# MetaMetrics Architecture

MetaMetrics is a framework-independent Python client library for the Meta Marketing API. It is designed to provide strict parity, type safety, and zero external runtime dependencies beyond `httpx`.

## Layered Architecture

```
                  ┌────────────────────────────────────────┐
                  │            MetaAds Facade              │
                  └───────────────────┬────────────────────┘
                                      │
         ┌───────────────┬────────────┼───────────────┬────────────────┐
         ▼               ▼            ▼               ▼                ▼
   Authentication     Account     Entities        Insights         Tracking
      Service         Service   (Campaign/AdSet/  Service           Parser
                                      Ad)             │
                                      │               ▼
                                      │        Metrics Engine
                                      │      (Registry/Calc/Agg)
                                      ▼               │
                              Paginator & Query       │
                                      │               │
                                      └───────┬───────┘
                                              ▼
                                      Historical Service
                                              │
                                              ▼
                                       Hierarchy Service
                                              │
                                              ▼
                                       MetaClient (HTTP)
```

## Key Principles

1. **Framework Independent**: No dependency on Django, Flask, FastAPI, or Celery. Reads no environment variables or configuration files internally.
2. **Immutability & Safety**: All configuration and DTO objects are frozen dataclasses with slots.
3. **Safe Diagnostics**: Exceptions and client logs never leak access tokens or sensitive credentials.
4. **Strict Parity**: Query parameters, numeric coercion, date validation, and metric formulas follow strict Meta API semantics.
