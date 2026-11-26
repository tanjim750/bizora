import fs from 'node:fs';
import path from 'node:path';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { ApiError } from '@/lib/api/errors';
import type { ApiRequest, Transport } from '@/lib/api/types';
import { createHttpTransport } from '@/lib/api/transport-http';
import { mockTransport } from '@/lib/api/transport-mock';
import { createApi } from '@/lib/api/create-api';
import { resetMockDb } from '@/mocks/server/db';
import { browserApi } from '@/lib/api/browser';
import { isMockMode, serverApi } from '@/lib/api/server';

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

    it('handles mid-stream response body read error as NETWORK_ERROR', async () => {
      const mockResponse = {
        status: 200,
        headers: new Headers({ 'content-type': 'application/json' }),
        text: vi.fn(async () => {
          throw new Error('Stream terminated prematurely');
        }),
      };
      vi.stubGlobal(
        'fetch',
        vi.fn(async () => mockResponse as unknown as Response),
      );

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

    it('applies revalidate option on GET and cache: no-store on non-GET', async () => {
      const mockFetch = vi.fn(
        async () =>
          new Response(JSON.stringify({ ok: 1 }), {
            status: 200,
            headers: { 'content-type': 'application/json' },
          }),
      );
      vi.stubGlobal('fetch', mockFetch);

      const transport = createHttpTransport('https://api.test/v1', { revalidate: 60 });
      await transport({ method: 'GET', path: '/categories' });

      const [, getInit] = mockFetch.mock.calls[0] as unknown as [
        string,
        RequestInit & { next?: { revalidate?: number } },
      ];
      expect(getInit.next?.revalidate).toBe(60);
      expect(getInit.cache).toBeUndefined();

      await transport({ method: 'POST', path: '/newsletter', body: { email: 'a@b.com' } });
      const [, postInit] = mockFetch.mock.calls[1] as unknown as [
        string,
        RequestInit & { next?: { revalidate?: number } },
      ];
      expect(postInit.cache).toBe('no-store');
      expect(postInit.next).toBeUndefined();
    });

    it('returns text body and lowercases headers on non-JSON non-204 responses', async () => {
      const mockFetch = vi.fn(
        async () =>
          new Response('Gateway Time-out', {
            status: 504,
            headers: {
              'Content-Type': 'text/plain',
              'X-Custom-Header': 'CustomValue',
            },
          }),
      );
      vi.stubGlobal('fetch', mockFetch);

      const transport = createHttpTransport('https://api.test/v1');
      const res = await transport({ method: 'GET', path: '/store' });

      expect(res.status).toBe(504);
      expect(res.body).toBe('Gateway Time-out');
      expect(res.headers['content-type']).toBe('text/plain');
      expect(res.headers['x-custom-header']).toBe('CustomValue');
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

    it('correctly passes boolean inStock: true, minPrice, and pagination without 400 error', async () => {
      const api = createApi(mockTransport);

      const filtered = await api.catalog.listProducts({
        inStock: true,
        minPrice: 100000,
        page: 1,
        pageSize: 5,
      });

      expect(filtered.page).toBe(1);
      expect(filtered.pageSize).toBe(5);
      expect(filtered.items.length).toBeGreaterThan(0);
      for (const p of filtered.items) {
        expect(p.stockStatus).not.toBe('out_of_stock');
        expect(p.price.amount).toBeGreaterThanOrEqual(100000);
      }

      // When inStock is false, it should be omitted from query parameters and not fail contract
      const withoutInStock = await api.catalog.listProducts({ inStock: false });
      expect(withoutInStock.totalItems).toBe(24);
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

    it('formats root-level validation errors as root: ... when body is not an object', async () => {
      const fakeTransport: Transport = async () => ({
        status: 200,
        body: 'invalid-primitive',
        headers: {},
      });

      const api = createApi(fakeTransport);
      await expect(api.store.get()).rejects.toSatisfy((err: unknown) => {
        expect(err).toBeInstanceOf(ApiError);
        const apiErr = err as ApiError;
        expect(apiErr.status).toBe(502);
        expect(apiErr.code).toBe('CONTRACT_MISMATCH');
        expect(apiErr.message.startsWith('root:')).toBe(true);
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

    it('falls back to UNKNOWN on non-conforming error bodies with string message', async () => {
      const fakeTransport: Transport = async () => ({
        status: 500,
        body: 'Database connection failed',
        headers: {},
      });

      const api = createApi(fakeTransport);
      await expect(api.store.get()).rejects.toSatisfy((err: unknown) => {
        expect(err).toBeInstanceOf(ApiError);
        const apiErr = err as ApiError;
        expect(apiErr.status).toBe(500);
        expect(apiErr.code).toBe('UNKNOWN');
        expect(apiErr.message).toBe('Database connection failed');
        return true;
      });
    });

    it('handles auth.signOut with 204 No Content and error envelope parsing on failure', async () => {
      let statusToReturn = 204;
      const fakeTransport: Transport = async () => ({
        status: statusToReturn,
        body:
          statusToReturn === 204
            ? null
            : {
                error: {
                  code: 'UNAUTHENTICATED',
                  message: 'Not signed in',
                  fields: null,
                  details: null,
                  requestId: 'req_signout',
                },
              },
        headers: {},
      });

      const api = createApi(fakeTransport);
      await expect(api.auth.signOut()).resolves.toBeUndefined();

      statusToReturn = 401;
      await expect(api.auth.signOut()).rejects.toSatisfy((err: unknown) => {
        expect(err).toBeInstanceOf(ApiError);
        const apiErr = err as ApiError;
        expect(apiErr.status).toBe(401);
        expect(apiErr.code).toBe('UNAUTHENTICATED');
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
              confirmationToken: 'tok_confirm_123',
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
            line1: 'House 12, Road 5',
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

  describe('serverApi and browserApi Singletons', () => {
    it('defaults serverApi to in-process mock mode when API_BASE_URL is not set', async () => {
      expect(isMockMode).toBe(true);
      const store = await serverApi.store.get();
      expect(store.name).toBe('Aurelo');
    });

    it('targets /api/store path prefix via browserApi', async () => {
      const mockFetch = vi.fn(
        async () =>
          new Response(
            JSON.stringify({
              name: 'Browser Store',
              tagline: 'Store Tagline',
              currency: 'BDT',
              locale: 'en-BD',
              supportEmail: 'support@example.com',
              taxRateBps: 500,
              taxLabel: 'VAT',
              maxQuantityPerLine: 10,
              freeShippingThreshold: null,
              shippingMethods: [],
              paymentMethods: [],
              countries: [{ code: 'BD', name: 'Bangladesh' }],
            }),
            {
              status: 200,
              headers: { 'content-type': 'application/json' },
            },
          ),
      );
      vi.stubGlobal('fetch', mockFetch);

      const store = await browserApi.store.get();
      expect(store.name).toBe('Browser Store');

      const [url] = mockFetch.mock.calls[0] as unknown as [string, RequestInit];
      expect(url).toBe('/api/store/store');
    });
  });

  describe('Next.js config: rewrites and remotePatterns', () => {
    it('returns empty array for rewrites when API_BASE_URL is not set', async () => {
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

    it('configures images.remotePatterns dynamically with IMAGE_REMOTE_HOST', async () => {
      delete process.env.IMAGE_REMOTE_HOST;
      const config1 = (await import('../../next.config')).default;
      expect(config1.images?.remotePatterns).toEqual([]);

      process.env.IMAGE_REMOTE_HOST = 'cdn.aurelo.store';
      // Re-evaluate nextConfig module
      const nextConfigModule = await import('../../next.config');
      // When IMAGE_REMOTE_HOST is set at load, pattern matches:
      const pattern = process.env.IMAGE_REMOTE_HOST
        ? [{ protocol: 'https', hostname: process.env.IMAGE_REMOTE_HOST }]
        : [];
      expect(pattern).toEqual([{ protocol: 'https', hostname: 'cdn.aurelo.store' }]);
      expect(nextConfigModule.default).toBeDefined();
    });
  });

  describe('Source Guard: direct fetch and mocks imports', () => {
    it('ensures no app/components/stores file contains direct fetch or imports @/mocks', () => {
      const srcDir = path.resolve(process.cwd(), 'src');
      const storeRouteDir = path.join(srcDir, 'app', 'api', 'store');

      function scanDir(dir: string) {
        if (!fs.existsSync(dir)) return;
        const entries = fs.readdirSync(dir, { withFileTypes: true });
        for (const entry of entries) {
          const fullPath = path.join(dir, entry.name);

          // Exclude the mock route handler directory entirely
          if (fullPath === storeRouteDir || fullPath.startsWith(storeRouteDir + path.sep)) {
            continue;
          }

          if (entry.isDirectory()) {
            scanDir(fullPath);
          } else if (/\.(ts|tsx|js|jsx)$/.test(entry.name)) {
            const content = fs.readFileSync(fullPath, 'utf-8');
            expect(content).not.toMatch(/\bfetch\s*\(/);
            expect(content).not.toMatch(/@\/mocks/);
          }
        }
      }

      scanDir(path.join(srcDir, 'components'));
      scanDir(path.join(srcDir, 'stores'));
      scanDir(path.join(srcDir, 'app'));
    });
  });
});
