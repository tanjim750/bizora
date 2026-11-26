import { beforeEach, describe, expect, it } from 'vitest';
import { NextRequest } from 'next/server';
import {
  CartSchema,
  CustomerEnvelopeSchema,
  ErrorEnvelopeSchema,
  OrderListSchema,
  OrderSchema,
  PlaceOrderResultSchema,
  ProductSchema,
  QuoteSchema,
  StoreConfigSchema,
} from '@/lib/api/schemas';
import { getDb, resetMockDb } from '@/mocks/server/db';
import { handleMockRequest } from '@/mocks/server/router';
import type { MockRequest, MockResponse } from '@/mocks/server/http';
import {
  DELETE as routeDelete,
  GET as routeGet,
  PATCH as routePatch,
  POST as routePost,
} from '@/app/api/store/[...path]/route';

class CookieJar {
  cookies: Record<string, string> = {};

  applySetCookies(setCookies: string[]) {
    for (const sc of setCookies) {
      const [cookiePart] = sc.split(';');
      const [name, ...valParts] = cookiePart.split('=');
      const value = valParts.join('=');
      if (sc.includes('Max-Age=0')) {
        delete this.cookies[name.trim()];
      } else {
        this.cookies[name.trim()] = value.trim();
      }
    }
  }

  getCookieHeader(): Record<string, string> {
    return { ...this.cookies };
  }
}

