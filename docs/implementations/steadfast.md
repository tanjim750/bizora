# Steadfast courier integration

The Django module lives in `app/integrations/steadfast`. It ports the PHP SDK's authenticated API operations: single and bulk orders, status and history, returns, pickups, payments, police stations, fraud score, and ping. It also verifies HMAC SHA-256 or bearer authenticated webhooks.

Migration `0011_steadfast_source` registers the `steadfast` courier provider. Configure a live connection through Bizora's existing integration configuration API. Set `is_mock: false`, select `SHIPMENT` and `SHIPMENT_EVENT` with `READ_SHIPMENTS`, and add `CREATE_SHIPMENTS` to the scopes if staff may submit orders. Configure `api_key`, `secret_key`, and optionally `webhook_secret` as `env:BIZORA_BUSINESS_<id>_<NAME>` references. Put the actual secrets only in the referenced environment variables. The webhook event list must include `delivery_status` to update shipments from webhooks.

Routes under `/api/businesses/<business_id>/integrations/steadfast/<connection_id>/`:

- `POST shipments/`: authenticated manager operation with `order_id`, `recipient_name`, `recipient_phone`, and `recipient_address`; optional `cod_amount` and supported Steadfast order fields. The order's BDT total is used for COD when omitted. Returns the saved shipment and whether it was newly created.
- `POST shipments/<shipment_id>/refresh/`: authenticated manager operation; fetches the courier status and records a change event.
- `POST webhook/`: validates the configured signature or bearer token and updates an existing shipment matched within the connection. The endpoint never creates an order or shipment from an incoming webhook.

The external invoice is deterministic (`BIZORA-<order_id>`). Submission locks the order and returns an existing shipment for the same connection to avoid duplicate local records. The PHP SDK retries order creation on transient errors; this port does likewise with that deterministic invoice. If the courier accepts a request but the response is lost, confirm the invoice with Steadfast before manually resubmitting.

The Python service can be used directly from trusted server code via `service_for(connection)`. The HTTP client accepts an injected transport and sleep callback for deterministic tests. It does not follow redirects, rejects absolute endpoints, bounds timeout and retries, and keeps credential values out of persisted records.
Live Bizora connections accept only the official `portal.packzy.com` HTTPS host as their provider base URL.
