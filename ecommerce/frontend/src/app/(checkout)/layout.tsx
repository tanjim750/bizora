import * as React from 'react';
import { serverApi } from '@/lib/api/server';
import SkipLink from '@/components/layout/SkipLink';
import CheckoutHeader from '@/components/layout/CheckoutHeader';
import { Container } from '@/components/ui/Container';

export default async function CheckoutLayout({ children }: { children: React.ReactNode }) {
  const store = await serverApi.store.get();

  return (
    <div className="min-h-screen flex flex-col bg-bg text-fg">
      <SkipLink />
      <CheckoutHeader storeName={store.name} />
      <main id="main" tabIndex={-1} className="outline-none flex-1">
        {children}
      </main>
      <footer className="border-t border-border py-8 text-small text-fg-muted">
        <Container className="text-center">
          Questions?{' '}
          <a
            href={`mailto:${store.supportEmail}`}
            className="text-accent underline hover:text-accent/80"
          >
            {store.supportEmail}
          </a>
        </Container>
      </footer>
    </div>
  );
}
