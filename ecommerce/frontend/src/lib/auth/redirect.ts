export function safeNextPath(
  next: string | null | undefined,
  fallback = '/account',
): string {
  if (!next || typeof next !== 'string') return fallback;
  if (next.length > 200) return fallback;
  if (!next.startsWith('/')) return fallback;
  if (next.startsWith('//') || next.startsWith('/\\')) return fallback;
  // Control characters
  if (/[\x00-\x1F\x7F]/.test(next)) return fallback;
  // Never returns an auth redirect loop
  if (
    next.startsWith('/account/sign-in') ||
    next.startsWith('/account/register')
  ) {
    return fallback;
  }
  return next;
}
