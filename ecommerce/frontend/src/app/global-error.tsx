'use client';

import * as React from 'react';
import { Button, Container } from '@/components/ui';
import './globals.css';

export default function GlobalError({
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
    <html lang="en">
      <body className="min-h-dvh bg-bg text-fg font-sans antialiased">
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
            <Button variant="primary" onClick={reset}>
              Try again
            </Button>
          </Container>
        </main>
      </body>
    </html>
  );
}
