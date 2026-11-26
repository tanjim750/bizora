'use client';

import * as React from 'react';
import Link from 'next/link';
import { Button, Container } from '@/components/ui';

export default function ErrorPage({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  React.useEffect(() => {
    if (process.env.NODE_ENV === 'development') {
      console.error(error.digest ?? error);
    }
  }, [error]);

  return (
    <main
      id="main"
      tabIndex={-1}
      className="min-h-dvh flex items-center justify-center outline-none"
    >
      <Container className="py-32 text-center flex flex-col items-center">
        <h1 className="font-display text-display-lg text-fg">Something went wrong</h1>
        <p className="text-body-lg text-fg-muted max-w-md mt-4 mb-8">
          Something went wrong on our side. Please try again.
        </p>
        <div className="flex flex-wrap items-center justify-center gap-4">
          <Button variant="primary" onClick={reset}>
            Try again
          </Button>
          <Button asChild variant="secondary">
            <Link href="/">Go home</Link>
          </Button>
        </div>
      </Container>
    </main>
  );
}
