import { describe, expect, it } from 'vitest';
import {
  AddressSchema,
  CartLineSchema,
  CartSchema,
  CategoryListSchema,
  CustomerEnvelopeSchema,
  CustomerSchema,
  ErrorCodeSchema,
  ErrorEnvelopeSchema,
  FacetsSchema,
  HomeContentSchema,
  MoneySchema,
  NewsletterResultSchema,
  OrderListSchema,
  OrderSchema,
  PlaceOrderBodySchema,
  PlaceOrderResultSchema,
  ProductListSchema,
  ProductSchema,
  ProductSummarySchema,
  QuoteSchema,
  RelatedProductsSchema,
  StoreConfigSchema,
  SuggestSchema,
} from '@/lib/api/schemas';
import { ApiError, isApiError, toUserMessage, USER_MESSAGES } from '@/lib/api/errors';
import { addMoney, formatMoney, multiplyMoney, toMajor, toMinor } from '@/lib/format/money';
import { formatDate, formatMonthYear } from '@/lib/format/date';

// Verbatim JSON examples from 03-API-CONTRACT.md
const storeConfigExample = {
  name: 'Aurelo',
  tagline: 'Objects for slow living',
  currency: 'BDT',
  locale: 'en-BD',
  supportEmail: 'help@aurelo.test',
  taxRateBps: 500,
  taxLabel: 'VAT',
  maxQuantityPerLine: 10,
  freeShippingThreshold: { amount: 500000, currency: 'BDT' },
  shippingMethods: [
    {
      id: 'standard',
      label: 'Standard delivery',
      description: '3–5 working days',
      price: { amount: 8000, currency: 'BDT' },
      freeOverThreshold: true,
      estimatedDays: { min: 3, max: 5 },
    },
    {
      id: 'express',
      label: 'Express delivery',
      description: '1–2 working days',
      price: { amount: 15000, currency: 'BDT' },
      freeOverThreshold: false,
      estimatedDays: { min: 1, max: 2 },
    },
  ],
  paymentMethods: [
    {
      id: 'cod',
      label: 'Cash on delivery',
      description: 'Pay when your order arrives.',
      enabled: true,
    },
    { id: 'card', label: 'Card payment', description: 'Coming soon.', enabled: false },
  ],
  countries: [{ code: 'BD', name: 'Bangladesh' }],
};

const productSummaryExample = {
  id: 'prod_001',
  slug: 'ondo-stoneware-mug',
  name: 'Ondo Stoneware Mug',
  subtitle: 'Hand-thrown, 350 ml',
  category: { slug: 'ceramics', name: 'Ceramics' },
  price: { amount: 145000, currency: 'BDT' },
  compareAtPrice: null,
  images: [
    {
      url: '/mock/products/ondo-stoneware-mug-1.jpg',
      alt: 'Ondo Stoneware Mug in Sand, front view',
      width: 1600,
      height: 2000,
    },
    {
      url: '/mock/products/ondo-stoneware-mug-2.jpg',
      alt: 'Ondo Stoneware Mug, close-up detail',
      width: 1600,
      height: 2000,
    },
  ],
  badges: ['bestseller'],
  stockStatus: 'in_stock',
  swatches: [
    { label: 'Sand', swatch: '#D8C8B0' },
    { label: 'Ink', swatch: '#2B2F36' },
    { label: 'Moss', swatch: '#6B7A55' },
  ],
};

const productDetailExample = {
  ...productSummaryExample,
  description: [
    'Each piece is thrown, trimmed and glazed by hand.',
    'Small variations in color are part of the craft.',
  ],
  details: [
    { label: 'Material', value: 'Stoneware clay' },
    { label: 'Dimensions', value: '8.5 cm x 9.5 cm' },
  ],
  options: [
    {
      name: 'Color',
      values: [
        { label: 'Sand', swatch: '#D8C8B0' },
        { label: 'Ink', swatch: '#2B2F36' },
      ],
    },
  ],
  variants: [
    {
      id: 'var_01',
      sku: 'AUR-001-SAN',
      title: 'Sand',
      options: { Color: 'Sand' },
      price: { amount: 145000, currency: 'BDT' },
      compareAtPrice: null,
      stockStatus: 'in_stock',
      availableQuantity: 15,
    },
  ],
  defaultVariantId: 'var_01',
  createdAt: '2026-11-26T08:00:00Z',
};

