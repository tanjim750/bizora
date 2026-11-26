import { z } from 'zod';
import type { Cart, Order, Quote } from '@/lib/api/types';
import {
  apiError,
  CART_COOKIE,
  clearCookie,
  json,
  type MockRequest,
  type MockResponse,
  queryOne,
  SESSION_COOKIE,
  zodFields,
} from './http';
import { findVariant, getDb, type MockOrder, recomputeStock } from './db';
import { buildCart, resolveCart } from './cart';

function randomHex(length: number): string {
  const chars = '0123456789abcdef';
  let out = '';
  for (let i = 0; i < length; i++) {
    out += chars[Math.floor(Math.random() * chars.length)];
  }
  return out;
}

export function stripOrderInternal(mockOrder: MockOrder): Order {
  const order: Partial<MockOrder> = { ...mockOrder };
  delete order.customerId;
  delete order.confirmationToken;
  return order as Order;
}

export function computeQuote(cart: Cart, shippingMethodId: string): Quote {
  const db = getDb();
  const method = db.store.shippingMethods.find((m) => m.id === shippingMethodId);
  if (!method) {
    throw new Error(`Shipping method ${shippingMethodId} not found`);
  }

  const isFree =
    method.freeOverThreshold &&
    db.store.freeShippingThreshold &&
    cart.subtotal.amount >= db.store.freeShippingThreshold.amount;

  const shippingAmount = isFree ? 0 : method.price.amount;
  const shipping = { amount: shippingAmount, currency: db.store.currency };
  const subtotal = cart.subtotal;
  const taxRateBps = db.store.taxRateBps;
  const taxAmount = Math.round(((subtotal.amount + shippingAmount) * taxRateBps) / 10000);
  const tax = { amount: taxAmount, currency: db.store.currency };
  const totalAmount = subtotal.amount + shippingAmount + taxAmount;
  const total = { amount: totalAmount, currency: db.store.currency };

  return {
    subtotal,
    shipping,
    tax,
    total,
    shippingMethodId,
    freeShippingApplied: Boolean(isFree),
    taxRateBps,
    itemCount: cart.itemCount,
  };
}

export function getQuote(req: MockRequest): MockResponse {
  const db = getDb();
  const cart = resolveCart(req);
  if (!cart || cart.lines.length === 0) {
    return apiError(409, 'CART_EMPTY', 'Your cart is empty.');
  }

  const shippingMethodId = queryOne(req.query, 'shippingMethodId');
  if (!shippingMethodId || !db.store.shippingMethods.some((m) => m.id === shippingMethodId)) {
    return apiError(422, 'SHIPPING_METHOD_UNAVAILABLE', 'Please choose another delivery option.');
  }

  const builtCart = buildCart(cart);
  return json(200, computeQuote(builtCart, shippingMethodId));
}

const AddressSchema = z.object({
  firstName: z.string().min(1).max(60),
  lastName: z.string().min(1).max(60),
  line1: z.string().min(3).max(120),
  line2: z.string().max(120).nullable().optional(),
  city: z.string().min(2).max(60),
  postalCode: z.string().regex(/^[A-Za-z0-9 -]{3,10}$/),
  countryCode: z.string(),
});

const PlaceOrderBodySchema = z.object({
  email: z.string().email(),
  phone: z.string().regex(/^\+?[0-9 ()-]{7,20}$/),
  shippingAddress: AddressSchema,
  shippingMethodId: z.string(),
  paymentMethodId: z.string(),
  note: z.string().max(500).nullable().optional(),
  expectedTotal: z.object({
    amount: z.number().int().min(0),
    currency: z.string().length(3),
  }),
});

