import { beforeEach, describe, expect, it } from 'vitest';
import { z } from 'zod';
import {
  CategoryListSchema,
  ErrorEnvelopeSchema,
  HomeContentSchema,
  NewsletterResultSchema,
  ProductListSchema,
  ProductSchema,
  RelatedProductsSchema,
  StoreConfigSchema,
  SuggestSchema,
} from '@/lib/api/schemas';
import {
  CART_COOKIE,
  clearCookie,
  cookie,
  type MockRequest,
  type MockResponse,
  noContent,
  queryAll,
  queryOne,
  SESSION_COOKIE,
  zodFields,
} from '@/mocks/server/http';
import { findVariant, getDb, recomputeStock, resetMockDb } from '@/mocks/server/db';
import { handleMockRequest } from '@/mocks/server/router';

async function call(
  method: 'GET' | 'POST' | 'PATCH' | 'DELETE',
  path: string,
  query?: Record<string, string | string[] | undefined>,
  body?: unknown,
  headers?: Record<string, string>,
): Promise<MockResponse> {
  const req: MockRequest = {
    method,
    path,
    query,
    body,
    headers: {
      ...(body !== undefined ? { 'content-type': 'application/json' } : {}),
      ...headers,
    },
    cookies: {},
  };
  return handleMockRequest(req);
}