const facetsExample = {
  categories: [{ slug: 'ceramics', name: 'Ceramics', count: 5 }],
  colors: [{ label: 'Sand', swatch: '#D8C8B0', count: 3 }],
  sizes: [{ label: 'Double', count: 1 }],
  price: {
    min: { amount: 95000, currency: 'BDT' },
    max: { amount: 2190000, currency: 'BDT' },
  },
};

const cartExample = {
  id: 'cart_9d2e',
  lines: [
    {
      id: 'line_01',
      variantId: 'var_ondo-stoneware-mug_sand',
      productSlug: 'ondo-stoneware-mug',
      productName: 'Ondo Stoneware Mug',
      variantTitle: 'Sand',
      image: {
        url: '/mock/products/ondo-stoneware-mug-1.jpg',
        alt: 'Ondo Stoneware Mug in Sand, front view',
        width: 1600,
        height: 2000,
      },
      unitPrice: { amount: 145000, currency: 'BDT' },
      compareAtUnitPrice: null,
      quantity: 2,
      lineTotal: { amount: 290000, currency: 'BDT' },
      maxQuantity: 10,
      stockStatus: 'in_stock',
    },
  ],
  itemCount: 2,
  subtotal: { amount: 290000, currency: 'BDT' },
  freeShippingRemaining: { amount: 210000, currency: 'BDT' },
  updatedAt: '2026-11-26T08:15:00Z',
};

const quoteExample = {
  subtotal: { amount: 290000, currency: 'BDT' },
  shipping: { amount: 8000, currency: 'BDT' },
  tax: { amount: 14900, currency: 'BDT' },
  total: { amount: 312900, currency: 'BDT' },
  shippingMethodId: 'standard',
  freeShippingApplied: false,
  taxRateBps: 500,
  itemCount: 2,
};

const customerExample = {
  id: 'cus_01',
  email: 'nadia@example.com',
  firstName: 'Nadia',
  lastName: 'Rahman',
  createdAt: '2026-11-20T10:00:00Z',
};

const orderExample = {
  id: 'ord_0200',
  number: 'AUR-100200',
  status: 'placed',
  paymentStatus: 'pending',
  placedAt: '2026-11-26T08:20:00Z',
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
  shippingMethod: {
    id: 'standard',
    label: 'Standard delivery',
    price: { amount: 8000, currency: 'BDT' },
  },
  paymentMethod: { id: 'cod', label: 'Cash on delivery' },
  lines: [
    {
      id: 'oline_1',
      productSlug: 'ondo-stoneware-mug',
      productName: 'Ondo Stoneware Mug',
      variantTitle: 'Sand',
      sku: 'AUR-001-SAN',
      image: null,
      unitPrice: { amount: 145000, currency: 'BDT' },
      quantity: 2,
      lineTotal: { amount: 290000, currency: 'BDT' },
    },
  ],
  subtotal: { amount: 290000, currency: 'BDT' },
  shipping: { amount: 8000, currency: 'BDT' },
  tax: { amount: 14900, currency: 'BDT' },
  total: { amount: 312900, currency: 'BDT' },
  note: null,
};

const homeContentExample = {
  hero: {
    eyebrow: 'Autumn edit 2026',
    headline: 'Made slowly. Kept for years.',
    subheadline: 'Ceramics, linen and light from small workshops, chosen to be used every day.',
    image: {
      url: '/mock/editorial/hero.jpg',
      alt: 'Stoneware mugs and a linen throw on an oak table in morning light',
      width: 2400,
      height: 1600,
    },
    cta: { label: 'Shop the collection', href: '/shop' },
  },
  featuredCategorySlugs: ['ceramics', 'linen', 'lighting', 'bags'],
  editorial: {
    eyebrow: 'From the workshop',
    headline: 'Every Ondo mug starts as 400 grams of clay',
    body: [
      'Each piece is thrown, trimmed and glazed by hand, so no two are quite the same.',
      'Small differences in colour and form are part of the object, not a flaw.',
    ],
    image: {
      url: '/mock/editorial/workshop.jpg',
      alt: "Hands shaping a mug on a potter's wheel",
      width: 1600,
      height: 2000,
    },
    cta: { label: 'Shop ceramics', href: '/shop?category=ceramics' },
  },
  values: [
    {
      icon: 'truck',
      title: 'Delivery across Bangladesh',
      body: 'Standard in 3–5 days, express in 1–2.',
    },
    {
      icon: 'leaf',
      title: 'Made by small workshops',
      body: 'Natural materials, made in small batches.',
    },
    {
      icon: 'refresh',
      title: 'Easy returns',
      body: 'Changed your mind? Return unused items within 14 days.',
    },
    { icon: 'shield', title: 'Cash on delivery', body: 'Pay when your order arrives.' },
  ],
};

