'use client';

import * as React from 'react';
import { ShoppingBag } from 'lucide-react';
import { useCartStore } from '@/stores/cart-store';

export default function CartButton() {
  const cart = useCartStore((s) => s.cart);
  const openDrawer = useCartStore((s) => s.openDrawer);
  const count = cart?.itemCount ?? 0;
  const label = `Cart, ${count} ${count === 1 ? 'item' : 'items'}`;

  return (
    <button
      id="header-cart-button"
      type="button"
      aria-label={label}
      onClick={openDrawer}
      className="inline-flex size-11 items-center justify-center rounded-pill text-fg hover:bg-surface-2 transition-colors relative"
    >
      <ShoppingBag size={20} strokeWidth={1.5} aria-hidden="true" />
      {count > 0 && (
        <span className="absolute -right-0.5 -top-0.5 flex min-w-5 h-5 px-1 items-center justify-center rounded-pill bg-accent text-accent-fg text-caption font-semibold leading-none">
          {count}
        </span>
      )}
    </button>
  );
}
