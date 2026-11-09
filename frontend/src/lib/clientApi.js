/**
 * Backward compatibility shim re-exporting clientApi, idempotency, and error helpers.
 */
export {
  clientApi,
  errorMessage,
  ApiError,
  normalizeError,
  newIdempotencyKey,
  makeExternalId,
} from './api/index.js'
