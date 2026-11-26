import * as React from 'react';
import Link from 'next/link';
import { Button, Container } from '@/components/ui';

export default function NotFound() {
  return (
    <main
      id="main"
      tabIndex={-1}
      className="min-h-dvh flex items-center justify-center outline-none"
    >
      <Container className="py-32 text-center flex flex-col items-center">
        <h1 className="font-display text-display-lg text-fg">Page not found</h1>
        <p className="text-body-lg text-fg-muted max-w-md mt-4 mb-8">
          The page you&apos;re looking for has moved or never existed.
        </p>
        <div className="flex flex-wrap items-center justify-center gap-4">
          <Button asChild variant="primary">
            <Link href="/">Go home</Link>
          </Button>
          <Button asChild variant="secondary">
            <Link href="/shop">Browse the shop</Link>
          </Button>
        </div>
      </Container>
    </main>
  );
}