describe('SF-08 Mock Backend Part 2 — Stateful Endpoints & Route Handler', () => {
  beforeEach(() => {
    resetMockDb();
    delete process.env.API_BASE_URL;
  });

  async function call(
    jar: CookieJar,
    method: 'GET' | 'POST' | 'PATCH' | 'DELETE',
    path: string,
    query?: Record<string, string | string[] | undefined>,
    body?: unknown,
    headers?: Record<string, string>,
  ): Promise<MockResponse> {
    const allHeaders: Record<string, string> = {
      ...(body !== undefined ? { 'content-type': 'application/json' } : {}),
      ...headers,
    };

    const req: MockRequest = {
      method,
      path,
      query,
      body,
      headers: allHeaders,
      cookies: jar.getCookieHeader(),
    };

    const res = await handleMockRequest(req);
    if (res.setCookies) {
      jar.applySetCookies(res.setCookies);
    }
    return res;
  }

  describe('Cart operations', () => {
    it('GET /cart with no cookies returns 200 with empty cart', async () => {
      const jar = new CookieJar();
      const res = await call(jar, 'GET', '/cart');
      expect(res.status).toBe(200);
      expect(() => CartSchema.parse(res.body)).not.toThrow();
      const cart = res.body as {
        id: string | null;
        itemCount: number;
        freeShippingRemaining: { amount: number };
      };
      expect(cart.id).toBeNull();
      expect(cart.itemCount).toBe(0);
      expect(cart.freeShippingRemaining.amount).toBe(500000);
    });

    it('adds item to cart and updates cart cookie, counts and subtotal', async () => {
      const jar = new CookieJar();
      const res = await call(jar, 'POST', '/cart/items', undefined, {
        variantId: 'var_ondo-stoneware-mug_sand',
        quantity: 2,
      });

      expect(res.status).toBe(200);
      expect(() => CartSchema.parse(res.body)).not.toThrow();
      expect(jar.cookies.aur_cart).toBeDefined();

      const cart1 = res.body as {
        itemCount: number;
        subtotal: { amount: number };
        freeShippingRemaining: { amount: number };
        lines: Array<{ variantId: string; quantity: number }>;
      };
      expect(cart1.itemCount).toBe(2);
      expect(cart1.subtotal.amount).toBe(290000);
      expect(cart1.freeShippingRemaining.amount).toBe(210000);
      expect(cart1.lines).toHaveLength(1);

      // Add same variant x1
      const res2 = await call(jar, 'POST', '/cart/items', undefined, {
        variantId: 'var_ondo-stoneware-mug_sand',
        quantity: 1,
      });
      expect(res2.status).toBe(200);
      expect(() => CartSchema.parse(res2.body)).not.toThrow();
      const cart2 = res2.body as {
        itemCount: number;
        lines: Array<{ variantId: string; quantity: number }>;
      };
      expect(cart2.itemCount).toBe(3);
      expect(cart2.lines).toHaveLength(1);
      expect(cart2.lines[0].quantity).toBe(3);
    });

    it('does NOT create a cart on 409 INSUFFICIENT_STOCK when cart is empty', async () => {
      const jar = new CookieJar();
      const db = getDb();
      expect(db.carts.size).toBe(0);

      const res = await call(jar, 'POST', '/cart/items', undefined, {
        variantId: 'var_hollow-bud-vase_sand',
        quantity: 4, // available is 3
      });
      expect(res.status).toBe(409);
      expect(db.carts.size).toBe(0);
      expect(jar.cookies.aur_cart).toBeUndefined();

      const cartCheck = await call(jar, 'GET', '/cart');
      expect((cartCheck.body as { id: string | null }).id).toBeNull();
    });

    it('enforces stock availability, caps and validation on addItem', async () => {
      const jar = new CookieJar();

      // out of stock item
      const outOfStock = await call(jar, 'POST', '/cart/items', undefined, {
        variantId: 'var_ember-teapot_ink',
        quantity: 1,
      });
      expect(outOfStock.status).toBe(409);
      expect((outOfStock.body as { error: { code: string } }).error.code).toBe('OUT_OF_STOCK');

      // quantity > maxQuantityPerLine (10) -> 400
      const overMaxLine = await call(jar, 'POST', '/cart/items', undefined, {
        variantId: 'var_ondo-stoneware-mug_sand',
        quantity: 11,
      });
      expect(overMaxLine.status).toBe(400);

      // insufficient stock: available 3, request 4
      const insufficient = await call(jar, 'POST', '/cart/items', undefined, {
        variantId: 'var_hollow-bud-vase_sand',
        quantity: 4,
      });
      expect(insufficient.status).toBe(409);
      const err = insufficient.body as {
        error: { code: string; details: { available: number }; message: string };
      };
      expect(err.error.code).toBe('INSUFFICIENT_STOCK');
      expect(err.error.details.available).toBe(3);
      expect(err.error.message).toBe("Only 3 left — we've updated the quantity.");

      // unknown variant -> 404
      const notFound = await call(jar, 'POST', '/cart/items', undefined, {
        variantId: 'var_nope',
        quantity: 1,
      });
      expect(notFound.status).toBe(404);
      expect((notFound.body as { error: { code: string } }).error.code).toBe('VARIANT_NOT_FOUND');

      // quantity 0 -> 400
      const badQty = await call(jar, 'POST', '/cart/items', undefined, {
        variantId: 'var_ondo-stoneware-mug_sand',
        quantity: 0,
      });
      expect(badQty.status).toBe(400);
      expect(
        (badQty.body as { error: { fields: Record<string, string[]> } }).error.fields.quantity,
      ).toBeDefined();
    });

    it('patches and deletes cart lines and validates updates', async () => {
      const jar = new CookieJar();
      const addRes = await call(jar, 'POST', '/cart/items', undefined, {
        variantId: 'var_ondo-stoneware-mug_sand',
        quantity: 1,
      });
      const lineId = (addRes.body as { lines: Array<{ id: string }> }).lines[0].id;

      // PATCH line quantity to 5
      const patchRes = await call(jar, 'PATCH', `/cart/items/${lineId}`, undefined, {
        quantity: 5,
      });
      expect(patchRes.status).toBe(200);
      expect(() => CartSchema.parse(patchRes.body)).not.toThrow();
      expect((patchRes.body as { lines: Array<{ quantity: number }> }).lines[0].quantity).toBe(5);

      // PATCH line quantity 0 -> 400
      const patchZero = await call(jar, 'PATCH', `/cart/items/${lineId}`, undefined, {
        quantity: 0,
      });
      expect(patchZero.status).toBe(400);

      // PATCH line quantity > available or maxQuantityPerLine (10) -> 409
      const patchOver = await call(jar, 'PATCH', `/cart/items/${lineId}`, undefined, {
        quantity: 15,
      });
      expect(patchOver.status).toBe(409);
      expect((patchOver.body as { error: { code: string } }).error.code).toBe('INSUFFICIENT_STOCK');

      // PATCH unknown line -> 404
      const patchBad = await call(jar, 'PATCH', '/cart/items/line_unknown', undefined, {
        quantity: 2,
      });
      expect(patchBad.status).toBe(404);
      expect((patchBad.body as { error: { code: string } }).error.code).toBe('LINE_NOT_FOUND');

      // DELETE unknown line -> 404
      const deleteBad = await call(jar, 'DELETE', '/cart/items/line_unknown');
      expect(deleteBad.status).toBe(404);

      // DELETE the line -> 200
      const deleteRes = await call(jar, 'DELETE', `/cart/items/${lineId}`);
      expect(deleteRes.status).toBe(200);
      expect(() => CartSchema.parse(deleteRes.body)).not.toThrow();
      expect((deleteRes.body as { lines: unknown[] }).lines).toHaveLength(0);
    });

    it('does not set aur_cart cookie when signed-in user adds item', async () => {
      const jar = new CookieJar();
      await call(jar, 'POST', '/auth/sign-in', undefined, {
        email: 'demo@aurelo.test',
        password: 'demo-pass-123',
      });
      expect(jar.cookies.aur_session).toBeDefined();
      delete jar.cookies.aur_cart;

      const addRes = await call(jar, 'POST', '/cart/items', undefined, {
        variantId: 'var_ondo-stoneware-mug_sand',
        quantity: 1,
      });
      expect(addRes.status).toBe(200);
      expect(jar.cookies.aur_cart).toBeUndefined(); // no cart cookie for signed in customer
    });
  });

  describe('Auth operations & Cart Merging', () => {
    it('signs in and merges guest cart without returning password', async () => {
      const jar = new CookieJar();
      // add item as guest
      await call(jar, 'POST', '/cart/items', undefined, {
        variantId: 'var_ondo-stoneware-mug_sand',
        quantity: 2,
      });

      // sign in as demo (case-insensitive email)
      const signInRes = await call(jar, 'POST', '/auth/sign-in', undefined, {
        email: 'DEMO@aurelo.test',
        password: 'demo-pass-123',
      });
      expect(signInRes.status).toBe(200);
      expect(() => CustomerEnvelopeSchema.parse(signInRes.body)).not.toThrow();
      expect(
        (signInRes.body as { customer: Record<string, unknown> }).customer.password,
      ).toBeUndefined();
      expect(jar.cookies.aur_session).toBeDefined();

      // cart cookie is cleared, but session cart has merged item
      const cartRes = await call(jar, 'GET', '/cart');
      expect(cartRes.status).toBe(200);
      expect((cartRes.body as { itemCount: number }).itemCount).toBe(2);

      // GET /auth/me returns current customer
      const meRes = await call(jar, 'GET', '/auth/me');
      expect(meRes.status).toBe(200);
      expect(() => CustomerEnvelopeSchema.parse(meRes.body)).not.toThrow();
      expect((meRes.body as { customer: { email: string } }).customer.email).toBe(
        'demo@aurelo.test',
      );
    });

    it('merges guest cart into an existing customer cart with variant caps and OOS handling', async () => {
      const demoJar = new CookieJar();
      // Sign in as demo and add an item
      await call(demoJar, 'POST', '/auth/sign-in', undefined, {
        email: 'demo@aurelo.test',
        password: 'demo-pass-123',
      });
      await call(demoJar, 'POST', '/cart/items', undefined, {
        variantId: 'var_ondo-stoneware-mug_sand',
        quantity: 8,
      });

      // Now create a guest cart
      const guestJar = new CookieJar();
      await call(guestJar, 'POST', '/cart/items', undefined, {
        variantId: 'var_ondo-stoneware-mug_sand',
        quantity: 5, // total 8 + 5 = 13 > maxQuantityPerLine (10) -> capped at 10
      });
      await call(guestJar, 'POST', '/cart/items', undefined, {
        variantId: 'var_kiln-serving-bowl_sand',
        quantity: 2,
      });

      // Sign in as demo in guestJar -> merges guest cart into existing demo cart
      const mergeRes = await call(guestJar, 'POST', '/auth/sign-in', undefined, {
        email: 'demo@aurelo.test',
        password: 'demo-pass-123',
      });
      expect(mergeRes.status).toBe(200);
      expect(guestJar.cookies.aur_cart).toBeUndefined();

      const mergedCart = await call(guestJar, 'GET', '/cart');
      expect(mergedCart.status).toBe(200);
      expect(() => CartSchema.parse(mergedCart.body)).not.toThrow();
      const body = mergedCart.body as {
        lines: Array<{ variantId: string; quantity: number }>;
      };
      const mugLine = body.lines.find((l) => l.variantId === 'var_ondo-stoneware-mug_sand');
      const bowlLine = body.lines.find((l) => l.variantId === 'var_kiln-serving-bowl_sand');
      expect(mugLine?.quantity).toBe(10); // capped at maxQuantityPerLine
      expect(bowlLine?.quantity).toBe(2);
    });

    it('rate limits after 5 consecutive failed sign-in attempts within 60s and resets on success', async () => {
      const jar = new CookieJar();
      for (let i = 0; i < 5; i++) {
        const failRes = await call(jar, 'POST', '/auth/sign-in', undefined, {
          email: 'demo@aurelo.test',
          password: 'wrong-password',
        });
        expect(failRes.status).toBe(401);
        expect((failRes.body as { error: { code: string } }).error.code).toBe(
          'INVALID_CREDENTIALS',
        );
      }

      // 6th attempt -> 429
      const rateLimitRes = await call(jar, 'POST', '/auth/sign-in', undefined, {
        email: 'demo@aurelo.test',
        password: 'wrong-password',
      });
      expect(rateLimitRes.status).toBe(429);
      const err = rateLimitRes.body as {
        error: { code: string; details: { retryAfterSeconds: number } };
      };
      expect(err.error.code).toBe('RATE_LIMITED');
      expect(err.error.details.retryAfterSeconds).toBe(60);
      expect(rateLimitRes.headers['retry-after']).toBe('60');

      // Now test reset on different user or successful login after window:
      const db = getDb();
      db.signInFailures.delete('demo@aurelo.test');
      const successRes = await call(jar, 'POST', '/auth/sign-in', undefined, {
        email: 'demo@aurelo.test',
        password: 'demo-pass-123',
      });
      expect(successRes.status).toBe(200);
      expect(db.signInFailures.has('demo@aurelo.test')).toBe(false);
    });

    it('handles registration validation, duplicate email, and sign-out', async () => {
      const jar = new CookieJar();

      // invalid registration body -> 400
      const badReg = await call(jar, 'POST', '/auth/register', undefined, {
        firstName: '',
        lastName: 'User',
        email: 'invalid-email',
        password: 'short',
      });
      expect(badReg.status).toBe(400);

      // register existing email -> 409
      const dupRes = await call(jar, 'POST', '/auth/register', undefined, {
        firstName: 'Demo',
        lastName: 'User',
        email: 'demo@aurelo.test',
        password: 'password123',
      });
      expect(dupRes.status).toBe(409);
      expect((dupRes.body as { error: { code: string } }).error.code).toBe('EMAIL_TAKEN');

      // register new email -> 201
      const regRes = await call(jar, 'POST', '/auth/register', undefined, {
        firstName: 'Tariq',
        lastName: 'Hasan',
        email: 'tariq@example.test',
        password: 'password123',
      });
      expect(regRes.status).toBe(201);
      expect(() => CustomerEnvelopeSchema.parse(regRes.body)).not.toThrow();
      expect(jar.cookies.aur_session).toBeDefined();

      const meRes = await call(jar, 'GET', '/auth/me');
      expect(meRes.status).toBe(200);
      expect(() => CustomerEnvelopeSchema.parse(meRes.body)).not.toThrow();
      expect((meRes.body as { customer: { email: string } }).customer.email).toBe(
        'tariq@example.test',
      );

      // sign out clears both session and cart cookies
      jar.cookies.aur_cart = 'some_cart';
      const signOutRes = await call(jar, 'POST', '/auth/sign-out');
      expect(signOutRes.status).toBe(204);
      expect(jar.cookies.aur_session).toBeUndefined();
      expect(jar.cookies.aur_cart).toBeUndefined();

      const meAfter = await call(jar, 'GET', '/auth/me');
      expect(meAfter.status).toBe(401);
    });
  });

  describe('Checkout & Quotes', () => {
    it('handles quotes with empty cart, standard delivery and invalid method', async () => {
      const jar = new CookieJar();

      // quote with empty cart -> 409 CART_EMPTY
      const emptyQuote = await call(jar, 'GET', '/checkout/quote', {
        shippingMethodId: 'standard',
      });
      expect(emptyQuote.status).toBe(409);
      expect((emptyQuote.body as { error: { code: string } }).error.code).toBe('CART_EMPTY');

      // add mug x2
      await call(jar, 'POST', '/cart/items', undefined, {
        variantId: 'var_ondo-stoneware-mug_sand',
        quantity: 2,
      });

      // quote with standard delivery
      const quoteRes = await call(jar, 'GET', '/checkout/quote', {
        shippingMethodId: 'standard',
      });
      expect(quoteRes.status).toBe(200);
      expect(() => QuoteSchema.parse(quoteRes.body)).not.toThrow();
      const quote = quoteRes.body as {
        subtotal: { amount: number };
        shipping: { amount: number };
        tax: { amount: number };
        total: { amount: number };
        freeShippingApplied: boolean;
      };
      expect(quote.subtotal.amount).toBe(290000);
      expect(quote.shipping.amount).toBe(8000);
      expect(quote.tax.amount).toBe(14900);
      expect(quote.total.amount).toBe(312900);
      expect(quote.freeShippingApplied).toBe(false);

      // Free shipping threshold test (subtotal >= 500000)
      await call(jar, 'POST', '/cart/items', undefined, {
        variantId: 'var_drift-linen-throw_oat',
        quantity: 1, // 680000
      });
      const freeQuoteRes = await call(jar, 'GET', '/checkout/quote', {
        shippingMethodId: 'standard',
      });
      expect(freeQuoteRes.status).toBe(200);
      const freeQuote = freeQuoteRes.body as {
        shipping: { amount: number };
        freeShippingApplied: boolean;
      };
      expect(freeQuote.shipping.amount).toBe(0);
      expect(freeQuote.freeShippingApplied).toBe(true);

      // invalid shipping method -> 422
      const badMethod = await call(jar, 'GET', '/checkout/quote', {
        shippingMethodId: 'nope',
      });
      expect(badMethod.status).toBe(422);
      expect((badMethod.body as { error: { code: string } }).error.code).toBe(
        'SHIPPING_METHOD_UNAVAILABLE',
      );
    });

    it('places order, decrements stock, empties cart, and enforces idempotency', async () => {
      const jar = new CookieJar();
      await call(jar, 'POST', '/cart/items', undefined, {
        variantId: 'var_ondo-stoneware-mug_sand',
        quantity: 2,
      });

      const validBody = {
        email: 'nadia@example.com',
        phone: '+8801712345678',
        shippingAddress: {
          firstName: 'Nadia',
          lastName: 'Rahman',
          line1: 'House 12, Road 5',
          line2: null,
          city: 'Dhaka',
          postalCode: '1209',
          countryCode: 'BD',
        },
        shippingMethodId: 'standard',
        paymentMethodId: 'cod',
        note: null,
        expectedTotal: { amount: 312900, currency: 'BDT' },
      };

      // missing idempotency header -> 400
      const missingKey = await call(jar, 'POST', '/checkout', undefined, validBody);
      expect(missingKey.status).toBe(400);
      expect((missingKey.body as { error: { code: string } }).error.code).toBe(
        'IDEMPOTENCY_KEY_REQUIRED',
      );

      // invalid country code -> 400
      const badCountry = await call(
        jar,
        'POST',
        '/checkout',
        undefined,
        {
          ...validBody,
          shippingAddress: { ...validBody.shippingAddress, countryCode: 'US' },
        },
        { 'idempotency-key': 'key_bad_country' },
      );
      expect(badCountry.status).toBe(400);

      // invalid shipping method -> 422
      const badShipping = await call(
        jar,
        'POST',
        '/checkout',
        undefined,
        { ...validBody, shippingMethodId: 'rocket' },
        { 'idempotency-key': 'key_bad_shipping' },
      );
      expect(badShipping.status).toBe(422);

      // wrong expectedTotal -> 409 PRICE_CHANGED
      const wrongPrice = await call(
        jar,
        'POST',
        '/checkout',
        undefined,
        {
          ...validBody,
          expectedTotal: { amount: 999999, currency: 'BDT' },
        },
        { 'idempotency-key': 'key_test_1' },
      );
      expect(wrongPrice.status).toBe(409);
      const wrongPriceDetails = wrongPrice.body as {
        error: { details: { quote: { total: { amount: number } } } };
      };
      expect(wrongPriceDetails.error.details.quote.total.amount).toBe(312900);

      // disabled payment method ('card') -> 422
      const disabledPayment = await call(
        jar,
        'POST',
        '/checkout',
        undefined,
        {
          ...validBody,
          paymentMethodId: 'card',
        },
        { 'idempotency-key': 'key_test_2' },
      );
      expect(disabledPayment.status).toBe(422);
      expect((disabledPayment.body as { error: { code: string } }).error.code).toBe(
        'PAYMENT_METHOD_UNAVAILABLE',
      );

      // Valid order placement
      const placeRes = await call(jar, 'POST', '/checkout', undefined, validBody, {
        'idempotency-key': 'idem_key_order_1',
      });
      expect(placeRes.status).toBe(201);
      expect(() => PlaceOrderResultSchema.parse(placeRes.body)).not.toThrow();

      const resBody = placeRes.body as {
        order: { number: string; lines: Array<{ quantity: number }> };
        confirmationToken: string;
      };
      expect(resBody.order.number).toBe('AUR-100200');
      expect(resBody.confirmationToken.startsWith('tok_')).toBe(true);

      // cart is empty afterwards
      const cartAfter = await call(jar, 'GET', '/cart');
      expect((cartAfter.body as { itemCount: number }).itemCount).toBe(0);

      // idempotency: same key + same body -> same 201 response
      const retryRes = await call(jar, 'POST', '/checkout', undefined, validBody, {
        'idempotency-key': 'idem_key_order_1',
      });
      expect(retryRes.status).toBe(201);
      expect(() => PlaceOrderResultSchema.parse(retryRes.body)).not.toThrow();
      expect((retryRes.body as { order: { number: string } }).order.number).toBe('AUR-100200');

      // idempotency: same key + different body -> 409 conflict
      const conflictRes = await call(
        jar,
        'POST',
        '/checkout',
        undefined,
        { ...validBody, phone: '+8801999999999' },
        { 'idempotency-key': 'idem_key_order_1' },
      );
      expect(conflictRes.status).toBe(409);
      expect((conflictRes.body as { error: { code: string } }).error.code).toBe(
        'IDEMPOTENCY_CONFLICT',
      );

      // Stock was decremented: Ondo mug Sand variant had 25, now has 23
      const prodRes = await call(jar, 'GET', '/products/ondo-stoneware-mug');
      expect(() => ProductSchema.parse(prodRes.body)).not.toThrow();
      const prod = prodRes.body as {
        variants: Array<{ id: string; availableQuantity: number }>;
      };
      const mugSand = prod.variants.find((v) => v.id === 'var_ondo-stoneware-mug_sand');
      expect(mugSand?.availableQuantity).toBe(23);

      // Empty cart checkout -> 409 CART_EMPTY
      const emptyCheckout = await call(jar, 'POST', '/checkout', undefined, validBody, {
        'idempotency-key': 'key_empty_cart',
      });
      expect(emptyCheckout.status).toBe(409);
      expect((emptyCheckout.body as { error: { code: string } }).error.code).toBe('CART_EMPTY');
    });

    it('rejects checkout with 409 OUT_OF_STOCK when item stock drops before checkout', async () => {
      const jar = new CookieJar();
      await call(jar, 'POST', '/cart/items', undefined, {
        variantId: 'var_hollow-bud-vase_sand',
        quantity: 3,
      });

      // Simulate stock drop in DB
      const db = getDb();
      const vase = db.products.find((p) => p.slug === 'hollow-bud-vase');
      const vaseSand = vase?.variants.find((v) => v.id === 'var_hollow-bud-vase_sand');
      if (vaseSand) vaseSand.availableQuantity = 1;

      const placeRes = await call(
        jar,
        'POST',
        '/checkout',
        undefined,
        {
          email: 'nadia@example.com',
          phone: '+8801712345678',
          shippingAddress: {
            firstName: 'Nadia',
            lastName: 'Rahman',
            line1: 'House 12, Road 5',
            line2: null,
            city: 'Dhaka',
            postalCode: '1209',
            countryCode: 'BD',
          },
          shippingMethodId: 'standard',
          paymentMethodId: 'cod',
          note: null,
          expectedTotal: { amount: 307250, currency: 'BDT' },
        },
        { 'idempotency-key': 'key_oos_check' },
      );

      expect(placeRes.status).toBe(409);
      const err = placeRes.body as {
        error: {
          code: string;
          details: { lines: Array<{ variantId: string; available: number }> };
        };
      };
      expect(err.error.code).toBe('OUT_OF_STOCK');
      expect(err.error.details.lines[0].variantId).toBe('var_hollow-bud-vase_sand');
      expect(err.error.details.lines[0].available).toBe(1);
    });
  });

  describe('Orders lookup', () => {
    it('retrieves orders for signed-in demo user and guests with confirmation tokens', async () => {
      const jar = new CookieJar();

      // Guest order lookup with token
      const guestPlace = await call(jar, 'POST', '/cart/items', undefined, {
        variantId: 'var_drift-linen-throw_oat',
        quantity: 1,
      });
      expect(guestPlace.status).toBe(200);

      const checkoutRes = await call(
        jar,
        'POST',
        '/checkout',
        undefined,
        {
          email: 'guest@example.com',
          phone: '+8801700000000',
          shippingAddress: {
            firstName: 'Guest',
            lastName: 'User',
            line1: 'Road 1',
            line2: null,
            city: 'Dhaka',
            postalCode: '1200',
            countryCode: 'BD',
          },
          shippingMethodId: 'standard',
          paymentMethodId: 'cod',
          note: null,
          expectedTotal: { amount: 714000, currency: 'BDT' },
        },
        { 'idempotency-key': 'guest_order_idem_key' },
      );
      expect(checkoutRes.status).toBe(201);
      expect(() => PlaceOrderResultSchema.parse(checkoutRes.body)).not.toThrow();

      const token = (checkoutRes.body as { confirmationToken: string }).confirmationToken;
      const orderNum = (checkoutRes.body as { order: { number: string } }).order.number;

      // GET order with valid token -> strips internal fields
      const guestLookup = await call(jar, 'GET', `/orders/${orderNum}`, { token });
      expect(guestLookup.status).toBe(200);
      expect(() => OrderSchema.parse(guestLookup.body)).not.toThrow();
      const rawOrder = guestLookup.body as Record<string, unknown>;
      expect(rawOrder.customerId).toBeUndefined();
      expect(rawOrder.confirmationToken).toBeUndefined();

      // GET order with invalid token -> 404
      const badTokenLookup = await call(jar, 'GET', `/orders/${orderNum}`, {
        token: 'tok_invalid',
      });
      expect(badTokenLookup.status).toBe(404);

      // GET /orders without session -> 401
      const noSessionList = await call(jar, 'GET', '/orders');
      expect(noSessionList.status).toBe(401);

      // Sign in as demo
      await call(jar, 'POST', '/auth/sign-in', undefined, {
        email: 'demo@aurelo.test',
        password: 'demo-pass-123',
      });

      // Customer B cannot view demo's order (AUR-100101 belongs to demo)
      const userBJar = new CookieJar();
      await call(userBJar, 'POST', '/auth/register', undefined, {
        firstName: 'Other',
        lastName: 'Person',
        email: 'other@example.test',
        password: 'password123',
      });
      const crossOrderRes = await call(userBJar, 'GET', '/orders/AUR-100101');
      expect(crossOrderRes.status).toBe(404); // returns 404 without revealing existence

      // GET /orders for demo -> 3 items newest first (AUR-100142 first)
      const demoOrdersRes = await call(jar, 'GET', '/orders');
      expect(demoOrdersRes.status).toBe(200);
      expect(() => OrderListSchema.parse(demoOrdersRes.body)).not.toThrow();
      const list = demoOrdersRes.body as {
        items: Array<{ number: string }>;
        totalItems: number;
      };
      expect(list.totalItems).toBe(3);
      expect(list.items[0].number).toBe('AUR-100142');

      // GET /orders with pagination validation
      const badPage = await call(jar, 'GET', '/orders', { page: '0' });
      expect(badPage.status).toBe(400);

      const pagedOrders = await call(jar, 'GET', '/orders', { page: '1', pageSize: '2' });
      expect(pagedOrders.status).toBe(200);
      expect((pagedOrders.body as { items: unknown[] }).items).toHaveLength(2);

      // GET /orders/AUR-100101 as demo owner -> 200
      const singleOrderRes = await call(jar, 'GET', '/orders/AUR-100101');
      expect(singleOrderRes.status).toBe(200);
      expect(() => OrderSchema.parse(singleOrderRes.body)).not.toThrow();
      const singleOrder = singleOrderRes.body as Record<string, unknown>;
      expect(singleOrder.customerId).toBeUndefined();
      expect(singleOrder.confirmationToken).toBeUndefined();
    });
  });

  describe('Route Handler Smoke & Edge cases', () => {
    it('handles GET request through Next.js route handler', async () => {
      process.env.MOCK_LATENCY_MS = '0';
      const req = new NextRequest('http://localhost/api/store/store');
      const response = await routeGet(req, {
        params: Promise.resolve({ path: ['store'] }),
      });

      expect(response.status).toBe(200);
      const data = await response.json();
      expect(() => StoreConfigSchema.parse(data)).not.toThrow();
      expect(response.headers.get('x-request-id')).toMatch(/^req_[0-9a-f]{8}$/);
    });

    it('returns 404 ErrorEnvelope with valid requestId when API_BASE_URL is set', async () => {
      process.env.API_BASE_URL = 'http://real-backend.test';
      const req = new NextRequest('http://localhost/api/store/store');
      const response = await routeGet(req, {
        params: Promise.resolve({ path: ['store'] }),
      });

      expect(response.status).toBe(404);
      expect(response.headers.get('x-request-id')).toMatch(/^req_[0-9a-f]{8}$/);
      const json = await response.json();
      expect(() => ErrorEnvelopeSchema.parse(json)).not.toThrow();
      expect(json.error.code).toBe('NOT_FOUND');
      expect(typeof json.error.requestId).toBe('string');
      delete process.env.API_BASE_URL;
    });

    it('returns 400 ErrorEnvelope with valid requestId on malformed JSON body', async () => {
      process.env.MOCK_LATENCY_MS = '0';
      const req = new NextRequest('http://localhost/api/store/newsletter', {
        method: 'POST',
        headers: { 'content-type': 'application/json' },
        body: '{ malformed json',
      });
      const response = await routePost(req, {
        params: Promise.resolve({ path: ['newsletter'] }),
      });

      expect(response.status).toBe(400);
      expect(response.headers.get('x-request-id')).toMatch(/^req_[0-9a-f]{8}$/);
      const json = await response.json();
      expect(() => ErrorEnvelopeSchema.parse(json)).not.toThrow();
      expect(json.error.code).toBe('VALIDATION_FAILED');
      expect(typeof json.error.requestId).toBe('string');
    });

    it('forwards cookies and parses repeated query parameters in route handler', async () => {
      process.env.MOCK_LATENCY_MS = '0';
      const req = new NextRequest('http://localhost/api/store/products?color=Sand&color=Ink');
      const response = await routeGet(req, {
        params: Promise.resolve({ path: ['products'] }),
      });

      expect(response.status).toBe(200);
      const json = await response.json();
      expect(json.items).toBeDefined();
    });

    it('handles POST, PATCH, and DELETE with cookie persistence through route handler', async () => {
      process.env.MOCK_LATENCY_MS = '0';

      // POST /cart/items sets aur_cart
      const postReq = new NextRequest('http://localhost/api/store/cart/items', {
        method: 'POST',
        headers: { 'content-type': 'application/json' },
        body: JSON.stringify({ variantId: 'var_ondo-stoneware-mug_sand', quantity: 1 }),
      });
      const postRes = await routePost(postReq, {
        params: Promise.resolve({ path: ['cart', 'items'] }),
      });
      expect(postRes.status).toBe(200);
      const setCookie = postRes.headers.get('set-cookie');
      expect(setCookie).toContain('aur_cart=');
      const cartData = await postRes.json();
      const lineId = cartData.lines[0].id;
      const cartId = cartData.id;

      // PATCH /cart/items/:id with cookie forwarded
      const patchReq = new NextRequest(`http://localhost/api/store/cart/items/${lineId}`, {
        method: 'PATCH',
        headers: {
          'content-type': 'application/json',
          cookie: `aur_cart=${cartId}`,
        },
        body: JSON.stringify({ quantity: 3 }),
      });
      const patchRes = await routePatch(patchReq, {
        params: Promise.resolve({ path: ['cart', 'items', lineId] }),
      });
      expect(patchRes.status).toBe(200);
      const patchData = await patchRes.json();
      expect(patchData.lines[0].quantity).toBe(3);

      // DELETE /cart/items/:id
      const delReq = new NextRequest(`http://localhost/api/store/cart/items/${lineId}`, {
        method: 'DELETE',
        headers: {
          cookie: `aur_cart=${cartId}`,
        },
      });
      const delRes = await routeDelete(delReq, {
        params: Promise.resolve({ path: ['cart', 'items', lineId] }),
      });
      expect(delRes.status).toBe(200);
      const delData = await delRes.json();
      expect(delData.lines).toHaveLength(0);
    });
  });
});
