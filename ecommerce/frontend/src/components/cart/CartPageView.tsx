'use client';

import * as React from 'react';
import Link from 'next/link';
import { AnimatePresence } from 'motion/react';
import { Banknote } from 'lucide-react';
import { useCartStore } from '@/stores/cart-store';
import { browserApi } from '@/lib/api/browser';
import { formatMoney } from '@/lib/format/money';
import { Container } from '@/components/ui/Container';
import { Button } from '@/components/ui/Button';
import { Skeleton } from '@/components/ui/Skeleton';
import CartLine from '@/components/cart/CartLine';
import FreeShippingMeter from '@/components/cart/FreeShippingMeter';
import ProductGrid from '@/components/product/ProductGrid';
import type { Money, ProductSummary } from '@/lib/api/types';

export interface CartPageViewProps {
  freeShippingThreshold: Money | null;
  codAvailable: boolean;
}

export default function CartPageView({
  freeShippingThreshold,
  codAvailable,
}: CartPageViewProps) {
  const cart = useCartStore((s) => s.cart);
  const status = useCartStore((s) => s.status);
  const error = useCartStore((s) => s.error);
  const hydrate = useCartStore((s) => s.hydrate);

  const [featuredProducts, setFeaturedProducts] = React.useState<ProductSummary[]>([]);

  // Load featured products once on mount if empty cart
  React.useEffect(() => {
    let active = true;
    if (cart && cart.lines.length === 0) {
      browserApi.catalog
        .listProducts({ collection: 'featured', pageSize: 4 })
        .then((res) => {
          if (active && res.items) {
            setFeaturedProducts(res.items);
          }
        })
        .catch(() => {
          // Failure -> simply not shown
        });
    }
    return () => {
      active = false;
    };
  }, [cart]);

  // Loading state
  if ((status === 'idle' || status === 'loading') && !cart) {
    return (
      <Container className="py-12">
        <h1 className="font-display text-display-lg mb-8">Your cart</h1>
        <div className="lg:grid lg:grid-cols-12 lg:gap-12">
          <div className="lg:col-span-8 space-y-4">
            <Skeleton className="h-36 w-full" />
            <Skeleton className="h-36 w-full" />
          </div>
          <div className="lg:col-span-4 mt-8 lg:mt-0">
            <Skeleton className="h-64 w-full rounded-lg" />
          </div>
        </div>
      </Container>
    );
  }

  // Error state
  if (status === 'error' && !cart) {
    return (
      <Container className="py-12">
        <h1 className="font-display text-display-lg mb-8">Your cart</h1>
        <div className="rounded-lg border border-border bg-surface p-8 text-center space-y-4 max-w-lg mx-auto">
          <p className="text-body text-fg">We couldn&apos;t load your cart.</p>
          {error && <p className="text-caption text-fg-muted">{error}</p>}
          <Button type="button" onClick={() => hydrate()}>
            Try again
          </Button>
        </div>
      </Container>
    );
  }

  // Empty state
  if (!cart || cart.lines.length === 0) {
    return (
      <Container className="py-12">
        <h1 className="font-display text-display-lg mb-8">Your cart</h1>
        <div className="py-16 text-center space-y-6 max-w-md mx-auto">
          <p className="text-title text-fg font-medium">Your cart is empty.</p>
          <Button asChild size="lg">
            <Link href="/shop">Start shopping</Link>
          </Button>
        </div>

        {featuredProducts.length > 0 && (
          <section className="mt-20 pt-12 border-t border-border">
            <h2 className="font-display text-heading-lg mb-8">Most loved</h2>
            <ProductGrid products={featuredProducts} columns="home" />
          </section>
        )}
      </Container>
    );
  }

  // Lines state
  return (
    <Container className="py-12">
      <h1 className="font-display text-display-lg mb-8">Your cart</h1>

      <div className="lg:grid lg:grid-cols-12 lg:gap-12 items-start">
        <ul className="lg:col-span-8 divide-y divide-border">
          <AnimatePresence>
            {cart.lines.map((line) => (
              <CartLine key={line.id} line={line} size="lg" />
            ))}
          </AnimatePresence>
        </ul>

        <aside
          aria-labelledby="summary-title"
          className="lg:col-span-4 lg:sticky lg:top-24 self-start rounded-lg border border-border bg-surface p-6 mt-12 lg:mt-0 space-y-6"
        >
          <h2 id="summary-title" className="text-title font-semibold text-fg">
            Summary
          </h2>

          <div className="flex justify-between items-center text-body">
            <span className="text-fg-muted">Subtotal</span>
            <span className="font-medium text-fg">{formatMoney(cart.subtotal)}</span>
          </div>

          <FreeShippingMeter
            remaining={cart.freeShippingRemaining}
            threshold={freeShippingThreshold}
          />

          <p className="text-caption text-fg-muted">
            Delivery and VAT are calculated at checkout.
          </p>

          <Button asChild size="lg" className="w-full">
            <Link href="/checkout">Checkout</Link>
          </Button>

          {codAvailable && (
            <div className="flex items-center gap-2 text-caption text-fg-muted pt-2 border-t border-border">
              <Banknote size={16} aria-hidden="true" className="shrink-0" />
              <span>Cash on delivery available</span>
            </div>
          )}
        </aside>
      </div>
    </Container>
  );
}
