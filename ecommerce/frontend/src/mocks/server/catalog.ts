import { z } from 'zod';
import type { Product, ProductSummary } from '@/lib/api/types';
import { apiError, json, type MockResponse, queryAll, queryOne } from './http';
import { getDb } from './db';

function parseStrictInt(str: string): number | null {
  if (!/^\d+$/.test(str)) return null;
  const n = Number(str);
  return Number.isSafeInteger(n) ? n : null;
}

export function toSummary(product: Product): ProductSummary {
  return {
    id: product.id,
    slug: product.slug,
    name: product.name,
    subtitle: product.subtitle,
    category: product.category,
    price: product.price,
    compareAtPrice: product.compareAtPrice,
    images: product.images.slice(0, 2),
    badges: product.badges,
    stockStatus: product.stockStatus,
    swatches: product.swatches,
  };
}

export function getStore(): MockResponse {
  return json(200, getDb().store);
}

export function getHomeContent(): MockResponse {
  return json(200, getDb().home);
}

export function listCategories(): MockResponse {
  const db = getDb();
  const items = db.categories.items.map((cat) => {
    const count = db.products.filter((p) => p.category.slug === cat.slug).length;
    return { ...cat, productCount: count };
  });
  return json(200, { items });
}

export function listProducts(query?: Record<string, string | string[] | undefined>): MockResponse {
  const db = getDb();
  const fields: Record<string, string[]> = {};

  let page = 1;
  const pageStr = queryOne(query, 'page');
  if (pageStr !== undefined) {
    const p = parseStrictInt(pageStr);
    if (p === null || p < 1) {
      fields.page = ['Must be an integer ≥ 1.'];
    } else {
      page = p;
    }
  }

  let pageSize = 24;
  const pageSizeStr = queryOne(query, 'pageSize');
  if (pageSizeStr !== undefined) {
    const ps = parseStrictInt(pageSizeStr);
    if (ps === null || ps < 1 || ps > 48) {
      fields.pageSize = ['Must be between 1 and 48.'];
    } else {
      pageSize = ps;
    }
  }

  let sort = 'featured';
  const sortStr = queryOne(query, 'sort');
  if (sortStr !== undefined) {
    if (!['featured', 'newest', 'price-asc', 'price-desc', 'name-asc'].includes(sortStr)) {
      fields.sort = ['Unknown sort.'];
    } else {
      sort = sortStr;
    }
  }

  let minPrice: number | undefined;
  const minPriceStr = queryOne(query, 'minPrice');
  if (minPriceStr !== undefined) {
    const mp = parseStrictInt(minPriceStr);
    if (mp === null || mp < 0) {
      fields.minPrice = ['Must be a whole number ≥ 0.'];
    } else {
      minPrice = mp;
    }
  }

  let maxPrice: number | undefined;
  const maxPriceStr = queryOne(query, 'maxPrice');
  if (maxPriceStr !== undefined) {
    const mx = parseStrictInt(maxPriceStr);
    if (mx === null || mx < 0) {
      fields.maxPrice = ['Must be a whole number ≥ 0.'];
    } else {
      maxPrice = mx;
    }
  }

  const category = queryOne(query, 'category');
  if (category !== undefined && !/^[a-z0-9]+(?:-[a-z0-9]+)*$/.test(category)) {
    fields.category = ['Invalid category slug.'];
  }

  const collection = queryOne(query, 'collection');
  if (collection !== undefined && !['featured', 'new', 'sale'].includes(collection)) {
    fields.collection = ['Must be featured, new, or sale.'];
  }

  let inStock = false;
  const inStockRaw = queryOne(query, 'inStock');
  if (inStockRaw !== undefined) {
    if (inStockRaw !== 'true') {
      fields.inStock = ['Must be true.'];
    } else {
      inStock = true;
    }
  }

  const q = queryOne(query, 'q')?.trim();
  if (q !== undefined && q.length > 100) {
    fields.q = ['Must be at most 100 characters.'];
  }

  const colors = queryAll(query, 'color');
  const sizes = queryAll(query, 'size');

  if (Object.keys(fields).length > 0) {
    return apiError(400, 'VALIDATION_FAILED', 'Some fields are not valid.', fields);
  }

  type Filters = {
    category?: string;
    collection?: string;
    colors: string[];
    sizes: string[];
    minPrice?: number;
    maxPrice?: number;
    inStock: boolean;
    q?: string;
  };

  const currentFilters: Filters = {
    category,
    collection,
    colors,
    sizes,
    minPrice,
    maxPrice,
    inStock,
    q,
  };

  function matches(
    p: Product,
    f: Filters,
    skip?: 'category' | 'color' | 'size' | 'price',
  ): boolean {
    if (skip !== 'category' && f.category && p.category.slug !== f.category) {
      return false;
    }

    if (skip !== 'color' && f.colors.length > 0) {
      const colorOpt = p.options.find((o) => o.name === 'Color');
      const hasColor = colorOpt?.values.some((v) => f.colors.includes(v.label));
      if (!hasColor) return false;
    }

    if (skip !== 'size' && f.sizes.length > 0) {
      const sizeOpt = p.options.find((o) => o.name === 'Size');
      const hasSize = sizeOpt?.values.some((v) => f.sizes.includes(v.label));
      if (!hasSize) return false;
    }

    if (skip !== 'price') {
      if (f.minPrice !== undefined && p.price.amount < f.minPrice) return false;
      if (f.maxPrice !== undefined && p.price.amount > f.maxPrice) return false;
    }

    if (f.collection) {
      if (
        f.collection === 'featured' &&
        !p.badges.includes('bestseller') &&
        !p.badges.includes('new')
      ) {
        return false;
      }
      if (f.collection === 'new' && !p.badges.includes('new')) {
        return false;
      }
      if (f.collection === 'sale' && p.compareAtPrice === null) {
        return false;
      }
    }

    if (f.inStock && p.stockStatus === 'out_of_stock') {
      return false;
    }

    if (f.q) {
      const qLower = f.q.toLowerCase();
      const inName = p.name.toLowerCase().includes(qLower);
      const inSubtitle = p.subtitle.toLowerCase().includes(qLower);
      const inCat = p.category.name.toLowerCase().includes(qLower);
      const inDesc = p.description.some((d) => d.toLowerCase().includes(qLower));
      const inOptions = p.options.some((o) =>
        o.values.some((v) => v.label.toLowerCase().includes(qLower)),
      );
      if (!inName && !inSubtitle && !inCat && !inDesc && !inOptions) {
        return false;
      }
    }

    return true;
  }

  // Compute Facets per 03-API-CONTRACT.md §4.10:
  // "Counts are computed over the result set with all filters EXCEPT the facet's own (so a user can widen a choice).
  //  price.min/max cover the result set ignoring the price filter. Empty result → arrays [], price = null."
  const facetCategories = db.categories.items
    .map((cat) => {
      const count = db.products.filter(
        (p) => matches(p, currentFilters, 'category') && p.category.slug === cat.slug,
      ).length;
      return {
        slug: cat.slug,
        name: cat.name,
        count,
      };
    })
    .filter((c) => c.count > 0);

  const colorMap = new Map<string, { swatch: string | null; count: number }>();
  for (const p of db.products) {
    if (matches(p, currentFilters, 'color')) {
      const colorOpt = p.options.find((o) => o.name === 'Color');
      if (colorOpt) {
        for (const v of colorOpt.values) {
          const existing = colorMap.get(v.label);
          if (existing) {
            existing.count++;
          } else {
            colorMap.set(v.label, { swatch: v.swatch, count: 1 });
          }
        }
      }
    }
  }
  const facetColors = Array.from(colorMap.entries()).map(([label, val]) => ({
    label,
    swatch: val.swatch,
    count: val.count,
  }));

  const sizeMap = new Map<string, number>();
  for (const p of db.products) {
    if (matches(p, currentFilters, 'size')) {
      const sizeOpt = p.options.find((o) => o.name === 'Size');
      if (sizeOpt) {
        for (const v of sizeOpt.values) {
          sizeMap.set(v.label, (sizeMap.get(v.label) ?? 0) + 1);
        }
      }
    }
  }
  const facetSizes = Array.from(sizeMap.entries()).map(([label, count]) => ({
    label,
    count,
  }));

  const priceFiltered = db.products.filter((p) => matches(p, currentFilters, 'price'));
  let facetPrice = null;
  if (priceFiltered.length > 0) {
    const min = Math.min(...priceFiltered.map((p) => p.price.amount));
    const max = Math.max(...priceFiltered.map((p) => p.price.amount));
    facetPrice = {
      min: { amount: min, currency: db.store.currency },
      max: { amount: max, currency: db.store.currency },
    };
  }

  const facets = {
    categories: facetCategories,
    colors: facetColors,
    sizes: facetSizes,
    price: facetPrice,
  };

  // Filter & Sort Products
  const filtered = db.products.filter((p) => matches(p, currentFilters));

  const sorted = [...filtered].sort((a, b) => {
    if (sort === 'price-asc') {
      return a.price.amount - b.price.amount || a.name.localeCompare(b.name, 'en');
    }
    if (sort === 'price-desc') {
      return b.price.amount - a.price.amount || a.name.localeCompare(b.name, 'en');
    }
    if (sort === 'newest') {
      return (
        new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime() ||
        a.name.localeCompare(b.name, 'en')
      );
    }
    if (sort === 'name-asc') {
      return a.name.localeCompare(b.name, 'en');
    }
    return 0;
  });

  const totalItems = sorted.length;
  const totalPages = Math.ceil(totalItems / pageSize);
  const startIndex = (page - 1) * pageSize;
  const items = sorted.slice(startIndex, startIndex + pageSize).map(toSummary);

  return json(200, {
    items,
    page,
    pageSize,
    totalItems,
    totalPages,
    facets,
  });
}