describe('SF-07 Mock Backend Part 1 — Catalog & Core', () => {
  beforeEach(() => {
    resetMockDb();
  });

  describe('HTTP & DB Helpers', () => {
    it('verifies http.ts helpers (noContent, zodFields, cookie, clearCookie, query helpers)', () => {
      const nc = noContent();
      expect(nc.status).toBe(204);
      expect(nc.body).toBeNull();

      expect(cookie('aur_session', 'token123', 3600)).toBe(
        'aur_session=token123; Path=/; HttpOnly; SameSite=Lax; Max-Age=3600',
      );
      expect(clearCookie('aur_session')).toBe(
        'aur_session=; Path=/; HttpOnly; SameSite=Lax; Max-Age=0',
      );
      expect(CART_COOKIE).toBe('aur_cart');
      expect(SESSION_COOKIE).toBe('aur_session');

      const testSchema = z.object({ email: z.string().email(), age: z.number().int() });
      const parseRes = testSchema.safeParse({ email: 'bad', age: -1.5 });
      if (!parseRes.success) {
        const fields = zodFields(parseRes.error);
        expect(fields.email).toBeDefined();
        expect(fields.age).toBeDefined();
      }

      expect(queryOne({ q: ['a', 'b'] }, 'q')).toBe('a');
      expect(queryOne({ q: 'single' }, 'q')).toBe('single');
      expect(queryOne(undefined, 'q')).toBeUndefined();
      expect(queryAll({ tag: ['x', 'y'] }, 'tag')).toEqual(['x', 'y']);
      expect(queryAll({ tag: 'single' }, 'tag')).toEqual(['single']);
      expect(queryAll(undefined, 'tag')).toEqual([]);
    });

    it('verifies db.ts recomputeStock and findVariant', () => {
      const db = getDb();
      const product = db.products[0];
      expect(findVariant(product.variants[0].id)?.variant.id).toBe(product.variants[0].id);
      expect(findVariant('nonexistent')).toBeNull();

      // Test recomputeStock thresholds
      const clone = structuredClone(product);
      clone.variants[0].availableQuantity = 0;
      clone.variants[1].availableQuantity = 3;
      clone.variants[2].availableQuantity = 20;
      recomputeStock(clone);
      expect(clone.variants[0].stockStatus).toBe('out_of_stock');
      expect(clone.variants[1].stockStatus).toBe('low_stock');
      expect(clone.variants[2].stockStatus).toBe('in_stock');
      expect(clone.stockStatus).toBe('in_stock');
      expect(clone.defaultVariantId).toBe(clone.variants[1].id);

      // All zero
      clone.variants[1].availableQuantity = 0;
      clone.variants[2].availableQuantity = 0;
      recomputeStock(clone);
      expect(clone.stockStatus).toBe('out_of_stock');
      expect(clone.defaultVariantId).toBe(clone.variants[0].id);
    });
  });

  describe('Static & Content Endpoints', () => {
    it('GET /store returns 200 matching StoreConfigSchema', async () => {
      const res = await call('GET', '/store');
      expect(res.status).toBe(200);
      expect(() => StoreConfigSchema.parse(res.body)).not.toThrow();
      expect(res.headers['x-request-id']).toMatch(/^req_[0-9a-f]{8}$/);
    });

    it('GET /store/ handles trailing slash', async () => {
      const res = await call('GET', '/store/');
      expect(res.status).toBe(200);
    });

    it('GET /content/home returns 200 matching HomeContentSchema', async () => {
      const res = await call('GET', '/content/home');
      expect(res.status).toBe(200);
      expect(() => HomeContentSchema.parse(res.body)).not.toThrow();
    });

    it('GET /categories returns 5 categories with productCounts', async () => {
      const res = await call('GET', '/categories');
      expect(res.status).toBe(200);
      expect(() => CategoryListSchema.parse(res.body)).not.toThrow();
      const body = res.body as { items: Array<{ slug: string; productCount: number }> };
      expect(body.items).toHaveLength(5);
      const ceramics = body.items.find((c) => c.slug === 'ceramics');
      expect(ceramics?.productCount).toBe(5);
    });
  });

  describe('GET /products', () => {
    it('returns default page 1 with 24 items and facets', async () => {
      const res = await call('GET', '/products');
      expect(res.status).toBe(200);
      expect(() => ProductListSchema.parse(res.body)).not.toThrow();
      expect(res.headers['x-request-id']).toMatch(/^req_/);

      const body = res.body as {
        items: Array<{ slug: string }>;
        totalItems: number;
        pageSize: number;
        totalPages: number;
      };
      expect(body.totalItems).toBe(24);
      expect(body.pageSize).toBe(24);
      expect(body.totalPages).toBe(1);
      expect(body.items[0].slug).toBe('ondo-stoneware-mug');
    });

    it('filters by collection, category, q, color, size, price, and inStock', async () => {
      const saleRes = await call('GET', '/products', { collection: 'sale' });
      expect((saleRes.body as { items: unknown[] }).items).toHaveLength(5);

      const newRes = await call('GET', '/products', { collection: 'new' });
      expect((newRes.body as { items: unknown[] }).items).toHaveLength(5);

      const featRes = await call('GET', '/products', { collection: 'featured' });
      expect((featRes.body as { items: unknown[] }).items).toHaveLength(10);

      const bagsRes = await call('GET', '/products', { category: 'bags' });
      expect((bagsRes.body as { items: unknown[] }).items).toHaveLength(5);

      const qRes = await call('GET', '/products', { q: 'MUG' });
      const qItems = (qRes.body as { items: Array<{ slug: string }> }).items;
      expect(qItems.some((p) => p.slug === 'ondo-stoneware-mug')).toBe(true);

      const colorRes = await call('GET', '/products', { color: ['Sand', 'Ink'] });
      const colorItems = (colorRes.body as { items: Array<{ swatches: Array<{ label: string }> }> })
        .items;
      for (const item of colorItems) {
        const labels = item.swatches.map((s) => s.label);
        expect(labels.includes('Sand') || labels.includes('Ink')).toBe(true);
      }

      const sizeRes = await call('GET', '/products', { size: 'King' });
      const sizeItems = (sizeRes.body as { items: Array<{ slug: string }> }).items;
      expect(sizeItems).toHaveLength(1);
      expect(sizeItems[0].slug).toBe('still-bed-linen');

      const priceRes = await call('GET', '/products', {
        minPrice: '100000',
        maxPrice: '200000',
      });
      const priceItems = (priceRes.body as { items: Array<{ price: { amount: number } }> }).items;
      for (const item of priceItems) {
        expect(item.price.amount).toBeGreaterThanOrEqual(100000);
        expect(item.price.amount).toBeLessThanOrEqual(200000);
      }

      const stockRes = await call('GET', '/products', { inStock: 'true' });
      expect((stockRes.body as { items: unknown[] }).items).toHaveLength(23);
    });

    it('computes facets correctly: own facet ignored, other facets preserved, empty result returns empty arrays', async () => {
      const res = await call('GET', '/products', { category: 'ceramics' });
      const body = res.body as {
        facets: {
          categories: Array<{ slug: string; count: number }>;
          colors: Array<{ label: string; count: number }>;
          sizes: Array<{ label: string; count: number }>;
          price: { min: { amount: number }; max: { amount: number } } | null;
        };
      };
      // All 5 categories have count > 0 when category filter is ignored for its own facet
      expect(body.facets.categories).toHaveLength(5);
      const ceramicsTotal = body.facets.categories.find((c) => c.slug === 'ceramics')?.count;
      expect(ceramicsTotal).toBe(5);

      // facets.colors only reflects ceramics products
      const colorLabels = body.facets.colors.map((c) => c.label);
      expect(colorLabels).toContain('Sand');
      expect(colorLabels).toContain('Ink');
      expect(colorLabels).toContain('Moss');
      expect(colorLabels).toContain('Ash');
      expect(colorLabels).toContain('Clay');
      expect(colorLabels).not.toContain('Oat'); // Oat is not in ceramics

      // Empty result gives empty facet arrays and price: null
      const emptyRes = await call('GET', '/products', { q: 'zzzzzz' });
      const emptyBody = emptyRes.body as {
        facets: {
          categories: unknown[];
          colors: unknown[];
          sizes: unknown[];
          price: unknown;
        };
      };
      expect(emptyBody.facets.categories).toHaveLength(0);
      expect(emptyBody.facets.colors).toHaveLength(0);
      expect(emptyBody.facets.sizes).toHaveLength(0);
      expect(emptyBody.facets.price).toBeNull();
    });

    it('sorts by price-asc, price-desc, newest, and name-asc', async () => {
      const pAsc = await call('GET', '/products', { sort: 'price-asc' });
      const pAscItems = (pAsc.body as { items: Array<{ price: { amount: number } }> }).items;
      expect(pAscItems[0].price.amount).toBe(95000);

      const pDesc = await call('GET', '/products', { sort: 'price-desc' });
      const pDescItems = (pDesc.body as { items: Array<{ slug: string }> }).items;
      expect(pDescItems[0].slug).toBe('dusk-floor-lamp');

      const newest = await call('GET', '/products', { sort: 'newest' });
      const newestItems = (newest.body as { items: Array<{ slug: string }> }).items;
      expect(newestItems[0].slug).toBe('commute-backpack');

      const nameAsc = await call('GET', '/products', { sort: 'name-asc' });
      const nameAscItems = (nameAsc.body as { items: Array<{ slug: string }> }).items;
      expect(nameAscItems[0].slug).toBe('arc-table-lamp');
    });

    it('handles pagination and validation errors', async () => {
      const page5 = await call('GET', '/products', { pageSize: '5', page: '5' });
      const p5Body = page5.body as { items: unknown[]; totalPages: number };
      expect(p5Body.items).toHaveLength(4);
      expect(p5Body.totalPages).toBe(5);

      const page99 = await call('GET', '/products', { page: '99' });
      expect((page99.body as { items: unknown[] }).items).toHaveLength(0);

      // Validation errors on non-integer or out of bounds inputs
      const invalidPageSize = await call('GET', '/products', { pageSize: '100' });
      expect(invalidPageSize.status).toBe(400);
      expect(() => ErrorEnvelopeSchema.parse(invalidPageSize.body)).not.toThrow();
      const err = (
        invalidPageSize.body as { error: { code: string; fields: Record<string, string[]> } }
      ).error;
      expect(err.code).toBe('VALIDATION_FAILED');
      expect(err.fields.pageSize).toBeDefined();

      const invalidMinPrice = await call('GET', '/products', { minPrice: '100.5' });
      expect(invalidMinPrice.status).toBe(400);

      const invalidCategory = await call('GET', '/products', { category: 'Bad Slug' });
      expect(invalidCategory.status).toBe(400);

      const invalidInStock = await call('GET', '/products', { inStock: 'bogus' });
      expect(invalidInStock.status).toBe(400);

      const invalidSort = await call('GET', '/products', { sort: 'bogus' });
      expect(invalidSort.status).toBe(400);

      const invalidCollection = await call('GET', '/products', { collection: 'bogus' });
      expect(invalidCollection.status).toBe(400);

      const invalidQ = await call('GET', '/products', { q: 'a'.repeat(101) });
      expect(invalidQ.status).toBe(400);
    });
  });

  describe('GET /products/:slug and /related', () => {
    it('returns Product for valid slug and 404 for unknown slug', async () => {
      const res = await call('GET', '/products/ondo-stoneware-mug');
      expect(res.status).toBe(200);
      expect(() => ProductSchema.parse(res.body)).not.toThrow();
      expect((res.body as { variants: unknown[] }).variants).toHaveLength(3);

      const notFound = await call('GET', '/products/nope');
      expect(notFound.status).toBe(404);
      expect(() => ErrorEnvelopeSchema.parse(notFound.body)).not.toThrow();
      expect((notFound.body as { error: { code: string } }).error.code).toBe('NOT_FOUND');
    });

    it('returns related products with same-category first, out-of-stock last', async () => {
      const res = await call('GET', '/products/ondo-stoneware-mug/related');
      expect(res.status).toBe(200);
      expect(() => RelatedProductsSchema.parse(res.body)).not.toThrow();
      const items = (res.body as { items: Array<{ slug: string }> }).items;
      expect(items.map((i) => i.slug)).toEqual([
        'kiln-serving-bowl',
        'tide-dinner-plates',
        'hollow-bud-vase',
        'drift-linen-throw',
      ]);

      const invalidLimit = await call('GET', '/products/ondo-stoneware-mug/related', {
        limit: '0',
      });
      expect(invalidLimit.status).toBe(400);

      const invalidLimitHigh = await call('GET', '/products/ondo-stoneware-mug/related', {
        limit: '13',
      });
      expect(invalidLimitHigh.status).toBe(400);

      const notFoundRelated = await call('GET', '/products/nope/related');
      expect(notFoundRelated.status).toBe(404);
    });
  });

  describe('GET /search/suggest', () => {
    it('returns empty results when query is shorter than 2 chars', async () => {
      const res = await call('GET', '/search/suggest', { q: 'm' });
      expect(res.status).toBe(200);
      expect(() => SuggestSchema.parse(res.body)).not.toThrow();
      const body = res.body as { products: unknown[]; categories: unknown[] };
      expect(body.products).toHaveLength(0);
      expect(body.categories).toHaveLength(0);
    });

    it('suggests matching products and categories for q="lamp"', async () => {
      const res = await call('GET', '/search/suggest', { q: 'lamp' });
      expect(res.status).toBe(200);
      expect(() => SuggestSchema.parse(res.body)).not.toThrow();
      const body = res.body as {
        products: Array<{ slug: string }>;
        categories: Array<{ slug: string }>;
      };
      expect(body.products.some((p) => p.slug === 'arc-table-lamp')).toBe(true);
      expect(body.products.length).toBeLessThanOrEqual(5);
    });
  });

  describe('POST /newsletter', () => {
    it('validates email and subscribes', async () => {
      const invalid = await call('POST', '/newsletter', undefined, { email: 'x' });
      expect(invalid.status).toBe(400);
      expect(() => ErrorEnvelopeSchema.parse(invalid.body)).not.toThrow();
      const err = (invalid.body as { error: { fields: Record<string, string[]> } }).error;
      expect(err.fields.email).toBeDefined();

      const valid = await call('POST', '/newsletter', undefined, { email: 'test@example.com' });
      expect(valid.status).toBe(202);
      expect(() => NewsletterResultSchema.parse(valid.body)).not.toThrow();
      expect(valid.body).toEqual({ status: 'subscribed' });

      // 415 unsupported media type (including when body is null)
      const badMedia = await call(
        'POST',
        '/newsletter',
        undefined,
        { email: 'test@example.com' },
        { 'content-type': 'text/plain' },
      );
      expect(badMedia.status).toBe(415);

      const nullBodyBadMedia = await call('POST', '/newsletter', undefined, null, {
        'content-type': 'text/plain',
      });
      expect(nullBodyBadMedia.status).toBe(415);
    });
  });

  describe('Unknown routes', () => {
    it('returns 404 NOT_FOUND for unknown path', async () => {
      const res = await call('GET', '/nothing');
      expect(res.status).toBe(404);
      expect((res.body as { error: { code: string } }).error.code).toBe('NOT_FOUND');
    });
  });
});
