'use client';

import * as React from 'react';
import Link from 'next/link';
import { usePathname, useSearchParams } from 'next/navigation';
import { Menu } from 'lucide-react';
import { useUiStore } from '@/stores/ui-store';
import { Container } from '@/components/ui/Container';
import { IconButton } from '@/components/ui/IconButton';
import SearchButton from './SearchButton';
import AccountLink from './AccountLink';
import CartButton from './CartButton';
import ThemeToggle from './ThemeToggle';
import MobileNav from './MobileNav';
import type { Category } from '@/lib/api/types';

function MainNavInner({ categories }: { categories: Category[] }) {
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const currentCategory = searchParams ? searchParams.get('category') : null;

  const isShopAllActive = pathname === '/shop' && !currentCategory;

  return (
    <nav aria-label="Main" className="hidden lg:flex items-center gap-6">
      <Link
        href="/shop"
        aria-current={isShopAllActive ? 'page' : undefined}
        className="relative py-2 text-body font-medium text-fg hover:text-accent transition-colors"
      >
        <span>Shop all</span>
        <span
          className={`absolute inset-x-0 bottom-0 h-0.5 bg-accent origin-left transition-transform duration-200 ${
            isShopAllActive ? 'scale-x-100' : 'scale-x-0'
          }`}
        />
      </Link>
      {categories.map((cat) => {
        const isActive = pathname === '/shop' && currentCategory === cat.slug;
        return (
          <Link
            key={cat.id}
            href={`/shop?category=${cat.slug}`}
            aria-current={isActive ? 'page' : undefined}
            className="relative py-2 text-body font-medium text-fg hover:text-accent transition-colors"
          >
            <span>{cat.name}</span>
            <span
              className={`absolute inset-x-0 bottom-0 h-0.5 bg-accent origin-left transition-transform duration-200 ${
                isActive ? 'scale-x-100' : 'scale-x-0'
              }`}
            />
          </Link>
        );
      })}
    </nav>
  );
}

function MainNav({ categories }: { categories: Category[] }) {
  return (
    <React.Suspense fallback={null}>
      <MainNavInner categories={categories} />
    </React.Suspense>
  );
}

export default function Header({
  storeName,
  categories,
}: {
  storeName: string;
  categories: Category[];
}) {
  const setMobileNavOpen = useUiStore((s) => s.setMobileNavOpen);
  const [scrolled, setScrolled] = React.useState(false);

  React.useEffect(() => {
    let rafId: number | null = null;
    const handleScroll = () => {
      if (rafId !== null) return;
      rafId = window.requestAnimationFrame(() => {
        setScrolled(window.scrollY > 24);
        rafId = null;
      });
    };

    window.addEventListener('scroll', handleScroll, { passive: true });
    return () => {
      window.removeEventListener('scroll', handleScroll);
      if (rafId !== null) window.cancelAnimationFrame(rafId);
    };
  }, []);

  return (
    <header
      data-scrolled={scrolled}
      className="sticky top-0 z-(--aur-z-header) bg-bg border-b border-transparent data-[scrolled=true]:border-border transition-colors duration-200"
    >
      <Container>
        <div className="flex h-16 lg:h-18 items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <IconButton
              aria-label="Open menu"
              onClick={() => setMobileNavOpen(true)}
              className="lg:hidden"
            >
              <Menu size={22} strokeWidth={1.5} aria-hidden="true" />
            </IconButton>

            <Link
              href="/"
              aria-label={`${storeName} home`}
              className="font-display text-title font-semibold tracking-tight text-fg"
            >
              {storeName}
            </Link>
          </div>

          <MainNav categories={categories} />

          <div className="flex items-center gap-1 sm:gap-2">
            <SearchButton />
            <div className="hidden sm:inline-flex">
              <ThemeToggle />
            </div>
            <AccountLink />
            <CartButton />
          </div>
        </div>
      </Container>
      <MobileNav categories={categories} />
    </header>
  );
}