export function getProduct(slug: string): MockResponse {
  const db = getDb();
  const product = db.products.find((p) => p.slug === slug);
  if (!product) {
    return apiError(404, 'NOT_FOUND', 'Product not found.');
  }
  return json(200, product);
}

export function getRelated(slug: string, limitQuery?: string | string[]): MockResponse {
  const db = getDb();
  const target = db.products.find((p) => p.slug === slug);
  if (!target) {
    return apiError(404, 'NOT_FOUND', 'Product not found.');
  }

  let limit = 4;
  if (limitQuery !== undefined) {
    const raw = Array.isArray(limitQuery) ? limitQuery[0] : limitQuery;
    const parsed = parseStrictInt(raw);
    if (parsed === null || parsed < 1 || parsed > 12) {
      return apiError(400, 'VALIDATION_FAILED', 'Invalid limit.', {
        limit: ['Limit must be between 1 and 12.'],
      });
    }
    limit = parsed;
  }

  const others = db.products.filter((p) => p.slug !== slug);
  const sameCat = others.filter((p) => p.category.slug === target.category.slug);
  const diffCat = others.filter((p) => p.category.slug !== target.category.slug);

  const sameCatInStock = sameCat.filter((p) => p.stockStatus !== 'out_of_stock');
  const sameCatOOS = sameCat.filter((p) => p.stockStatus === 'out_of_stock');
  const diffCatInStock = diffCat.filter((p) => p.stockStatus !== 'out_of_stock');
  const diffCatOOS = diffCat.filter((p) => p.stockStatus === 'out_of_stock');

  const ordered = [...sameCatInStock, ...diffCatInStock, ...sameCatOOS, ...diffCatOOS];
  const items = ordered.slice(0, limit).map(toSummary);

  return json(200, { items });
}

