export const duration = {
  instant: 0.12,
  fast: 0.2,
  base: 0.32,
  slow: 0.56,
  hero: 0.9,
} as const;

export const ease = {
  out: [0.16, 1, 0.3, 1],
  inOut: [0.65, 0, 0.35, 1],
  in: [0.7, 0, 0.84, 0],
} as const;

export const gsapEase = {
  out: 'expo.out',
  inOut: 'power3.inOut',
  in: 'power3.in',
} as const;

export const spring = {
  snappy: { type: 'spring', stiffness: 420, damping: 34, mass: 0.9 },
  soft: { type: 'spring', stiffness: 220, damping: 28 },
} as const;

export const stagger = {
  list: 0.04,
  maxItems: 12,
} as const;

export const distance = {
  reveal: 24,
  page: 12,
} as const;

export function staggerDelay(index: number): number {
  return Math.min(index, stagger.maxItems - 1) * stagger.list;
}

export const MEDIA_FULL = '(prefers-reduced-motion: no-preference)';
export const MEDIA_REDUCED = '(prefers-reduced-motion: reduce)';
