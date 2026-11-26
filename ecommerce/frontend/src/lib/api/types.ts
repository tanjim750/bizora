import { z } from 'zod';
import {
  AddressSchema,
  BadgeSchema,
  CartLineSchema,
  CartSchema,
  CategoryListSchema,
  CategorySchema,
  CustomerEnvelopeSchema,
  CustomerSchema,
  ErrorCodeSchema,
  ErrorEnvelopeSchema,
  FacetsSchema,
  HomeContentSchema,
  ImageSchema,
  MoneySchema,
  NewsletterResultSchema,
  OptionValueSchema,
  OrderLineSchema,
  OrderListSchema,
  OrderSchema,
  OrderStatusSchema,
  OrderSummarySchema,
  PaymentMethodSchema,
  PaymentStatusSchema,
  PlaceOrderBodySchema,
  PlaceOrderResultSchema,
  ProductListSchema,
  ProductOptionSchema,
  ProductSchema,
  ProductSummarySchema,
  QuoteSchema,
  RelatedProductsSchema,
  ShippingMethodSchema,
  StockStatusSchema,
  StoreConfigSchema,
  SuggestSchema,
  VariantSchema,
} from './schemas';

export type Money = z.infer<typeof MoneySchema>;
export type Image = z.infer<typeof ImageSchema>;
export type ShippingMethod = z.infer<typeof ShippingMethodSchema>;
export type PaymentMethod = z.infer<typeof PaymentMethodSchema>;
export type StoreConfig = z.infer<typeof StoreConfigSchema>;
export type Category = z.infer<typeof CategorySchema>;
export type CategoryList = z.infer<typeof CategoryListSchema>;
export type OptionValue = z.infer<typeof OptionValueSchema>;
export type ProductOption = z.infer<typeof ProductOptionSchema>;
export type StockStatus = z.infer<typeof StockStatusSchema>;
export type Variant = z.infer<typeof VariantSchema>;
export type Badge = z.infer<typeof BadgeSchema>;
export type ProductSummary = z.infer<typeof ProductSummarySchema>;
export type Product = z.infer<typeof ProductSchema>;
export type Facets = z.infer<typeof FacetsSchema>;
export type ProductList = z.infer<typeof ProductListSchema>;
export type RelatedProducts = z.infer<typeof RelatedProductsSchema>;
export type Suggest = z.infer<typeof SuggestSchema>;
export type CartLine = z.infer<typeof CartLineSchema>;
export type Cart = z.infer<typeof CartSchema>;
export type Customer = z.infer<typeof CustomerSchema>;
export type CustomerEnvelope = z.infer<typeof CustomerEnvelopeSchema>;
export type Address = z.infer<typeof AddressSchema>;
export type Quote = z.infer<typeof QuoteSchema>;
export type OrderLine = z.infer<typeof OrderLineSchema>;
export type OrderStatus = z.infer<typeof OrderStatusSchema>;
export type PaymentStatus = z.infer<typeof PaymentStatusSchema>;
export type Order = z.infer<typeof OrderSchema>;
export type OrderSummary = z.infer<typeof OrderSummarySchema>;
export type OrderList = z.infer<typeof OrderListSchema>;
export type PlaceOrderBody = z.infer<typeof PlaceOrderBodySchema>;
export type PlaceOrderResult = z.infer<typeof PlaceOrderResultSchema>;
export type HomeContent = z.infer<typeof HomeContentSchema>;
export type NewsletterResult = z.infer<typeof NewsletterResultSchema>;
export type ErrorCode = z.infer<typeof ErrorCodeSchema>;
export type ErrorEnvelope = z.infer<typeof ErrorEnvelopeSchema>;

export interface Paginated<T> {
  items: T[];
  page: number;
  pageSize: number;
  totalItems: number;
  totalPages: number;
}

export type ProductListQuery = {
  q?: string;
  category?: string;
  collection?: 'featured' | 'new' | 'sale';
  color?: string[];
  size?: string[];
  minPrice?: number;
  maxPrice?: number;
  inStock?: boolean;
  sort?: 'featured' | 'newest' | 'price-asc' | 'price-desc' | 'name-asc';
  page?: number;
  pageSize?: number;
};

export type ApiRequest = {
  method: 'GET' | 'POST' | 'PATCH' | 'DELETE';
  path: string;
  query?: Record<string, string | string[] | undefined>;
  body?: unknown;
  headers?: Record<string, string>;
};

export type ApiResponse = {
  status: number;
  body: unknown;
  headers: Record<string, string>;
};

export type Transport = (req: ApiRequest) => Promise<ApiResponse>;