export function suggest(qQuery?: string | string[]): MockResponse {
  const db = getDb();
  const rawQ = Array.isArray(qQuery) ? qQuery[0] : qQuery;
  const q = rawQ?.trim() ?? '';

  if (q.length < 2) {
    return json(200, {
      query: q,
      products: [],
      categories: [],
    });
  }

  const qLower = q.toLowerCase();
  const products = db.products
    .filter(
      (p) => p.name.toLowerCase().includes(qLower) || p.subtitle.toLowerCase().includes(qLower),
    )
    .slice(0, 5)
    .map((p) => ({
      slug: p.slug,
      name: p.name,
      image: p.images[0] ?? null,
      price: p.price,
    }));

  const categories = db.categories.items
    .filter((c) => c.name.toLowerCase().includes(qLower))
    .slice(0, 3)
    .map((c) => ({
      slug: c.slug,
      name: c.name,
    }));

  return json(200, {
    query: q,
    products,
    categories,
  });
}

export function subscribeNewsletter(body: unknown): MockResponse {
  const db = getDb();
  const NewsletterSchema = z.object({
    email: z.string().email(),
  });

  const parsed = NewsletterSchema.safeParse(body);
  if (!parsed.success) {
    return apiError(400, 'VALIDATION_FAILED', 'Some fields are not valid.', {
      email: ['Enter a valid email address.'],
    });
  }

  db.newsletter.add(parsed.data.email.toLowerCase());
  return json(202, { status: 'subscribed' });
}
