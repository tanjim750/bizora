import { apiError, type MockRequest, type MockResponse } from './http';
import * as catalog from './catalog';

export async function handleMockRequest(req: MockRequest): Promise<MockResponse> {
  try {
    let cleanPath = req.path.replace(/\/+$/, '');
    if (!cleanPath.startsWith('/')) {
      cleanPath = '/' + cleanPath;
    }

    const headers: Record<string, string> = {};
    if (req.headers) {
      for (const [k, v] of Object.entries(req.headers)) {
        headers[k.toLowerCase()] = v;
      }
    }

    // 415 rule: request with body must have content-type starting with application/json
    if (req.body !== undefined) {
      const contentType = headers['content-type'] ?? '';
      if (!contentType.toLowerCase().startsWith('application/json')) {
        return apiError(415, 'UNSUPPORTED_MEDIA_TYPE', 'Content-Type must be application/json.');
      }
    }

    const method = req.method.toUpperCase();

    // Routes
    if (method === 'GET' && cleanPath === '/store') {
      return catalog.getStore();
    }

    if (method === 'GET' && cleanPath === '/content/home') {
      return catalog.getHomeContent();
    }

    if (method === 'POST' && cleanPath === '/newsletter') {
      return catalog.subscribeNewsletter(req.body);
    }

    if (method === 'GET' && cleanPath === '/categories') {
      return catalog.listCategories();
    }

    if (method === 'GET' && cleanPath === '/products') {
      return catalog.listProducts(req.query);
    }

    if (method === 'GET' && cleanPath.startsWith('/products/')) {
      const remainder = cleanPath.slice('/products/'.length);
      if (remainder.endsWith('/related')) {
        const slug = remainder.slice(0, -'/related'.length);
        if (slug && !slug.includes('/')) {
          return catalog.getRelated(slug, req.query?.limit);
        }
      } else if (!remainder.includes('/')) {
        return catalog.getProduct(remainder);
      }
    }

    if (method === 'GET' && cleanPath === '/search/suggest') {
      return catalog.suggest(req.query?.q);
    }

    return apiError(404, 'NOT_FOUND', 'Route not found.');
  } catch {
    return apiError(500, 'INTERNAL', 'Unexpected error.');
  }
}
