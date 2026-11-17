/**
 * Generates an RFC4122 v4 UUID for idempotency keys.
 * Safely works on secure and non-secure origins (LAN http://192.168.x.x or local dev).
 */
export function newIdempotencyKey() {
  if (typeof crypto !== 'undefined') {
    if (typeof crypto.randomUUID === 'function') {
      try {
        return crypto.randomUUID()
      } catch {
        // Fall through on non-secure contexts where randomUUID throws
      }
    }

    if (typeof crypto.getRandomValues === 'function') {
      try {
        const bytes = new Uint8Array(16)
        crypto.getRandomValues(bytes)
        bytes[6] = (bytes[6] & 0x0f) | 0x40 // Version 4
        bytes[8] = (bytes[8] & 0x3f) | 0x80 // Variant 10xx
        const hex = Array.from(bytes, (b) => b.toString(16).padStart(2, '0')).join('')
        return `${hex.slice(0, 8)}-${hex.slice(8, 12)}-${hex.slice(12, 16)}-${hex.slice(16, 20)}-${hex.slice(20)}`
      } catch {
        // Fall through to Math.random
      }
    }
  }

  // Pure fallback for environments without crypto
  return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, (c) => {
    const r = (Math.random() * 16) | 0
    const v = c === 'x' ? r : (r & 0x3) | 0x8
    return v.toString(16)
  })
}

/**
 * Creates a stable external reference ID that embeds an idempotency key.
 * Stays stable across retries for the same key.
 */
export function makeExternalId(prefix, key) {
  const cleanKey = String(key || '')
    .replaceAll('-', '')
    .slice(0, 16)
  return `${prefix}_${cleanKey}`
}
