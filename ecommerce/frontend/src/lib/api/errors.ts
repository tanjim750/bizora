import { z } from 'zod';
import { ErrorCodeSchema } from './schemas';

export type ErrorCode = z.infer<typeof ErrorCodeSchema>;

export class ApiError extends Error {
  constructor(
    public status: number,
    public code: string,
    message: string,
    public fields: Record<string, string[]> | null = null,
    public details: Record<string, unknown> | null = null,
    public requestId: string | null = null,
  ) {
    super(message);
    this.name = 'ApiError';
  }
}

export function isApiError(e: unknown): e is ApiError {
  return (
    e instanceof ApiError ||
    (typeof e === 'object' &&
      e !== null &&
      'name' in e &&
      (e as { name: string }).name === 'ApiError' &&
      'status' in e &&
      'code' in e)
  );
}

export const USER_MESSAGES: Record<string, string> = {
  VALIDATION_FAILED: 'Please check the highlighted fields.',
  IDEMPOTENCY_KEY_REQUIRED: 'Something went wrong. Please try again.',
  UNAUTHENTICATED: 'Please sign in.',
  INVALID_CREDENTIALS: "That email and password don't match.",
  NOT_FOUND: 'This item is no longer available.',
  VARIANT_NOT_FOUND: 'This option is no longer available.',
  LINE_NOT_FOUND: 'Your cart was updated.',
  EMAIL_TAKEN: 'An account with this email already exists.',
  OUT_OF_STOCK: 'Sorry, this is sold out.',
  CART_EMPTY: 'Your cart is empty.',
  PRICE_CHANGED: 'Prices changed since you started checkout. Please review the new total.',
  IDEMPOTENCY_CONFLICT: 'Something went wrong. Please try again.',
  UNSUPPORTED_MEDIA_TYPE: 'Something went wrong. Please try again.',
  SHIPPING_METHOD_UNAVAILABLE: 'Please choose another delivery option.',
  PAYMENT_METHOD_UNAVAILABLE: 'Please choose another payment method.',
  INTERNAL: 'Something went wrong on our side. Please try again.',
  UNAVAILABLE: 'The shop is taking a short break. Please try again soon.',
  NETWORK_ERROR: 'You seem to be offline. Check your connection and try again.',
  CONTRACT_MISMATCH: 'Something went wrong on our side. Please try again.',
  UNKNOWN: 'Something went wrong. Please try again.',
};

export function toUserMessage(e: unknown): string {
  if (!isApiError(e)) {
    return 'Something went wrong. Please try again.';
  }

  if (e.code === 'INSUFFICIENT_STOCK') {
    const available = e.details?.available ?? 0;
    return `Only ${available} left — we've updated the quantity.`;
  }

  if (e.code === 'RATE_LIMITED') {
    const retryAfter = e.details?.retryAfterSeconds ?? 60;
    return `Too many attempts. Try again in ${retryAfter} seconds.`;
  }

  if (Object.hasOwn(USER_MESSAGES, e.code)) {
    return USER_MESSAGES[e.code];
  }

  return 'Something went wrong. Please try again.';
}