const errorEnvelopeExample = {
  error: {
    code: 'VALIDATION_FAILED',
    message: 'Some fields are not valid.',
    fields: { email: ['Enter a valid email address.'] },
    details: null,
    requestId: 'req_7f3a2c',
  },
};

describe('SF-05 API Contract & Schemas', () => {
  describe('Zod Schemas against 03-API-CONTRACT examples', () => {
    it('parses StoreConfig example and accepts null freeShippingThreshold', () => {
      expect(() => StoreConfigSchema.parse(storeConfigExample)).not.toThrow();
      expect(() =>
        StoreConfigSchema.parse({
          ...storeConfigExample,
          freeShippingThreshold: null,
        }),
      ).not.toThrow();
    });

    it('parses ProductSummary and Product detail example', () => {
      expect(() => ProductSummarySchema.parse(productSummaryExample)).not.toThrow();
      expect(() => ProductSchema.parse(productDetailExample)).not.toThrow();
    });

    it('parses Facets example and empty facets (price: null)', () => {
      expect(() => FacetsSchema.parse(facetsExample)).not.toThrow();
      expect(() =>
        FacetsSchema.parse({
          categories: [],
          colors: [],
          sizes: [],
          price: null,
        }),
      ).not.toThrow();
    });

    it('parses Cart example and empty cart', () => {
      expect(() => CartSchema.parse(cartExample)).not.toThrow();

      const emptyCart = {
        id: null,
        lines: [],
        itemCount: 0,
        subtotal: { amount: 0, currency: 'BDT' },
        freeShippingRemaining: null,
        updatedAt: null,
      };
      expect(() => CartSchema.parse(emptyCart)).not.toThrow();
    });

    it('parses CartLine with maxQuantity: 0 when out of stock', () => {
      const lineWithZeroMax = {
        ...cartExample.lines[0],
        maxQuantity: 0,
        stockStatus: 'out_of_stock',
      };
      expect(() => CartLineSchema.parse(lineWithZeroMax)).not.toThrow();
    });

    it('parses Quote and Customer envelopes', () => {
      expect(() => QuoteSchema.parse(quoteExample)).not.toThrow();
      expect(() => CustomerSchema.parse(customerExample)).not.toThrow();
      expect(() => CustomerEnvelopeSchema.parse({ customer: customerExample })).not.toThrow();
    });

    it('parses Order and OrderList example', () => {
      expect(() => OrderSchema.parse(orderExample)).not.toThrow();
      const orderSummary = {
        number: orderExample.number,
        status: orderExample.status,
        placedAt: orderExample.placedAt,
        itemCount: 2,
        total: orderExample.total,
        previewImages: [
          {
            url: '/img.jpg',
            alt: '',
            width: 100,
            height: 100,
          },
        ],
      };
      expect(() =>
        OrderListSchema.parse({
          items: [orderSummary],
          page: 1,
          pageSize: 10,
          totalItems: 1,
          totalPages: 1,
        }),
      ).not.toThrow();
    });

    it('parses CategoryList, RelatedProducts, Suggest, and NewsletterResult', () => {
      expect(() =>
        CategoryListSchema.parse({
          items: [
            {
              id: 'cat_01',
              slug: 'ceramics',
              name: 'Ceramics',
              description: 'Handmade pots',
              image: null,
              productCount: 4,
            },
          ],
        }),
      ).not.toThrow();

      expect(() =>
        RelatedProductsSchema.parse({
          items: [productSummaryExample],
        }),
      ).not.toThrow();

      expect(() =>
        SuggestSchema.parse({
          query: 'on',
          products: [
            {
              slug: 'ondo-stoneware-mug',
              name: 'Ondo Mug',
              image: null,
              price: { amount: 145000, currency: 'BDT' },
            },
          ],
          categories: [{ slug: 'ceramics', name: 'Ceramics' }],
        }),
      ).not.toThrow();

      expect(() => NewsletterResultSchema.parse({ status: 'subscribed' })).not.toThrow();
    });

    it('parses ProductList with facets', () => {
      expect(() =>
        ProductListSchema.parse({
          items: [productSummaryExample],
          page: 1,
          pageSize: 24,
          totalItems: 1,
          totalPages: 1,
          facets: facetsExample,
        }),
      ).not.toThrow();
    });

    it('parses PlaceOrderResult', () => {
      expect(() =>
        PlaceOrderResultSchema.parse({
          order: orderExample,
          confirmationToken: 'tok_test123',
        }),
      ).not.toThrow();
    });

    it('parses HomeContent example', () => {
      expect(() => HomeContentSchema.parse(homeContentExample)).not.toThrow();
    });

    it('parses ErrorEnvelope example', () => {
      expect(() => ErrorEnvelopeSchema.parse(errorEnvelopeExample)).not.toThrow();
    });

    it('strips unknown keys on ProductSummary', () => {
      const parsed = ProductSummarySchema.parse({
        ...productSummaryExample,
        secret: 1,
      }) as typeof productSummaryExample & { secret?: number };
      expect(parsed.secret).toBeUndefined();
    });
  });

  describe('Validation constraints', () => {
    it('enforces Money constraints (non-negative integer amount, uppercase 3-letter currency)', () => {
      expect(MoneySchema.safeParse({ amount: 10.5, currency: 'BDT' }).success).toBe(false);
      expect(MoneySchema.safeParse({ amount: -1, currency: 'BDT' }).success).toBe(false);
      expect(MoneySchema.safeParse({ amount: 1000, currency: 'bdt' }).success).toBe(false);
      expect(MoneySchema.safeParse({ amount: 1000, currency: 'BD' }).success).toBe(false);
      expect(MoneySchema.safeParse({ amount: 1000, currency: 'BDT' }).success).toBe(true);
    });

    it('enforces Address constraints', () => {
      expect(
        AddressSchema.safeParse({
          firstName: '',
          lastName: 'Rahman',
          line1: 'House 12',
          line2: null,
          city: 'Dhaka',
          postalCode: '1209',
          countryCode: 'BD',
        }).success,
      ).toBe(false);

      expect(
        AddressSchema.safeParse({
          firstName: 'Nadia',
          lastName: 'Rahman',
          line1: 'House 12',
          line2: null,
          city: 'Dhaka',
          postalCode: '!',
          countryCode: 'BD',
        }).success,
      ).toBe(false);
    });

    it('enforces PlaceOrderBody constraints (phone regex, etc.)', () => {
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

      expect(PlaceOrderBodySchema.safeParse(validBody).success).toBe(true);
      expect(PlaceOrderBodySchema.safeParse({ ...validBody, phone: 'abc' }).success).toBe(false);
    });

    it('ErrorCodeSchema includes all required contract codes', () => {
      expect(ErrorCodeSchema.options).toContain('PRICE_CHANGED');
      expect(ErrorCodeSchema.options).toContain('NETWORK_ERROR');
      expect(ErrorCodeSchema.options).toContain('CONTRACT_MISMATCH');
      expect(ErrorCodeSchema.options).toContain('UNKNOWN');
    });
  });

  describe('Errors and toUserMessage', () => {
    it('creates ApiError and checks isApiError with instance and duck typing', () => {
      const err = new ApiError(500, 'INTERNAL', 'Internal error message');
      expect(isApiError(err)).toBe(true);
      expect(isApiError(new Error('generic'))).toBe(false);
      expect(isApiError(null)).toBe(false);
      expect(isApiError(undefined)).toBe(false);
      expect(isApiError({ name: 'ApiError', status: 404, code: 'NOT_FOUND' })).toBe(true);
      expect(err.name).toBe('ApiError');
    });

    it('maps known error codes to user messages with details interpolation', () => {
      const stockErr = new ApiError(409, 'INSUFFICIENT_STOCK', 'x', null, { available: 3 });
      expect(toUserMessage(stockErr)).toBe("Only 3 left — we've updated the quantity.");

      const stockErrNoDetails = new ApiError(409, 'INSUFFICIENT_STOCK', 'x');
      expect(toUserMessage(stockErrNoDetails)).toBe("Only 0 left — we've updated the quantity.");

      const rateErr = new ApiError(429, 'RATE_LIMITED', 'x', null, { retryAfterSeconds: 45 });
      expect(toUserMessage(rateErr)).toBe('Too many attempts. Try again in 45 seconds.');

      const rateErrDefault = new ApiError(429, 'RATE_LIMITED', 'x');
      expect(toUserMessage(rateErrDefault)).toBe('Too many attempts. Try again in 60 seconds.');

      expect(toUserMessage(new ApiError(401, 'UNAUTHENTICATED', 'x'))).toBe('Please sign in.');
      expect(toUserMessage(new ApiError(404, 'NOT_FOUND', 'x'))).toBe(
        'This item is no longer available.',
      );
      expect(toUserMessage(new ApiError(400, 'VALIDATION_FAILED', 'x'))).toBe(
        'Please check the highlighted fields.',
      );
      expect(toUserMessage(new ApiError(409, 'OUT_OF_STOCK', 'x'))).toBe(
        'Sorry, this is sold out.',
      );
      expect(toUserMessage(new ApiError(404, 'LINE_NOT_FOUND', 'x'))).toBe(
        'Your cart was updated.',
      );
      expect(toUserMessage(new ApiError(409, 'EMAIL_TAKEN', 'x'))).toBe(
        'An account with this email already exists.',
      );
    });

    it('falls back to default message for unknown errors or prototype methods', () => {
      expect(toUserMessage(new Error('something random'))).toBe(
        'Something went wrong. Please try again.',
      );
      expect(toUserMessage(new ApiError(500, 'NONEXISTENT_CODE', 'x'))).toBe(
        'Something went wrong. Please try again.',
      );
      expect(toUserMessage(new ApiError(500, 'toString', 'x'))).toBe(
        'Something went wrong. Please try again.',
      );
    });

    it('exports USER_MESSAGES containing all non-interpolated error codes', () => {
      const expectedCodes = ErrorCodeSchema.options.filter(
        (code) => code !== 'INSUFFICIENT_STOCK' && code !== 'RATE_LIMITED',
      );
      for (const code of expectedCodes) {
        expect(USER_MESSAGES[code]).toBeDefined();
        expect(typeof USER_MESSAGES[code]).toBe('string');
      }
    });
  });

  describe('Formatters: Money', () => {
    it('formats whole amounts without fraction digits in BDT', () => {
      expect(formatMoney({ amount: 145000, currency: 'BDT' })).toBe('৳1,450');
      expect(formatMoney({ amount: 0, currency: 'BDT' })).toBe('৳0');
    });

    it('formats fractional amounts with 2 fraction digits in BDT', () => {
      expect(formatMoney({ amount: 1234567, currency: 'BDT' })).toBe('৳12,345.67');
      expect(formatMoney({ amount: 50, currency: 'BDT' })).toBe('৳0.50');
    });

    it('converts major to minor and vice versa', () => {
      expect(toMinor(14.5)).toBe(1450);
      expect(toMajor(1450)).toBe(14.5);
    });

    it('adds money of same currency and throws for different currency', () => {
      const a = { amount: 1000, currency: 'BDT' };
      const b = { amount: 2500, currency: 'BDT' };
      expect(addMoney(a, b)).toEqual({ amount: 3500, currency: 'BDT' });

      const c = { amount: 100, currency: 'USD' };
      expect(() => addMoney(a, c)).toThrow();
    });

    it('multiplies money by scalar with integer rounding', () => {
      const m = { amount: 1500, currency: 'BDT' };
      expect(multiplyMoney(m, 3)).toEqual({ amount: 4500, currency: 'BDT' });
      expect(multiplyMoney(m, 1.5)).toEqual({ amount: 2250, currency: 'BDT' });
      expect(multiplyMoney({ amount: 105, currency: 'BDT' }, 1.5)).toEqual({
        amount: 158,
        currency: 'BDT',
      });
    });
  });

  describe('Formatters: Date', () => {
    it('formats date to D MMM YYYY in Asia/Dhaka time zone', () => {
      expect(formatDate('2026-11-26T08:15:00Z')).toBe('26 Nov 2026');
      // 18:30 UTC is 00:30 the next day in Asia/Dhaka (UTC+6)
      expect(formatDate('2026-11-26T18:30:00Z')).toBe('27 Nov 2026');
    });

    it('formats month and year and rolls over month on Asia/Dhaka midnight', () => {
      expect(formatMonthYear('2026-03-14T10:00:00Z')).toBe('March 2026');
      // 18:30 UTC on March 31 is 00:30 on April 1 in Asia/Dhaka (UTC+6)
      expect(formatMonthYear('2026-03-31T18:30:00Z')).toBe('April 2026');
    });
  });
});
