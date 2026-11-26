import * as React from 'react';
import Link from 'next/link';
import { Lock } from 'lucide-react';
import { Container } from '@/components/ui/Container';

export interface CheckoutHeaderProps {
  storeName: string;
}

export default function CheckoutHeader({ storeName }: CheckoutHeaderProps) {
  return (
    <header className="border-b border-border bg-bg sticky top-0 z-40">
      <Container className="flex h-16 items-center justify-between">
        <Link
          href="/"
          aria-label={`${storeName} home`}
          className="font-display text-heading font-bold text-fg hover:opacity-80 transition-opacity"
        >
          {storeName}
        </Link>
        <div className="flex items-center gap-2 text-small font-medium text-fg-muted">
          <Lock size={16} aria-hidden="true" />
          <span>Secure checkout</span>
        </div>
        <Link
          href="/cart"
          className="text-small text-accent underline hover:text-accent/80 transition-colors"
        >
          Back to cart
        </Link>
      </Container>
    </header>
  );
}
