import { z } from 'zod';
import type { Cart, CartLine } from '@/lib/api/types';
import {
  apiError,
  CART_COOKIE,
  cookie,
  json,
  type MockRequest,
  type MockResponse,
  SESSION_COOKIE,
  zodFields,
} from './http';
import { findVariant, getDb, type MockCart } from './db';

export function buildCart(mockCart: MockCart | null): Cart {
  const db = getDb();
  if (!mockCart) {
    return {
      id: null,
      lines: [],
      itemCount: 0,
      subtotal: { amount: 0, currency: db.store.currency },
      freeShippingRemaining: db.store.freeShippingThreshold
        ? { amount: db.store.freeShippingThreshold.amount, currency: db.store.currency }
        : null,
      updatedAt: null,
    };
  }

  const lines: CartLine[] = [];
  let subtotalAmount = 0;
  let itemCount = 0;

  for (const line of mockCart.lines) {
    const found = findVariant(line.variantId);
    if (!found) continue;
    const { product, variant } = found;
    const lineTotalAmount = variant.price.amount * line.quantity;
    subtotalAmount += lineTotalAmount;
    itemCount += line.quantity;

    lines.push({
      id: line.id,
      variantId: line.variantId,
      productSlug: product.slug,
      productName: product.name,
      variantTitle: variant.title,
      image: product.images[0] ?? null,
      unitPrice: variant.price,
      compareAtUnitPrice: variant.compareAtPrice ?? null,
      quantity: line.quantity,
      lineTotal: { amount: lineTotalAmount, currency: variant.price.currency },
      maxQuantity: Math.min(variant.availableQuantity, db.store.maxQuantityPerLine),
      stockStatus: variant.stockStatus,
    });
  }

  const subtotal = { amount: subtotalAmount, currency: db.store.currency };
  const freeShippingRemaining = db.store.freeShippingThreshold
    ? {
        amount: Math.max(0, db.store.freeShippingThreshold.amount - subtotalAmount),
        currency: db.store.currency,
      }
    : null;

  return {
    id: mockCart.id,
    lines,
    itemCount,
    subtotal,
    freeShippingRemaining,
    updatedAt: mockCart.updatedAt,
  };
}

export function resolveCart(req: MockRequest): MockCart | null {
  const db = getDb();
  const sessionToken = req.cookies[SESSION_COOKIE];
  if (sessionToken) {
    const customerId = db.sessions.get(sessionToken);
    if (customerId) {
      for (const cart of db.carts.values()) {
        if (cart.customerId === customerId) {
          return cart;
        }
      }
      return null;
    }
  }

  const cartId = req.cookies[CART_COOKIE];
  if (cartId) {
    const cart = db.carts.get(cartId);
    if (cart && cart.customerId === null) {
      return cart;
    }
  }

  return null;
}

export function getCart(req: MockRequest): MockResponse {
  const cart = resolveCart(req);
  return json(200, buildCart(cart));
}

const AddItemBodySchema = z.object({
  variantId: z.string().min(1),
  quantity: z.number().int().min(1),
});

