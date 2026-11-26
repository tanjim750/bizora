import { apiError, type MockRequest, type MockResponse } from './http';
import * as catalog from './catalog';
import * as cart from './cart';
import * as auth from './auth';
import * as checkout from './checkout';
import * as orders from './orders';

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

    // Catalog & Content
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

    // Cart
    if (method === 'GET' && cleanPath === '/cart') {
      return cart.getCart(req);
    }

    if (method === 'POST' && cleanPath === '/cart/items') {
      return cart.addItem(req);
    }

    if (method === 'PATCH' && cleanPath.startsWith('/cart/items/')) {
      const lineId = cleanPath.slice('/cart/items/'.length);
      if (lineId && !lineId.includes('/')) {
        return cart.updateLine(req, lineId);
      }
    }

    if (method === 'DELETE' && cleanPath.startsWith('/cart/items/')) {
      const lineId = cleanPath.slice('/cart/items/'.length);
      if (lineId && !lineId.includes('/')) {
        return cart.removeLine(req, lineId);
      }
    }

    // Auth
    if (method === 'POST' && cleanPath === '/auth/register') {
      return auth.register(req);
    }

    if (method === 'POST' && cleanPath === '/auth/sign-in') {
      return auth.signIn(req);
    }

    if (method === 'POST' && cleanPath === '/auth/sign-out') {
      return auth.signOut(req);
    }

    if (method === 'GET' && cleanPath === '/auth/me') {
      return auth.me(req);
    }

    // Checkout
    if (method === 'GET' && cleanPath === '/checkout/quote') {
      return checkout.getQuote(req);
    }

    if (method === 'POST' && cleanPath === '/checkout') {
      return checkout.placeOrder(req);
    }

    // Orders
    if (method === 'GET' && cleanPath === '/orders') {
      return orders.listOrders(req);
    }

    if (method === 'GET' && cleanPath.startsWith('/orders/')) {
      const number = cleanPath.slice('/orders/'.length);
      if (number && !number.includes('/')) {
        return orders.getOrder(req, number);
      }
    }

    return apiError(404, 'NOT_FOUND', 'Route not found.');
  } catch {
    return apiError(500, 'INTERNAL', 'Unexpected error.');
  }
}
