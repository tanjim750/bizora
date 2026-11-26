import type {
  CategoryList,
  Customer,
  HomeContent,
  Order,
  Product,
  StoreConfig,
} from '@/lib/api/types';
import type { MockResponse } from './http';

import storeFixture from '../fixtures/store.json';
import homeFixture from '../fixtures/home.json';
import categoriesFixture from '../fixtures/categories.json';
import productsFixture from '../fixtures/products.json';
import usersFixture from '../fixtures/users.json';
import ordersFixture from '../fixtures/orders.json';

export type MockCartLine = { id: string; variantId: string; quantity: number };
export type MockCart = {
  id: string;
  customerId: string | null;
  lines: MockCartLine[];
  updatedAt: string;
};
export type MockUser = Customer & { password: string };
export type MockOrder = Order & { customerId: string | null; confirmationToken: string };

export type MockDb = {
  store: StoreConfig;
  home: HomeContent;
  categories: CategoryList;
  products: Product[];
  users: MockUser[];
  carts: Map<string, MockCart>;
  sessions: Map<string, string /* customerId */>;
  orders: MockOrder[];
  idempotency: Map<string, { bodyHash: string; response: MockResponse }>;
  signInFailures: Map<string, number[]>;
  newsletter: Set<string>;
  nextOrderSeq: number;
};

declare global {
  var __aureloMockDb: MockDb | undefined;
}

function initDb(): MockDb {
  return {
    store: structuredClone(storeFixture) as StoreConfig,
    home: structuredClone(homeFixture) as HomeContent,
    categories: structuredClone(categoriesFixture) as CategoryList,
    products: structuredClone(productsFixture.items) as Product[],
    users: structuredClone(usersFixture.items) as MockUser[],
    carts: new Map(),
    sessions: new Map(),
    orders: structuredClone(ordersFixture.items) as MockOrder[],
    idempotency: new Map(),
    signInFailures: new Map(),
    newsletter: new Set(),
    nextOrderSeq: 200,
  };
}

export function getDb(): MockDb {
  if (!globalThis.__aureloMockDb) {
    globalThis.__aureloMockDb = initDb();
  }
  return globalThis.__aureloMockDb;
}

export function resetMockDb(): MockDb {
  globalThis.__aureloMockDb = initDb();
  return globalThis.__aureloMockDb;
}

export function recomputeStock(product: Product): void {
  for (const variant of product.variants) {
    if (variant.availableQuantity <= 0) {
      variant.stockStatus = 'out_of_stock';
    } else if (variant.availableQuantity <= 5) {
      variant.stockStatus = 'low_stock';
    } else {
      variant.stockStatus = 'in_stock';
    }
  }

  if (product.variants.some((v) => v.stockStatus === 'in_stock')) {
    product.stockStatus = 'in_stock';
  } else if (product.variants.some((v) => v.stockStatus === 'low_stock')) {
    product.stockStatus = 'low_stock';
  } else {
    product.stockStatus = 'out_of_stock';
  }

  const firstAvail = product.variants.find((v) => v.availableQuantity > 0);
  product.defaultVariantId = firstAvail ? firstAvail.id : product.variants[0].id;
}

export function findVariant(
  variantId: string,
): { product: Product; variant: Product['variants'][number] } | null {
  const db = getDb();
  for (const prod of db.products) {
    const v = prod.variants.find((item) => item.id === variantId);
    if (v) {
      return { product: prod, variant: v };
    }
  }
  return null;
}
