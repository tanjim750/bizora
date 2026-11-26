import fs from 'node:fs';
import path from 'node:path';
import { describe, expect, it } from 'vitest';
import {
  CategoryListSchema,
  CustomerSchema,
  HomeContentSchema,
  OrderSchema,
  ProductSchema,
  StoreConfigSchema,
} from '@/lib/api/schemas';
import type { Product, StockStatus } from '@/lib/api/types';

import store from '@/mocks/fixtures/store.json';
import home from '@/mocks/fixtures/home.json';
import categories from '@/mocks/fixtures/categories.json';
import productsData from '@/mocks/fixtures/products.json';
import users from '@/mocks/fixtures/users.json';
import orders from '@/mocks/fixtures/orders.json';

const products = productsData.items as Product[];

describe('SF-06 Fixtures & Images', () => {
  describe('Schema Validation', () => {
    it('validates store.json against StoreConfigSchema', () => {
      expect(() => StoreConfigSchema.parse(store)).not.toThrow();
    });

    it('validates home.json against HomeContentSchema', () => {
      expect(() => HomeContentSchema.parse(home)).not.toThrow();
    });

    it('validates categories.json against CategoryListSchema', () => {
      expect(() => CategoryListSchema.parse(categories)).not.toThrow();
    });

    it('validates every product against ProductSchema', () => {
      expect(products).toHaveLength(24);
      for (const prod of products) {
        expect(() => ProductSchema.parse(prod)).not.toThrow();
      }
    });

    it('validates users against CustomerSchema after removing password', () => {
      expect(users.items.length).toBeGreaterThan(0);
      for (const user of users.items) {
        const { password: _, ...customer } = user;
        expect(_).toBeDefined();
        expect(() => CustomerSchema.parse(customer)).not.toThrow();
      }
    });

    it('validates orders against OrderSchema after removing mock fields', () => {
      expect(orders.items.length).toBeGreaterThan(0);
      for (const order of orders.items) {
        const { customerId: _cid, confirmationToken: _ctok, ...cleanOrder } = order;
        expect(_cid).toBeDefined();
        expect(_ctok).toBeDefined();
        expect(() => OrderSchema.parse(cleanOrder)).not.toThrow();
      }
    });
  });

  describe('Categories and Product Counts', () => {
    it('has 5 categories with expected counts (5, 5, 5, 4, 5)', () => {
      expect(categories.items).toHaveLength(5);
      const counts = categories.items.map((c) => c.productCount);
      expect(counts).toEqual([5, 5, 5, 4, 5]);

      for (const cat of categories.items) {
        const matching = products.filter((p) => p.category.slug === cat.slug);
        expect(matching.length).toBe(cat.productCount);
      }
    });
  });

  describe('Products and Variants Derivation Rules', () => {
    it('has 24 products with prod_001..prod_024 ids in order and unique slugs', () => {
      expect(products).toHaveLength(24);
      const slugs = new Set<string>();

      products.forEach((prod, index) => {
        const expectedId = `prod_${String(index + 1).padStart(3, '0')}`;
        expect(prod.id).toBe(expectedId);
        expect(slugs.has(prod.slug)).toBe(false);
        slugs.add(prod.slug);
      });
    });

    it('has exactly 60 total variants with correct ids and skus', () => {
      const allVariants = products.flatMap((p) => p.variants);
      expect(allVariants).toHaveLength(60);

      const variantIds = new Set<string>();
      for (const prod of products) {
        for (const variant of prod.variants) {
          expect(variantIds.has(variant.id)).toBe(false);
          variantIds.add(variant.id);
          expect(variant.id).toMatch(new RegExp(`^var_${prod.slug}_`));
          expect(variant.sku).toMatch(/^AUR-\d{3}(-[A-Z0-9]{3})+$/);
        }
      }
    });

    it('derives product price, defaultVariantId, stockStatus and swatches correctly', () => {
      for (const prod of products) {
        const minPrice = Math.min(...prod.variants.map((v) => v.price.amount));
        expect(prod.price.amount).toBe(minPrice);

        // Aggregate stockStatus rule:
        // in_stock if any variant is in_stock, else low_stock if any is low_stock, else out_of_stock
        let expectedAggregate: StockStatus = 'out_of_stock';
        if (prod.variants.some((v) => v.stockStatus === 'in_stock')) {
          expectedAggregate = 'in_stock';
        } else if (prod.variants.some((v) => v.stockStatus === 'low_stock')) {
          expectedAggregate = 'low_stock';
        }
        expect(prod.stockStatus).toBe(expectedAggregate);

        // defaultVariantId is the first variant with availableQuantity > 0, else first variant
        const firstAvailable = prod.variants.find((v) => v.availableQuantity > 0);
        const expectedDefault = firstAvailable ? firstAvailable.id : prod.variants[0].id;
        expect(prod.defaultVariantId).toBe(expectedDefault);

        // swatches equal the Color option values or []
        const colorOption = prod.options.find((o) => o.name === 'Color');
        const expectedSwatches = colorOption ? colorOption.values : [];
        expect(prod.swatches).toEqual(expectedSwatches);
      }
    });

    it('has exact sale, new, out_of_stock, and low_stock product sets', () => {
      const saleSlugs = products.filter((p) => p.compareAtPrice !== null).map((p) => p.slug);
      expect(saleSlugs).toEqual([
        'tide-dinner-plates',
        'meadow-napkins',
        'halo-pendant',
        'archive-box',
        'weekend-duffle',
      ]);

      const newProducts = products.filter((p) => p.badges.includes('new'));
      expect(newProducts).toHaveLength(5);

      const oosSlugs = products.filter((p) => p.stockStatus === 'out_of_stock').map((p) => p.slug);
      expect(oosSlugs).toEqual(['ember-teapot']);

      const lowStockSlugs = products
        .filter((p) => p.stockStatus === 'low_stock')
        .map((p) => p.slug);
      expect(lowStockSlugs).toEqual(['hollow-bud-vase', 'dusk-floor-lamp']);
    });

    it('has cheapest product 95000 and most expensive 2190000', () => {
      const prices = products.map((p) => p.price.amount);
      expect(Math.min(...prices)).toBe(95000);
      expect(Math.max(...prices)).toBe(2190000);
    });
  });

  describe('Orders recomputation', () => {
    it('matches subtotal, shipping, tax and total for every stored order', () => {
      for (const order of orders.items) {
        const subtotal = order.lines.reduce(
          (sum: number, line: { lineTotal: { amount: number } }) => sum + line.lineTotal.amount,
          0,
        );
        expect(order.subtotal.amount).toBe(subtotal);

        // shipping: method price, or 0 when freeOverThreshold and subtotal >= 500000
        const isFree = order.shippingMethod.id === 'standard' && subtotal >= 500000;
        const expectedShipping = isFree ? 0 : order.shippingMethod.id === 'express' ? 15000 : 8000;
        expect(order.shipping.amount).toBe(expectedShipping);

        // tax: Math.round((subtotal + shipping) * 500 / 10000)
        const expectedTax = Math.round(((subtotal + expectedShipping) * 500) / 10000);
        expect(order.tax.amount).toBe(expectedTax);

        const expectedTotal = subtotal + expectedShipping + expectedTax;
        expect(order.total.amount).toBe(expectedTotal);
      }
    });
  });

  describe('Product placeholder images', () => {
    it('verifies that every image URL on every product exists in public directory', () => {
      for (const prod of products) {
        expect(prod.images.length).toBeGreaterThanOrEqual(1);
        for (const img of prod.images) {
          const filePath = path.join(process.cwd(), 'public', img.url.replace(/^\//, ''));
          expect(fs.existsSync(filePath)).toBe(true);
        }
      }

      // Editorial images exist
      const heroPath = path.join(process.cwd(), 'public/mock/editorial/hero.jpg');
      const workshopPath = path.join(process.cwd(), 'public/mock/editorial/workshop.jpg');
      expect(fs.existsSync(heroPath)).toBe(true);
      expect(fs.existsSync(workshopPath)).toBe(true);
    });
  });
});
