'use client';

import * as React from 'react';
import { useCartStore } from '@/stores/cart-store';

export default function CartHydrator() {
  React.useEffect(() => {
    void useCartStore.getState().hydrate();
  }, []);

  return null;
}
