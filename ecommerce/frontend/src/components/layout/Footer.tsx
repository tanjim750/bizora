import * as React from 'react';
import Link from 'next/link';
import { Container } from '@/components/ui/Container';
import ThemeToggle from './ThemeToggle';
import type { Category, StoreConfig } from '@/lib/api/types';

export default function Footer({
  store,
  categories,
}: {
  store: StoreConfig;
  categories: Category[];
}) {
  return (
    <footer className="border-t border-border bg-surface py-16 text-fg">
      <Container>
        <div className="grid grid-cols-1 md:grid-cols-4 lg:grid-cols-5 gap-10">
          <div className="md:col-span-2 space-y-4">
            <span className="font-display text-title font-semibold tracking-tight text-fg block">
              {store.name}
            </span>
            <p className="text-body text-fg-muted max-w-sm">{store.tagline}</p>
            <div id="newsletter-slot" className="pt-2" />
          </div>

          <div className="space-y-4">
            <span className="text-caption font-semibold uppercase tracking-wider text-fg-muted block">
              Shop
            </span>
            <ul className="space-y-2.5">
              <li>
                <Link
                  href="/shop"
                  className="text-body text-fg hover:text-accent transition-colors"
                >
                  All products
                </Link>
              </li>
              {categories.map((cat) => (
                <li key={cat.id}>
                  <Link
                    href={`/shop?category=${cat.slug}`}
                    className="text-body text-fg hover:text-accent transition-colors"
                  >
                    {cat.name}
                  </Link>
                </li>
              ))}
            </ul>
          </div>

          <div className="space-y-4">
            <span className="text-caption font-semibold uppercase tracking-wider text-fg-muted block">
              Help
            </span>
            <ul className="space-y-2.5">
              <li>
                <Link
                  href="/shop"
                  title="Policy pages are coming soon"
                  className="text-body text-fg hover:text-accent transition-colors"
                >
                  Delivery
                </Link>
              </li>
              <li>
                <Link
                  href="/shop"
                  title="Policy pages are coming soon"
                  className="text-body text-fg hover:text-accent transition-colors"
                >
                  Returns
                </Link>
              </li>
              <li>
                <a
                  href={`mailto:${store.supportEmail}`}
                  className="text-body text-fg hover:text-accent transition-colors"
                >
                  Contact
                </a>
              </li>
            </ul>
          </div>
        </div>

        <div className="mt-16 pt-8 border-t border-border flex flex-col sm:flex-row items-center justify-between gap-4">
          <p className="text-caption text-fg-muted">
            &copy; {new Date().getFullYear()} {store.name}. All rights reserved.
          </p>
          <div className="flex items-center gap-3">
            <span className="text-caption text-fg-muted">Appearance</span>
            <ThemeToggle />
          </div>
        </div>
      </Container>
    </footer>
  );
}
