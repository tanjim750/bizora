import { describe, expect, it } from 'vitest';
import storeJson from '@/mocks/fixtures/store.json';
import { StoreConfigSchema, PlaceOrderBodySchema } from '@/lib/api/schemas';
import {
  emptyCheckoutValues,
  validateCheckout,
  validateField,
  toPlaceOrderBody,
  mapApiFieldErrors,
} from '@/lib/checkout/validation';
import { createAttemptKeys } from '@/lib/checkout/idempotency';

const store = StoreConfigSchema.parse(storeJson);

const uuidV4Regex =
  /^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;

describe('SF-26 Checkout logic', () => {
  it('initializes empty checkout values from store', () => {
    const values = emptyCheckoutValues(store);
    expect(values.countryCode).toBe('BD');
    expect(values.shippingMethodId).toBe('standard');
    expect(values.paymentMethodId).toBe('cod');
  });

  it('validates all-empty values with default ids and returns exact messages', () => {
    const values = emptyCheckoutValues(store);
    const result = validateCheckout(values, store);

    expect(result.ok).toBe(false);
    if (!result.ok) {
      expect(result.errors.email).toBe('Enter your email address.');
      expect(result.errors.phone).toBe('Enter a phone number we can call.');
      expect(result.errors.firstName).toBe('Enter your first name.');
      expect(result.errors.lastName).toBe('Enter your last name.');
      expect(result.errors.line1).toBe('Enter your street address.');
      expect(result.errors.city).toBe('Enter your city.');
      expect(result.errors.postalCode).toBe('Enter a valid postal code.');
      expect(result.errors.line2).toBeUndefined();
      expect(result.errors.note).toBeUndefined();
    }
  });

  it('validates a valid set (§5.5 example) and formats body correctly', () => {
    const validValues = {
      email: '  nadia@example.com  ',
      phone: '+8801712345678',
      firstName: 'Nadia',
      lastName: 'Rahman',
      line1: 'House 12, Road 5',
      line2: '   ',
      city: 'Dhaka',
      postalCode: '1209',
      countryCode: 'BD',
      shippingMethodId: 'standard',
      paymentMethodId: 'cod',
      note: '',
    };

    const result = validateCheckout(validValues, store);
    expect(result.ok).toBe(true);
    if (result.ok) {
      expect(result.body.email).toBe('nadia@example.com');
      expect(result.body.shippingAddress.line2).toBeNull();
      expect(result.body.note).toBeNull();
    }
  });

  it('validates edge cases for payment method, note, and phone', () => {
    const values = {
      ...emptyCheckoutValues(store),
      paymentMethodId: 'card', // disabled in fixtures
      note: 'a'.repeat(501),
      phone: '12',
    };

    const result = validateCheckout(values, store);
    expect(result.ok).toBe(false);
    if (!result.ok) {
      expect(result.errors.paymentMethodId).toBe('Choose a payment method.');
      expect(result.errors.note).toBe('Keep the note under 500 characters.');
      expect(result.errors.phone).toBe('Enter a phone number we can call.');
    }
  });

  it('validates single field on blur with validateField', () => {
    const values = {
      ...emptyCheckoutValues(store),
      postalCode: '!',
    };
    const err = validateField('postalCode', values, store);
    expect(err).toBe('Enter a valid postal code.');
  });

  it('maps API field errors correctly', () => {
    const mapped = mapApiFieldErrors({
      'shippingAddress.postalCode': ['Bad'],
      'x.y': ['?'],
    });
    expect(mapped).toEqual({ postalCode: 'Bad' });
  });

  it('creates PlaceOrderBody that parses with PlaceOrderBodySchema', () => {
    const validValues = {
      email: 'nadia@example.com',
      phone: '+8801712345678',
      firstName: 'Nadia',
      lastName: 'Rahman',
      line1: 'House 12, Road 5',
      line2: '',
      city: 'Dhaka',
      postalCode: '1209',
      countryCode: 'BD',
      shippingMethodId: 'standard',
      paymentMethodId: 'cod',
      note: '',
    };

    const result = validateCheckout(validValues, store);
    expect(result.ok).toBe(true);
    if (result.ok) {
      const placeOrderBody = toPlaceOrderBody(result.body, {
        amount: 312900,
        currency: 'BDT',
      });
      const parsed = PlaceOrderBodySchema.safeParse(placeOrderBody);
      expect(parsed.success).toBe(true);
    }
  });

  it('creates attempt keys that return current key until renew is called', () => {
    const keys = createAttemptKeys();
    const key1 = keys.current();
    const key2 = keys.current();
    expect(key1).toBe(key2);
    expect(key1).toMatch(uuidV4Regex);

    const renewed = keys.renew();
    expect(renewed).not.toBe(key1);
    expect(keys.current()).toBe(renewed);
    expect(renewed).toMatch(uuidV4Regex);
  });
});
