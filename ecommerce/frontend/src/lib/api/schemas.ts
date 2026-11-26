import { z } from 'zod';

export const CurrencySchema = z.string().regex(/^[A-Z]{3}$/);

export const SlugSchema = z.string().regex(/^[a-z0-9]+(?:-[a-z0-9]+)*$/);

export const SwatchSchema = z
  .string()
  .regex(/^#[0-9A-Fa-f]{6}$/)
  .nullable();

export const MoneySchema = z.object({
  amount: z.number().int().nonnegative(),
  currency: CurrencySchema,
});

export const ImageSchema = z.object({
  url: z.string().min(1),
  alt: z.string(),
  width: z.number().int().positive(),
  height: z.number().int().positive(),
});

export const ShippingMethodSchema = z.object({
  id: z.string().min(1),
  label: z.string().min(1),
  description: z.string(),
  price: MoneySchema,
  freeOverThreshold: z.boolean(),
  estimatedDays: z.object({
    min: z.number().int(),
    max: z.number().int(),
  }),
});

export const PaymentMethodSchema = z.object({
  id: z.string().min(1),
  label: z.string().min(1),
  description: z.string(),
  enabled: z.boolean(),
});

export const StoreConfigSchema = z.object({
  name: z.string().min(1),
  tagline: z.string(),
  currency: CurrencySchema,
  locale: z.string().min(1),
  supportEmail: z.string().email(),
  taxRateBps: z.number().int().min(0).max(10000),
  taxLabel: z.string().min(1),
  maxQuantityPerLine: z.number().int().positive(),
  freeShippingThreshold: MoneySchema.nullable(),
  shippingMethods: z.array(ShippingMethodSchema),
  paymentMethods: z.array(PaymentMethodSchema),
  countries: z.array(
    z.object({
      code: z.string().min(2),
      name: z.string().min(1),
    }),
  ),
});

export const CategorySchema = z.object({
  id: z.string().min(1),
  slug: SlugSchema,
  name: z.string().min(1),
  description: z.string(),
  image: ImageSchema.nullable(),
  productCount: z.number().int().nonnegative(),
});

export const CategoryListSchema = z.object({
  items: z.array(CategorySchema),
});

export const OptionValueSchema = z.object({
  label: z.string().min(1),
  swatch: SwatchSchema,
});

export const ProductOptionSchema = z.object({
  name: z.string().min(1),
  values: z.array(OptionValueSchema).min(1),
});

export const StockStatusSchema = z.enum(['in_stock', 'low_stock', 'out_of_stock']);

export const VariantSchema = z.object({
  id: z.string().min(1),
  sku: z.string().min(1),
  title: z.string().min(1),
  options: z.record(z.string(), z.string()),
  price: MoneySchema,
  compareAtPrice: MoneySchema.nullable(),
  stockStatus: StockStatusSchema,
  availableQuantity: z.number().int().nonnegative(),
});

export const BadgeSchema = z.enum(['new', 'sale', 'bestseller']);

export const ProductSummarySchema = z.object({
  id: z.string().min(1),
  slug: SlugSchema,
  name: z.string().min(1),
  subtitle: z.string(),
  category: z.object({
    slug: SlugSchema,
    name: z.string().min(1),
  }),
  price: MoneySchema,
  compareAtPrice: MoneySchema.nullable(),
  images: z.array(ImageSchema),
  badges: z.array(BadgeSchema),
  stockStatus: StockStatusSchema,
  swatches: z.array(OptionValueSchema),
});

export const ProductSchema = ProductSummarySchema.extend({
  description: z.array(z.string()),
  details: z.array(
    z.object({
      label: z.string(),
      value: z.string(),
    }),
  ),
  options: z.array(ProductOptionSchema),
  variants: z.array(VariantSchema).min(1),
  defaultVariantId: z.string().min(1),
  createdAt: z.string().min(1),
});

export const FacetsSchema = z.object({
  categories: z.array(
    z.object({
      slug: SlugSchema,
      name: z.string().min(1),
      count: z.number().int().nonnegative(),
    }),
  ),
  colors: z.array(
    z.object({
      label: z.string().min(1),
      swatch: SwatchSchema,
      count: z.number().int().nonnegative(),
    }),
  ),
  sizes: z.array(
    z.object({
      label: z.string().min(1),
      count: z.number().int().nonnegative(),
    }),
  ),
  price: z
    .object({
      min: MoneySchema,
      max: MoneySchema,
    })
    .nullable(),
});

export function paginated<T extends z.ZodTypeAny>(item: T) {
  return z.object({
    items: z.array(item),
    page: z.number().int().positive(),
    pageSize: z.number().int().positive(),
    totalItems: z.number().int().nonnegative(),
    totalPages: z.number().int().nonnegative(),
  });
}

export const ProductListSchema = paginated(ProductSummarySchema).extend({
  facets: FacetsSchema,
});

export const RelatedProductsSchema = z.object({
  items: z.array(ProductSummarySchema),
});

export const SuggestSchema = z.object({
  query: z.string(),
  products: z.array(
    z.object({
      slug: SlugSchema,
      name: z.string().min(1),
      image: ImageSchema.nullable(),
      price: MoneySchema,
    }),
  ),
  categories: z.array(
    z.object({
      slug: SlugSchema,
      name: z.string().min(1),
    }),
  ),
});

export const CartLineSchema = z.object({
  id: z.string().min(1),
  variantId: z.string().min(1),
  productSlug: SlugSchema,
  productName: z.string().min(1),
  variantTitle: z.string().min(1),
  image: ImageSchema.nullable(),
  unitPrice: MoneySchema,
  compareAtUnitPrice: MoneySchema.nullable(),
  quantity: z.number().int().positive(),
  lineTotal: MoneySchema,
  maxQuantity: z.number().int().nonnegative(),
  stockStatus: StockStatusSchema,
});

export const CartSchema = z.object({
  id: z.string().nullable(),
  lines: z.array(CartLineSchema),
  itemCount: z.number().int().nonnegative(),
  subtotal: MoneySchema,
  freeShippingRemaining: MoneySchema.nullable(),
  updatedAt: z.string().nullable(),
});

export const CustomerSchema = z.object({
  id: z.string().min(1),
  email: z.string().email(),
  firstName: z.string().min(1),
  lastName: z.string().min(1),
  createdAt: z.string().min(1),
});

export const CustomerEnvelopeSchema = z.object({
  customer: CustomerSchema,
});

export const AddressSchema = z.object({
  firstName: z.string().min(1).max(60),
  lastName: z.string().min(1).max(60),
  line1: z.string().min(3).max(120),
  line2: z.string().max(120).nullable(),
  city: z.string().min(2).max(60),
  postalCode: z.string().regex(/^[A-Za-z0-9 -]{3,10}$/),
  countryCode: z.string().min(2).max(3),
});

export const QuoteSchema = z.object({
  subtotal: MoneySchema,
  shipping: MoneySchema,
  tax: MoneySchema,
  total: MoneySchema,
  shippingMethodId: z.string().min(1),
  freeShippingApplied: z.boolean(),
  taxRateBps: z.number().int().nonnegative(),
  itemCount: z.number().int().nonnegative(),
});

export const OrderLineSchema = z.object({
  id: z.string().min(1),
  productSlug: SlugSchema,
  productName: z.string().min(1),
  variantTitle: z.string().min(1),
  sku: z.string().min(1),
  image: ImageSchema.nullable(),
  unitPrice: MoneySchema,
  quantity: z.number().int().positive(),
  lineTotal: MoneySchema,
});

export const OrderStatusSchema = z.enum([
  'placed',
  'processing',
  'shipped',
  'delivered',
  'cancelled',
]);

export const PaymentStatusSchema = z.enum(['pending', 'paid', 'refunded']);

export const OrderSchema = z.object({
  id: z.string().min(1),
  number: z.string().min(1),
  status: OrderStatusSchema,
  paymentStatus: PaymentStatusSchema,
  placedAt: z.string().min(1),
  email: z.string().email(),
  phone: z.string().min(1),
  shippingAddress: AddressSchema,
  shippingMethod: z.object({
    id: z.string().min(1),
    label: z.string().min(1),
    price: MoneySchema,
  }),
  paymentMethod: z.object({
    id: z.string().min(1),
    label: z.string().min(1),
  }),
  lines: z.array(OrderLineSchema),
  subtotal: MoneySchema,
  shipping: MoneySchema,
  tax: MoneySchema,
  total: MoneySchema,
  note: z.string().max(500).nullable(),
});

export const OrderSummarySchema = z.object({
  number: z.string().min(1),
  status: OrderStatusSchema,
  placedAt: z.string().min(1),
  itemCount: z.number().int().nonnegative(),
  total: MoneySchema,
  previewImages: z.array(ImageSchema).max(3),
});

export const OrderListSchema = paginated(OrderSummarySchema);

export const PlaceOrderBodySchema = z.object({
  email: z.string().email(),
  phone: z.string().regex(/^\+?[0-9 ()-]{7,20}$/),
  shippingAddress: AddressSchema,
  shippingMethodId: z.string().min(1),
  paymentMethodId: z.string().min(1),
  note: z.string().max(500).nullable(),
  expectedTotal: MoneySchema,
});

export const PlaceOrderResultSchema = z.object({
  order: OrderSchema,
  confirmationToken: z.string().min(1),
});

export const HomeContentSchema = z.object({
  hero: z.object({
    eyebrow: z.string(),
    headline: z.string(),
    subheadline: z.string(),
    image: ImageSchema,
    cta: z.object({
      label: z.string(),
      href: z.string(),
    }),
  }),
  featuredCategorySlugs: z.array(SlugSchema),
  editorial: z.object({
    eyebrow: z.string(),
    headline: z.string(),
    body: z.array(z.string()),
    image: ImageSchema,
    cta: z.object({
      label: z.string(),
      href: z.string(),
    }),
  }),
  values: z.array(
    z.object({
      icon: z.enum(['truck', 'leaf', 'refresh', 'shield']),
      title: z.string(),
      body: z.string(),
    }),
  ),
});

export const NewsletterResultSchema = z.object({
  status: z.literal('subscribed'),
});

export const ErrorCodeSchema = z.enum([
  'VALIDATION_FAILED',
  'IDEMPOTENCY_KEY_REQUIRED',
  'UNAUTHENTICATED',
  'INVALID_CREDENTIALS',
  'NOT_FOUND',
  'VARIANT_NOT_FOUND',
  'LINE_NOT_FOUND',
  'EMAIL_TAKEN',
  'OUT_OF_STOCK',
  'INSUFFICIENT_STOCK',
  'CART_EMPTY',
  'PRICE_CHANGED',
  'IDEMPOTENCY_CONFLICT',
  'UNSUPPORTED_MEDIA_TYPE',
  'SHIPPING_METHOD_UNAVAILABLE',
  'PAYMENT_METHOD_UNAVAILABLE',
  'RATE_LIMITED',
  'INTERNAL',
  'UNAVAILABLE',
  'NETWORK_ERROR',
  'CONTRACT_MISMATCH',
  'UNKNOWN',
]);

export const ErrorEnvelopeSchema = z.object({
  error: z.object({
    code: z.string(),
    message: z.string(),
    fields: z.record(z.string(), z.array(z.string())).nullable(),
    details: z.record(z.string(), z.unknown()).nullable(),
    requestId: z.string(),
  }),
});
