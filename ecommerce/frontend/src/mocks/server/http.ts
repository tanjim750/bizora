import type { z } from 'zod';

export type MockRequest = {
  method: 'GET' | 'POST' | 'PATCH' | 'DELETE';
  path: string;
  query?: Record<string, string | string[] | undefined>;
  body?: unknown;
  headers?: Record<string, string>;
  cookies: Record<string, string>;
};

export type MockResponse = {
  status: number;
  body: unknown;
  headers: Record<string, string>;
  setCookies: string[];
};

export const CART_COOKIE = 'aur_cart';
export const SESSION_COOKIE = 'aur_session';

export function newRequestId(): string {
  const chars = '0123456789abcdef';
  let id = '';
  for (let i = 0; i < 8; i++) {
    id += chars[Math.floor(Math.random() * chars.length)];
  }
  return `req_${id}`;
}

export function json(status: number, body: unknown, setCookies: string[] = []): MockResponse {
  const reqId = newRequestId();
  return {
    status,
    body,
    headers: {
      'content-type': 'application/json',
      'x-request-id': reqId,
    },
    setCookies,
  };
}

export function noContent(setCookies: string[] = []): MockResponse {
  return {
    status: 204,
    body: null,
    headers: {
      'x-request-id': newRequestId(),
    },
    setCookies,
  };
}

export function apiError(
  status: number,
  code: string,
  message: string,
  fields: Record<string, string[]> | null = null,
  details: Record<string, unknown> | null = null,
): MockResponse {
  const reqId = newRequestId();
  return {
    status,
    body: {
      error: {
        code,
        message,
        fields,
        details,
        requestId: reqId,
      },
    },
    headers: {
      'content-type': 'application/json',
      'x-request-id': reqId,
    },
    setCookies: [],
  };
}

export function zodFields(error: z.ZodError): Record<string, string[]> {
  const fields: Record<string, string[]> = {};
  for (const issue of error.issues) {
    const key = issue.path.join('.');
    if (!fields[key]) {
      fields[key] = [];
    }
    fields[key].push(issue.message);
  }
  return fields;
}

export function queryOne(
  query: Record<string, string | string[] | undefined> | undefined,
  key: string,
): string | undefined {
  if (!query) return undefined;
  const val = query[key];
  if (Array.isArray(val)) return val[0];
  return val;
}

export function queryAll(
  query: Record<string, string | string[] | undefined> | undefined,
  key: string,
): string[] {
  if (!query) return [];
  const val = query[key];
  if (val === undefined) return [];
  if (Array.isArray(val)) return val;
  return [val];
}

export function cookie(name: string, value: string, maxAgeSeconds: number): string {
  return `${name}=${value}; Path=/; HttpOnly; SameSite=Lax; Max-Age=${maxAgeSeconds}`;
}

export function clearCookie(name: string): string {
  return `${name}=; Path=/; HttpOnly; SameSite=Lax; Max-Age=0`;
}
