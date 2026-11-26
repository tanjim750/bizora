import type { z } from 'zod';
import {
  CartSchema,
  CategoryListSchema,
  CustomerEnvelopeSchema,
  ErrorEnvelopeSchema,
  HomeContentSchema,
  NewsletterResultSchema,
  OrderListSchema,
  OrderSchema,
  PlaceOrderResultSchema,
  ProductListSchema,
  ProductSchema,
  QuoteSchema,
  RelatedProductsSchema,
  StoreConfigSchema,
  SuggestSchema,
} from './schemas';
import { ApiError } from './errors';
import type {
  ApiRequest,
  Cart,
  Category,
  Customer,
  HomeContent,
  NewsletterResult,
  Order,
  OrderList,
  PlaceOrderBody,
  PlaceOrderResult,
  Product,
  ProductList,
  ProductListQuery,
  ProductSummary,
  Quote,
  StoreConfig,
  Suggest,
  Transport,
} from './types';

async function request<T>(transport: Transport, req: ApiRequest, schema: z.ZodType<T>): Promise<T> {
  const res = await transport(req);

  if (res.status < 200 || res.status >= 300) {
    const errorParsed = ErrorEnvelopeSchema.safeParse(res.body);
    if (errorParsed.success) {
      const err = errorParsed.data.error;
      throw new ApiError(res.status, err.code, err.message, err.fields, err.details, err.requestId);
    }
    throw new ApiError(
      res.status,
      'UNKNOWN',
      typeof res.body === 'string' && res.body ? res.body : 'Unexpected error response',
    );
  }

  const parsed = schema.safeParse(res.body);
  if (!parsed.success) {
    const firstIssue = parsed.error.issues[0];
    const pathStr = firstIssue ? firstIssue.path.join('.') : 'root';
    const msg = firstIssue ? firstIssue.message : 'Validation failed';
    throw new ApiError(502, 'CONTRACT_MISMATCH', `${pathStr}: ${msg}`);
  }

  return parsed.data;
}

async function requestNoContent(transport: Transport, req: ApiRequest): Promise<void> {
  const res = await transport(req);
  if (res.status < 200 || res.status >= 300) {
    const errorParsed = ErrorEnvelopeSchema.safeParse(res.body);
    if (errorParsed.success) {
      const err = errorParsed.data.error;
      throw new ApiError(res.status, err.code, err.message, err.fields, err.details, err.requestId);
    }
    throw new ApiError(res.status, 'UNKNOWN', 'Unexpected error response');
  }
}

export function createApi(transport: Transport) {
  return {
    store: {
      get: (): Promise<StoreConfig> =>
        request(transport, { method: 'GET', path: '/store' }, StoreConfigSchema),
    },

    content: {
      home: (): Promise<HomeContent> =>
        request(transport, { method: 'GET', path: '/content/home' }, HomeContentSchema),
    },

    newsletter: {
      subscribe: (email: string): Promise<NewsletterResult> =>
        request(
          transport,
          { method: 'POST', path: '/newsletter', body: { email } },
          NewsletterResultSchema,
        ),
    },

    catalog: {
      listCategories: async (): Promise<Category[]> => {
        const res = await request(
          transport,
          { method: 'GET', path: '/categories' },
          CategoryListSchema,
        );
        return res.items;
      },

      listProducts: (query: ProductListQuery = {}): Promise<ProductList> =>
        request(
          transport,
          {
            method: 'GET',
            path: '/products',
            query: query as Record<string, string | string[] | undefined>,
          },
          ProductListSchema,
        ),

      getProduct: (slug: string): Promise<Product> =>
        request(
          transport,
          { method: 'GET', path: `/products/${encodeURIComponent(slug)}` },
          ProductSchema,
        ),

      getRelated: async (slug: string, limit = 4): Promise<ProductSummary[]> => {
        const res = await request(
          transport,
          {
            method: 'GET',
            path: `/products/${encodeURIComponent(slug)}/related`,
            query: { limit: String(limit) },
          },
          RelatedProductsSchema,
        );
        return res.items;
      },

      suggest: (q: string): Promise<Suggest> =>
        request(transport, { method: 'GET', path: '/search/suggest', query: { q } }, SuggestSchema),
    },

    cart: {
      get: (): Promise<Cart> => request(transport, { method: 'GET', path: '/cart' }, CartSchema),

      addItem: (body: { variantId: string; quantity: number }): Promise<Cart> =>
        request(transport, { method: 'POST', path: '/cart/items', body }, CartSchema),

      updateLine: (lineId: string, quantity: number): Promise<Cart> =>
        request(
          transport,
          {
            method: 'PATCH',
            path: `/cart/items/${encodeURIComponent(lineId)}`,
            body: { quantity },
          },
          CartSchema,
        ),

      removeLine: (lineId: string): Promise<Cart> =>
        request(
          transport,
          { method: 'DELETE', path: `/cart/items/${encodeURIComponent(lineId)}` },
          CartSchema,
        ),
    },

    auth: {
      register: async (body: {
        firstName: string;
        lastName: string;
        email: string;
        password: string;
      }): Promise<Customer> => {
        const res = await request(
          transport,
          { method: 'POST', path: '/auth/register', body },
          CustomerEnvelopeSchema,
        );
        return res.customer;
      },

      signIn: async (body: { email: string; password: string }): Promise<Customer> => {
        const res = await request(
          transport,
          { method: 'POST', path: '/auth/sign-in', body },
          CustomerEnvelopeSchema,
        );
        return res.customer;
      },

      signOut: (): Promise<void> =>
        requestNoContent(transport, { method: 'POST', path: '/auth/sign-out' }),

      me: async (): Promise<Customer> => {
        const res = await request(
          transport,
          { method: 'GET', path: '/auth/me' },
          CustomerEnvelopeSchema,
        );
        return res.customer;
      },
    },

    checkout: {
      quote: (shippingMethodId: string): Promise<Quote> =>
        request(
          transport,
          { method: 'GET', path: '/checkout/quote', query: { shippingMethodId } },
          QuoteSchema,
        ),

      placeOrder: (body: PlaceOrderBody, idempotencyKey: string): Promise<PlaceOrderResult> =>
        request(
          transport,
          {
            method: 'POST',
            path: '/checkout',
            body,
            headers: { 'Idempotency-Key': idempotencyKey },
          },
          PlaceOrderResultSchema,
        ),
    },

    orders: {
      list: ({
        page = 1,
        pageSize = 10,
      }: { page?: number; pageSize?: number } = {}): Promise<OrderList> =>
        request(
          transport,
          {
            method: 'GET',
            path: '/orders',
            query: { page: String(page), pageSize: String(pageSize) },
          },
          OrderListSchema,
        ),

      get: (number: string, token?: string): Promise<Order> =>
        request(
          transport,
          {
            method: 'GET',
            path: `/orders/${encodeURIComponent(number)}`,
            query: token ? { token } : undefined,
          },
          OrderSchema,
        ),
    },
  };
}

export type StoreApi = ReturnType<typeof createApi>;
