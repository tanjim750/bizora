'use client';

import * as React from 'react';
import Link from 'next/link';
import { Dialog } from 'radix-ui';
import { motion, AnimatePresence } from 'motion/react';
import { X } from 'lucide-react';
import { useCartStore } from '@/stores/cart-store';
import { usePrefersReducedMotion } from '@/lib/motion/use-reduced-motion';
import { spring, duration } from '@/lib/motion/tokens';
import { formatMoney } from '@/lib/format/money';
import { IconButton } from '@/components/ui/IconButton';
import { Button } from '@/components/ui/Button';
import { Skeleton } from '@/components/ui/Skeleton';
import RollingNumber from '@/components/motion/RollingNumber';
import FreeShippingMeter from './FreeShippingMeter';
import CartLine from './CartLine';
import type { Money } from '@/lib/api/types';

export interface CartDrawerProps {
  freeShippingThreshold: Money | null;
}

export default function CartDrawer({ freeShippingThreshold }: CartDrawerProps) {
  const drawerOpen = useCartStore((s) => s.drawerOpen);
  const closeDrawer = useCartStore((s) => s.closeDrawer);
  const cart = useCartStore((s) => s.cart);
  const status = useCartStore((s) => s.status);
  const hydrate = useCartStore((s) => s.hydrate);
  const reduced = usePrefersReducedMotion();

  const itemCount = cart?.itemCount ?? 0;
  const lines = cart?.lines ?? [];
  const hasLines = lines.length > 0;

  return (
    <Dialog.Root open={drawerOpen} onOpenChange={(open) => !open && closeDrawer()}>
      <AnimatePresence>
        {drawerOpen && (
          <Dialog.Portal forceMount>
            <Dialog.Overlay asChild>
              <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                transition={{ duration: duration.base }}
                className="fixed inset-0 z-(--aur-z-overlay) bg-overlay backdrop-blur-xs"
              />
            </Dialog.Overlay>

            <Dialog.Content asChild>
              <motion.div
                initial={reduced ? { opacity: 0 } : { x: '100%', opacity: 1 }}
                animate={reduced ? { opacity: 1 } : { x: 0, opacity: 1 }}
                exit={reduced ? { opacity: 0 } : { x: '100%', opacity: 1 }}
                transition={reduced ? { duration: 0.15 } : spring.snappy}
                className="fixed right-0 top-0 h-dvh w-full sm:max-w-md bg-surface shadow-modal sm:rounded-l-lg flex flex-col z-(--aur-z-drawer) focus:outline-none"
              >
                {/* Header */}
                <div className="flex h-16 items-center justify-between border-b border-border px-6">
                  <Dialog.Title className="font-display text-title font-semibold text-fg">
                    Your cart ({itemCount})
                  </Dialog.Title>
                  <Dialog.Description className="sr-only">
                    Review the items in your cart.
                  </Dialog.Description>
                  <Dialog.Close asChild>
                    <IconButton aria-label="Close cart" onClick={closeDrawer}>
                      <X size={20} strokeWidth={1.5} aria-hidden="true" />
                    </IconButton>
                  </Dialog.Close>
                </div>

                {/* Body */}
                <div className="flex-1 overflow-y-auto px-6 py-6 space-y-6">
                  {status === 'loading' && !cart && (
                    <div className="space-y-4">
                      <div className="flex gap-4">
                        <Skeleton className="size-20 rounded-md" />
                        <div className="flex-1 space-y-2">
                          <Skeleton className="h-4 w-3/4 rounded" />
                          <Skeleton className="h-4 w-1/2 rounded" />
                        </div>
                      </div>
                      <div className="flex gap-4">
                        <Skeleton className="size-20 rounded-md" />
                        <div className="flex-1 space-y-2">
                          <Skeleton className="h-4 w-3/4 rounded" />
                          <Skeleton className="h-4 w-1/2 rounded" />
                        </div>
                      </div>
                    </div>
                  )}

                  {status === 'error' && (
                    <div className="text-center py-12 space-y-4">
                      <p className="text-body text-fg-muted">We couldn&apos;t load your cart.</p>
                      <Button variant="secondary" onClick={() => void hydrate()}>
                        Try again
                      </Button>
                    </div>
                  )}

                  {status !== 'error' && !hasLines && (
                    <div className="text-center py-16 space-y-4">
                      <p className="text-body text-fg-muted">Your cart is empty.</p>
                      <Button asChild variant="primary" onClick={closeDrawer}>
                        <Link href="/shop">Start shopping</Link>
                      </Button>
                    </div>
                  )}

                  {hasLines && (
                    <>
                      <FreeShippingMeter
                        remaining={cart?.freeShippingRemaining ?? null}
                        threshold={freeShippingThreshold}
                      />
                      <ul className="divide-y divide-border">
                        <AnimatePresence initial={false}>
                          {lines.map((line) => (
                            <CartLine key={line.id} line={line} />
                          ))}
                        </AnimatePresence>
                      </ul>
                    </>
                  )}
                </div>

                {/* Footer */}
                {hasLines && cart && (
                  <div className="border-t border-border p-6 bg-surface space-y-4">
                    <div className="flex items-center justify-between text-body font-medium text-fg">
                      <span>Subtotal</span>
                      <span className="font-semibold text-title">
                        <RollingNumber value={formatMoney(cart.subtotal)} />
                      </span>
                    </div>

                    <p className="text-caption text-fg-muted">
                      Delivery and VAT are calculated at checkout.
                    </p>

                    <div className="space-y-2 pt-2">
                      <Button asChild variant="primary" className="w-full" onClick={closeDrawer}>
                        <Link href="/checkout">Checkout</Link>
                      </Button>
                      <Button
                        asChild
                        variant="ghost"
                        className="w-full text-body-sm text-fg-muted hover:text-fg"
                        onClick={closeDrawer}
                      >
                        <Link href="/cart">View cart</Link>
                      </Button>
                    </div>
                  </div>
                )}
              </motion.div>
            </Dialog.Content>
          </Dialog.Portal>
        )}
      </AnimatePresence>
    </Dialog.Root>
  );
}