export function placeOrder(req: MockRequest): MockResponse {
  const db = getDb();

  // 1. missing idempotency-key header -> 400
  const idempotencyKey = req.headers?.['idempotency-key'];
  if (!idempotencyKey) {
    return apiError(400, 'IDEMPOTENCY_KEY_REQUIRED', 'Something went wrong. Please try again.');
  }

  // 2. known key check
  const stored = db.idempotency.get(idempotencyKey);
  if (stored) {
    const bodyHash = JSON.stringify(req.body);
    if (stored.bodyHash === bodyHash) {
      return stored.response;
    }
    return apiError(409, 'IDEMPOTENCY_CONFLICT', 'Something went wrong. Please try again.');
  }

  // 3. zod PlaceOrderBodySchema validation
  const parseResult = PlaceOrderBodySchema.safeParse(req.body);
  if (!parseResult.success) {
    return apiError(400, 'VALIDATION_FAILED', 'Validation failed.', zodFields(parseResult.error));
  }
  const body = parseResult.data;

  // 4. countryCode check
  if (!db.store.countries.some((c) => c.code === body.shippingAddress.countryCode)) {
    return apiError(400, 'VALIDATION_FAILED', 'Validation failed.', {
      'shippingAddress.countryCode': ['Country is not supported.'],
    });
  }

  // 5. empty cart check
  const cart = resolveCart(req);
  if (!cart || cart.lines.length === 0) {
    return apiError(409, 'CART_EMPTY', 'Your cart is empty.');
  }

  // 6. shipping method check
  const shippingMethod = db.store.shippingMethods.find((m) => m.id === body.shippingMethodId);
  if (!shippingMethod) {
    return apiError(422, 'SHIPPING_METHOD_UNAVAILABLE', 'Please choose another delivery option.');
  }

  // 7. payment method check
  const paymentMethod = db.store.paymentMethods.find((m) => m.id === body.paymentMethodId);
  if (!paymentMethod || !paymentMethod.enabled) {
    return apiError(422, 'PAYMENT_METHOD_UNAVAILABLE', 'Please choose another payment method.');
  }

  // 8. out of stock check
  const outOfStockLines: Array<{ lineId: string; variantId: string; available: number }> = [];
  for (const line of cart.lines) {
    const found = findVariant(line.variantId);
    const avail = found ? found.variant.availableQuantity : 0;
    if (line.quantity > avail) {
      outOfStockLines.push({
        lineId: line.id,
        variantId: line.variantId,
        available: avail,
      });
    }
  }
  if (outOfStockLines.length > 0) {
    return apiError(409, 'OUT_OF_STOCK', 'Sorry, this is sold out.', null, {
      lines: outOfStockLines,
    });
  }

  // 9. quote check
  const builtCart = buildCart(cart);
  const quote = computeQuote(builtCart, body.shippingMethodId);
  if (
    body.expectedTotal.amount !== quote.total.amount ||
    body.expectedTotal.currency !== quote.total.currency
  ) {
    return apiError(
      409,
      'PRICE_CHANGED',
      'Prices changed since you started checkout. Please review the new total.',
      null,
      { quote },
    );
  }

  // 10. create order
  const seq = db.nextOrderSeq++;
  const orderNumber = `AUR-1${String(seq).padStart(5, '0')}`;
  const orderId = `ord_${String(seq).padStart(4, '0')}`;
  const confirmationToken = `tok_${randomHex(24)}`;

  const sessionToken = req.cookies[SESSION_COOKIE];
  const customerId = sessionToken ? (db.sessions.get(sessionToken) ?? null) : null;

  const orderLines = cart.lines.map((l, idx) => {
    const { product, variant } = findVariant(l.variantId)!;
    return {
      id: `oline_${seq}_${idx + 1}`,
      productSlug: product.slug,
      productName: product.name,
      variantTitle: variant.title,
      sku: variant.sku,
      image: product.images[0] ?? null,
      unitPrice: variant.price,
      quantity: l.quantity,
      lineTotal: {
        amount: variant.price.amount * l.quantity,
        currency: variant.price.currency,
      },
    };
  });

  const order: MockOrder = {
    id: orderId,
    number: orderNumber,
    status: 'placed',
    paymentStatus: 'pending',
    placedAt: new Date().toISOString(),
    email: body.email,
    phone: body.phone,
    shippingAddress: {
      ...body.shippingAddress,
      line2: body.shippingAddress.line2 ?? null,
    },
    shippingMethod: {
      id: shippingMethod.id,
      label: shippingMethod.label,
      price: quote.shipping,
    },
    paymentMethod: {
      id: paymentMethod.id,
      label: paymentMethod.label,
    },
    lines: orderLines,
    subtotal: quote.subtotal,
    shipping: quote.shipping,
    tax: quote.tax,
    total: quote.total,
    note: body.note ?? null,
    customerId,
    confirmationToken,
  };

  // Decrement stock and recomputeStock
  for (const l of cart.lines) {
    const { product, variant } = findVariant(l.variantId)!;
    variant.availableQuantity -= l.quantity;
    recomputeStock(product);
  }

  // Delete cart
  db.carts.delete(cart.id);

  // Prepend to orders
  db.orders.unshift(order);

  const cleanOrder = stripOrderInternal(order);
  const response = json(201, { order: cleanOrder, confirmationToken }, [clearCookie(CART_COOKIE)]);

  db.idempotency.set(idempotencyKey, {
    bodyHash: JSON.stringify(req.body),
    response,
  });

  return response;
}
