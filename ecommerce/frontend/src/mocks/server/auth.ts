import { z } from 'zod';
import type { Customer } from '@/lib/api/types';
import {
  apiError,
  CART_COOKIE,
  clearCookie,
  cookie,
  json,
  type MockRequest,
  type MockResponse,
  noContent,
  SESSION_COOKIE,
  zodFields,
} from './http';
import { findVariant, getDb, type MockCart, type MockUser } from './db';

function randomHex(length: number): string {
  const chars = '0123456789abcdef';
  let out = '';
  for (let i = 0; i < length; i++) {
    out += chars[Math.floor(Math.random() * chars.length)];
  }
  return out;
}

export function toCustomer(user: MockUser): Customer {
  return {
    id: user.id,
    email: user.email,
    firstName: user.firstName,
    lastName: user.lastName,
    createdAt: user.createdAt,
  };
}

function mergeGuestCart(customerId: string, guestCartId: string | undefined): void {
  const db = getDb();
  if (!guestCartId) return;
  const guestCart = db.carts.get(guestCartId);
  if (!guestCart || guestCart.customerId !== null) return;

  let customerCart: MockCart | undefined;
  for (const c of db.carts.values()) {
    if (c.customerId === customerId) {
      customerCart = c;
      break;
    }
  }

  if (customerCart) {
    for (const gLine of guestCart.lines) {
      const existing = customerCart.lines.find((l) => l.variantId === gLine.variantId);
      const found = findVariant(gLine.variantId);
      const available = found ? found.variant.availableQuantity : 0;
      const maxPerLine = db.store.maxQuantityPerLine;

      if (existing) {
        if (available > 0) {
          const cap = Math.min(available, maxPerLine);
          existing.quantity = Math.max(1, Math.min(existing.quantity + gLine.quantity, cap));
        }
      } else {
        const lineQty =
          available > 0
            ? Math.min(gLine.quantity, available, maxPerLine)
            : Math.min(gLine.quantity, maxPerLine);
        customerCart.lines.push({
          id: `line_${randomHex(8)}`,
          variantId: gLine.variantId,
          quantity: Math.max(1, lineQty),
        });
      }
    }
    customerCart.updatedAt = new Date().toISOString();
    db.carts.delete(guestCart.id);
  } else {
    guestCart.customerId = customerId;
    guestCart.updatedAt = new Date().toISOString();
  }
}

const RegisterBodySchema = z.object({
  firstName: z.string().min(1).max(60),
  lastName: z.string().min(1).max(60),
  email: z.string().email().max(254),
  password: z.string().min(8).max(128),
});

export function register(req: MockRequest): MockResponse {
  const db = getDb();
  const parseResult = RegisterBodySchema.safeParse(req.body);
  if (!parseResult.success) {
    return apiError(400, 'VALIDATION_FAILED', 'Validation failed.', zodFields(parseResult.error));
  }

  const { firstName, lastName, email, password } = parseResult.data;
  const lowerEmail = email.toLowerCase();

  const existingUser = db.users.find((u) => u.email.toLowerCase() === lowerEmail);
  if (existingUser) {
    return apiError(409, 'EMAIL_TAKEN', 'An account with this email already exists.', {
      email: ['An account with this email already exists.'],
    });
  }

  let maxSeq = 0;
  for (const u of db.users) {
    const match = u.id.match(/^cus_(\d+)$/);
    if (match) {
      const seq = parseInt(match[1], 10);
      if (seq > maxSeq) maxSeq = seq;
    }
  }
  const nextSeq = maxSeq + 1;
  const newUserId = `cus_${String(nextSeq).padStart(3, '0')}`;

  const newUser: MockUser = {
    id: newUserId,
    firstName,
    lastName,
    email: lowerEmail,
    password,
    createdAt: new Date().toISOString(),
  };
  db.users.push(newUser);

  const sessionToken = `sess_${randomHex(24)}`;
  db.sessions.set(sessionToken, newUser.id);

  mergeGuestCart(newUser.id, req.cookies[CART_COOKIE]);

  const setCookies = [
    cookie(SESSION_COOKIE, sessionToken, 30 * 24 * 3600),
    clearCookie(CART_COOKIE),
  ];

  return json(201, { customer: toCustomer(newUser) }, setCookies);
}

const SignInBodySchema = z.object({
  email: z.string().email(),
  password: z.string(),
});

export function signIn(req: MockRequest): MockResponse {
  const db = getDb();
  const parseResult = SignInBodySchema.safeParse(req.body);
  if (!parseResult.success) {
    return apiError(400, 'VALIDATION_FAILED', 'Validation failed.', zodFields(parseResult.error));
  }

  const { email, password } = parseResult.data;
  const lowerEmail = email.toLowerCase();
  const now = Date.now();

  const failures = db.signInFailures.get(lowerEmail) ?? [];
  const recentFailures = failures.filter((t) => now - t < 60000);
  db.signInFailures.set(lowerEmail, recentFailures);

  if (recentFailures.length >= 5) {
    const res = apiError(429, 'RATE_LIMITED', 'Too many attempts. Try again in 60 seconds.', null, {
      retryAfterSeconds: 60,
    });
    res.headers['retry-after'] = '60';
    return res;
  }

  const user = db.users.find(
    (u) => u.email.toLowerCase() === lowerEmail && u.password === password,
  );
  if (!user) {
    recentFailures.push(now);
    db.signInFailures.set(lowerEmail, recentFailures);
    return apiError(401, 'INVALID_CREDENTIALS', 'Invalid email or password.');
  }

  db.signInFailures.delete(lowerEmail);

  const sessionToken = `sess_${randomHex(24)}`;
  db.sessions.set(sessionToken, user.id);

  mergeGuestCart(user.id, req.cookies[CART_COOKIE]);

  const setCookies = [
    cookie(SESSION_COOKIE, sessionToken, 30 * 24 * 3600),
    clearCookie(CART_COOKIE),
  ];

  return json(200, { customer: toCustomer(user) }, setCookies);
}

export function signOut(req: MockRequest): MockResponse {
  const db = getDb();
  const sessionToken = req.cookies[SESSION_COOKIE];
  if (sessionToken) {
    db.sessions.delete(sessionToken);
  }
  return noContent([clearCookie(SESSION_COOKIE), clearCookie(CART_COOKIE)]);
}

export function me(req: MockRequest): MockResponse {
  const db = getDb();
  const sessionToken = req.cookies[SESSION_COOKIE];
  if (!sessionToken) {
    return apiError(401, 'UNAUTHENTICATED', 'Please sign in.');
  }

  const customerId = db.sessions.get(sessionToken);
  if (!customerId) {
    return apiError(401, 'UNAUTHENTICATED', 'Please sign in.');
  }

  const user = db.users.find((u) => u.id === customerId);
  if (!user) {
    return apiError(401, 'UNAUTHENTICATED', 'Please sign in.');
  }

  return json(200, { customer: toCustomer(user) });
}