export function addItem(req: MockRequest): MockResponse {
  const db = getDb();
  const parseResult = AddItemBodySchema.safeParse(req.body);
  if (!parseResult.success) {
    return apiError(400, 'VALIDATION_FAILED', 'Validation failed.', zodFields(parseResult.error));
  }

  const { variantId, quantity } = parseResult.data;
  if (quantity > db.store.maxQuantityPerLine) {
    return apiError(400, 'VALIDATION_FAILED', 'Validation failed.', {
      quantity: [`Must be at most ${db.store.maxQuantityPerLine}.`],
    });
  }

  const found = findVariant(variantId);
  if (!found) {
    return apiError(404, 'VARIANT_NOT_FOUND', 'This option is no longer available.');
  }

  if (found.variant.availableQuantity === 0) {
    return apiError(409, 'OUT_OF_STOCK', 'Sorry, this is sold out.', null, {
      lines: [{ lineId: null, variantId, available: 0 }],
    });
  }

  const cart = resolveCart(req);
  const existingLine = cart?.lines.find((l) => l.variantId === variantId);
  const existingQty = existingLine ? existingLine.quantity : 0;
  const newQty = existingQty + quantity;
  const availableCap = Math.min(found.variant.availableQuantity, db.store.maxQuantityPerLine);

  if (newQty > found.variant.availableQuantity || newQty > db.store.maxQuantityPerLine) {
    return apiError(
      409,
      'INSUFFICIENT_STOCK',
      `Only ${availableCap} left — we've updated the quantity.`,
      null,
      {
        variantId,
        available: availableCap,
      },
    );
  }

  let activeCart = cart;
  const setCookies: string[] = [];

  if (!activeCart) {
    const chars = '0123456789abcdef';
    let hex = '';
    for (let i = 0; i < 8; i++) hex += chars[Math.floor(Math.random() * chars.length)];
    const cartId = `cart_${hex}`;

    const sessionToken = req.cookies[SESSION_COOKIE];
    const customerId = sessionToken ? (db.sessions.get(sessionToken) ?? null) : null;

    activeCart = {
      id: cartId,
      customerId,
      lines: [],
      updatedAt: new Date().toISOString(),
    };
    db.carts.set(cartId, activeCart);

    if (!customerId) {
      setCookies.push(cookie(CART_COOKIE, cartId, 30 * 24 * 3600));
    }
  }

  const lineToUpdate = activeCart.lines.find((l) => l.variantId === variantId);
  if (lineToUpdate) {
    lineToUpdate.quantity = newQty;
  } else {
    const chars = '0123456789abcdef';
    let lineHex = '';
    for (let i = 0; i < 8; i++) lineHex += chars[Math.floor(Math.random() * chars.length)];
    activeCart.lines.push({
      id: `line_${lineHex}`,
      variantId,
      quantity,
    });
  }

  activeCart.updatedAt = new Date().toISOString();
  return json(200, buildCart(activeCart), setCookies);
}

const UpdateLineBodySchema = z.object({
  quantity: z.number().int().min(1),
});

export function updateLine(req: MockRequest, lineId: string): MockResponse {
  const db = getDb();
  const cart = resolveCart(req);
  if (!cart) {
    return apiError(404, 'LINE_NOT_FOUND', 'Your cart was updated.');
  }

  const line = cart.lines.find((l) => l.id === lineId);
  if (!line) {
    return apiError(404, 'LINE_NOT_FOUND', 'Your cart was updated.');
  }

  const parseResult = UpdateLineBodySchema.safeParse(req.body);
  if (!parseResult.success) {
    return apiError(400, 'VALIDATION_FAILED', 'Validation failed.', zodFields(parseResult.error));
  }

  const { quantity } = parseResult.data;
  const found = findVariant(line.variantId);
  if (!found) {
    return apiError(404, 'VARIANT_NOT_FOUND', 'This option is no longer available.');
  }

  const availableCap = Math.min(found.variant.availableQuantity, db.store.maxQuantityPerLine);
  if (quantity > found.variant.availableQuantity || quantity > db.store.maxQuantityPerLine) {
    return apiError(
      409,
      'INSUFFICIENT_STOCK',
      `Only ${availableCap} left — we've updated the quantity.`,
      null,
      {
        variantId: line.variantId,
        available: availableCap,
      },
    );
  }

  line.quantity = quantity;
  cart.updatedAt = new Date().toISOString();
  return json(200, buildCart(cart));
}

export function removeLine(req: MockRequest, lineId: string): MockResponse {
  const cart = resolveCart(req);
  if (!cart) {
    return apiError(404, 'LINE_NOT_FOUND', 'Your cart was updated.');
  }

  const lineIndex = cart.lines.findIndex((l) => l.id === lineId);
  if (lineIndex === -1) {
    return apiError(404, 'LINE_NOT_FOUND', 'Your cart was updated.');
  }

  cart.lines.splice(lineIndex, 1);
  cart.updatedAt = new Date().toISOString();
  return json(200, buildCart(cart));
}
