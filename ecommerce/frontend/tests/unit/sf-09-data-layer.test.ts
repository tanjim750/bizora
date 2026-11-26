import fs from 'node:fs';
import path from 'node:path';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { ApiError } from '@/lib/api/errors';
import type { ApiRequest, Transport } from '@/lib/api/types';
import { createHttpTransport } from '@/lib/api/transport-http';
import { mockTransport } from '@/lib/api/transport-mock';
import { createApi } from '@/lib/api/create-api';
import { resetMockDb } from '@/mocks/server/db';

describe('SF-09 Data Layer & Mock/Real Switch', () => {
  const originalEnv = { ...process.env };

  beforeEach(() => {
    resetMockDb();
    vi.restoreAllMocks();
  });

  afterEach(() => {
    process.env = { ...originalEnv };
    vi.unstubAllGlobals();
  });

  describe('HTTP Transport', () => {
    it('constructs query strings with repeated keys and booleans, setting credentials and headers', async () => {
      const mockFetch = vi.fn(
        async () =>
          new Response(JSON.stringify({ ok: 1 }), {
            status: 200,
            headers: { 'content-type': 'application/json' },
          }),
      );
      vi.stubGlobal('fetch', mockFetch);

      const transport = createHttpTransport('https://api.test/v1/');
      const res = await transport({
        method: 'GET',
        path: '/products',
        query: {
          color: ['Sand', 'Ink'],
          inStock: true as unknown as string,
          q: undefined,
        },
      });

      expect(res.status).toBe(200);
      expect(res.body).toEqual({ ok: 1 });
      expect(mockFetch).toHaveBeenCalledTimes(1);

      const [url, init] = mockFetch.mock.calls[0] as unknown as [string, RequestInit];
      expect(url).toBe('https://api.test/v1/products?color=Sand&color=Ink&inStock=true');
      expect(init.method).toBe('GET');
      expect(init.credentials).toBe('include');
      expect((init.headers as Record<string, string>)['accept']).toBe('application/json');
      expect((init.headers as Record<string, string>)['content-type']).toBeUndefined();
    });

    it('sends JSON body and content-type on POST requests', async () => {
      const mockFetch = vi.fn(
        async () =>
          new Response(JSON.stringify({ status: 'subscribed' }), {
            status: 200,
            headers: { 'content-type': 'application/json' },
          }),
      );
      vi.stubGlobal('fetch', mockFetch);

      const transport = createHttpTransport('https://api.test/v1');
      await transport({
        method: 'POST',
        path: '/newsletter',
        body: { email: 'test@example.com' },
      });

      const [, init] = mockFetch.mock.calls[0] as unknown as [string, RequestInit];
      expect(init.method).toBe('POST');
      expect(init.body).toBe(JSON.stringify({ email: 'test@example.com' }));
      expect((init.headers as Record<string, string>)['content-type']).toBe('application/json');
    });

    it('handles 204 No Content with null body', async () => {
      const mockFetch = vi.fn(
        async () =>
          new Response(null, {
            status: 204,
          }),
      );
      vi.stubGlobal('fetch', mockFetch);

      const transport = createHttpTransport('https://api.test/v1');
      const res = await transport({
        method: 'POST',
        path: '/auth/sign-out',
      });
      expect(res.status).toBe(204);
      expect(res.body).toBeNull();
    });

    it('translates fetch rejection into ApiError with NETWORK_ERROR code', async () => {
      const mockFetch = vi.fn(async () => {
        throw new Error('Connection refused');
      });
      vi.stubGlobal('fetch', mockFetch);

      const transport = createHttpTransport('https://api.test/v1');
      await expect(
        transport({
          method: 'GET',
          path: '/store',
        }),
      ).rejects.toSatisfy((err: unknown) => {
        expect(err).toBeInstanceOf(ApiError);
        const apiErr = err as ApiError;
        expect(apiErr.code).toBe('NETWORK_ERROR');
        expect(apiErr.status).toBe(0);
        return true;
      });
    });
  });

  describe('Mock Transport & createApi integration', () => {
    it('executes in-process mock requests via createApi(mockTransport)', async () => {
      const api = createApi(mockTransport);

      const store = await api.store.get();
      expect(store.name).toBe('Aurelo');

      const saleProducts = await api.catalog.listProducts({ collection: 'sale' });
      expect(saleProducts.totalItems).toBe(5);

      await expect(api.catalog.getProduct('nonexistent-product')).rejects.toSatisfy(
        (err: unknown) => {
          expect(err).toBeInstanceOf(ApiError);
          const apiErr = err as ApiError;
          expect(apiErr.status).toBe(404);
          expect(apiErr.code).toBe('NOT_FOUND');
          return true;
        },
      );
    });
  });

  describe('Contract enforcement in createApi', () => {
    it('throws ApiError with CONTRACT_MISMATCH status 502 when 2xx response violates schema', async () => {
      const fakeTransport: Transport = async () => ({
        status: 200,
        body: { invalidField: true },
        headers: {},
      });

      const api = createApi(fakeTransport);
      await expect(api.store.get()).rejects.toSatisfy((err: unknown) => {
        expect(err).toBeInstanceOf(ApiError);
        const apiErr = err as ApiError;
        expect(apiErr.status).toBe(502);
        expect(apiErr.code).toBe('CONTRACT_MISMATCH');
        return true;
      });
    });

    it('parses valid ErrorEnvelope on non-2xx status and extracts code and details', async () => {
      const fakeTransport: Transport = async () => ({
        status: 409,
        body: {
          error: {
            code: 'PRICE_CHANGED',
            message: 'Price has changed',
            fields: null,
            details: { quote: { total: { amount: 350000, currency: 'BDT' } } },
            requestId: 'req_12345678',
          },
        },
        headers: {},
      });

      const api = createApi(fakeTransport);
      await expect(api.checkout.quote('standard')).rejects.toSatisfy((err: unknown) => {
        expect(err).toBeInstanceOf(ApiError);
        const apiErr = err as ApiError;
        expect(apiErr.status).toBe(409);
        expect(apiErr.code).toBe('PRICE_CHANGED');
        expect(apiErr.details).toBeDefined();
        return true;
      });
    });

    it('falls back to UNKNOWN on non-conforming error bodies', async () => {
      const fakeTransport: Transport = async () => ({
        status: 500,
        body: 'oops',
        headers: {},
      });

      const api = createApi(fakeTransport);
      await expect(api.store.get()).rejects.toSatisfy((err: unknown) => {
        expect(err).toBeInstanceOf(ApiError);
        const apiErr = err as ApiError;
        expect(apiErr.status).toBe(500);
        expect(apiErr.code).toBe('UNKNOWN');
        return true;
      });
    });

    it('records Idempotency-Key header on placeOrder and token query param on orders.get', async () => {
      const calls: ApiRequest[] = [];
      const recordingTransport: Transport = async (req) => {
        calls.push(req);
        if (req.path.startsWith('/checkout')) {
          return {
            status: 201,
            body: {
              order: {
                id: 'ord_1',
                number: 'AUR-100200',
                status: 'placed',
                paymentStatus: 'pending',
                placedAt: '2026-11-26T00:00:00Z',
                email: 'test@example.com',
                phone: '+8801700000000',
                shippingAddress: {
                  firstName: 'Nadia',
                  lastName: 'Rahman',
                  line1: 'House 12, Road 5',
                  line2: null,
                  city: 'Dhaka',
                  postalCode: '1200',
                  countryCode: 'BD',
                },
                shippingMethod: {
                  id: 'standard',
                  label: 'Standard',
                  price: { amount: 8000, currency: 'BDT' },
                },
                paymentMethod: { id: 'cod', label: 'COD' },
                lines: [],
                subtotal: { amount: 100000, currency: 'BDT' },
                shipping: { amount: 8000, currency: 'BDT' },
                tax: { amount: 5400, currency: 'BDT' },
                total: { amount: 113400, currency: 'BDT' },
                note: null,
              },
              confirmationToken: 'tok_123',
            },
            headers: {},
          };
        }
        return {
          status: 200,
          body: {
            id: 'ord_1',
            number: 'AUR-1',
            status: 'placed',
            paymentStatus: 'pending',
            placedAt: '2026-11-26T00:00:00Z',
            email: 'test@example.com',
            phone: '+8801700000000',
            shippingAddress: {
              firstName: 'Nadia',
              lastName: 'Rahman',
              line1: 'House 12, Road 5',
              line2: null,
              city: 'Dhaka',
              postalCode: '1200',
              countryCode: 'BD',
            },
            shippingMethod: {
              id: 'standard',
              label: 'Standard',
              price: { amount: 8000, currency: 'BDT' },
            },
            paymentMethod: { id: 'cod', label: 'COD' },
            lines: [],
            subtotal: { amount: 100000, currency: 'BDT' },
            shipping: { amount: 8000, currency: 'BDT' },
            tax: { amount: 5400, currency: 'BDT' },
            total: { amount: 113400, currency: 'BDT' },
            note: null,
          },
          headers: {},
        };
      };

      const api = createApi(recordingTransport);
      await api.checkout.placeOrder(
        {
          email: 'test@example.com',
          phone: '+8801700000000',
          shippingAddress: {
            firstName: 'A',
            lastName: 'B',
            line1: 'C',
            line2: null,
            city: 'Dhaka',
            postalCode: '1200',
            countryCode: 'BD',
          },
          shippingMethodId: 'standard',
          paymentMethodId: 'cod',
          note: null,
          expectedTotal: { amount: 113400, currency: 'BDT' },
        },
        'key-1',
      );

      expect(calls[0].headers?.['Idempotency-Key']).toBe('key-1');

      await api.orders.get('AUR-1', 'tok');
      expect(calls[1].path).toBe('/orders/AUR-1');
      expect(calls[1].query).toEqual({ token: 'tok' });
    });
  });

  describe('Next.js rewrites switch in next.config.ts', () => {
    it('returns empty array when API_BASE_URL is not set', async () => {
      delete process.env.API_BASE_URL;
      const config = (await import('../../next.config')).default;
      const rewrites = typeof config.rewrites === 'function' ? await config.rewrites() : [];
      expect(rewrites).toEqual([]);
    });

    it('returns beforeFiles rewrite when API_BASE_URL is set', async () => {
      process.env.API_BASE_URL = 'https://api.test/v1/';
      const config = (await import('../../next.config')).default;
      const rewrites = typeof config.rewrites === 'function' ? await config.rewrites() : [];
      expect(rewrites).toEqual({
        beforeFiles: [
          {
            source: '/api/store/:path*',
            destination: 'https://api.test/v1/:path*',
          },
        ],
        afterFiles: [],
        fallback: [],
      });
    });
  });

  describe('Source Guard: direct fetch and mocks imports', () => {
    it('ensures no app/components/stores file contains direct fetch or imports @/mocks', () => {
      const srcDir = path.resolve(process.cwd(), 'src');
      const dirsToCheck = ['components', 'stores'];

      function checkDir(dir: string) {
        if (!fs.existsSync(dir)) return;
        const entries = fs.readdirSync(dir, { withFileTypes: true });
        for (const entry of entries) {
          const fullPath = path.join(dir, entry.name);
          if (entry.isDirectory()) {
            checkDir(fullPath);
          } else if (/\.(ts|tsx|js|jsx)$/.test(entry.name)) {
            const content = fs.readFileSync(fullPath, 'utf-8');
            expect(content).not.toMatch(/\bfetch\s*\(/);
            expect(content).not.toMatch(/from\s+['"]@\/mocks/);
          }
        }
      }

      for (const d of dirsToCheck) {
        checkDir(path.join(srcDir, d));
      }

      // Check app/ except app/api/store/
      function checkAppDir(dir: string) {
        if (!fs.existsSync(dir)) return;
        const entries = fs.readdirSync(dir, { withFileTypes: true });
        for (const entry of entries) {
          const fullPath = path.join(dir, entry.name);
          if (fullPath.includes(path.join('app', 'api', 'store'))) {
            continue;
          }
          if (entry.isDirectory()) {
            checkAppDir(fullPath);
          } else if (/\.(ts|tsx|js|jsx)$/.test(entry.name)) {
            const content = fs.readFileSync(fullPath, 'utf-8');
            expect(content).not.toMatch(/\bfetch\s*\(/);
            expect(content).not.toMatch(/from\s+['"]@\/mocks/);
          }
        }
      }
      checkAppDir(path.join(srcDir, 'app'));
    });
  });
});
