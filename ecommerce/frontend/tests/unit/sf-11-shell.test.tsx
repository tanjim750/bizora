import React from 'react';
import { render, screen, act, fireEvent } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import categoriesFixture from '@/mocks/fixtures/categories.json';
import storeFixture from '@/mocks/fixtures/store.json';
import { useCartStore, initialCartState } from '@/stores/cart-store';
import { useSessionStore, initialSessionState } from '@/stores/session-store';
import { useUiStore, initialUiState } from '@/stores/ui-store';
import Header from '@/components/layout/Header';
import Footer from '@/components/layout/Footer';
import SkipLink from '@/components/layout/SkipLink';
import type { Cart, Category, Customer, StoreConfig } from '@/lib/api/types';

vi.mock('next/navigation', () => ({
  usePathname: () => '/shop',
  useSearchParams: () => new URLSearchParams('category=linen'),
  useRouter: () => ({ push: vi.fn(), replace: vi.fn() }),
}));

vi.mock('next-themes', () => ({
  useTheme: () => ({ resolvedTheme: 'light', setTheme: vi.fn() }),
}));

const mockCategories = categoriesFixture.items as unknown as Category[];
const mockStore = storeFixture as unknown as StoreConfig;

const sampleCart: Cart = {
  id: 'cart_test_123',
  itemCount: 2,
  lines: [
    {
      id: 'line_01',
      variantId: 'var_mug_sand',
      productSlug: 'ondo-stoneware-mug',
      productName: 'Ondo Stoneware Mug',
      variantTitle: 'Sand / Standard',
      image: {
        url: '/mock/mug.webp',
        alt: 'Mug',
        width: 800,
        height: 1000,
      },
      unitPrice: { amount: 280000, currency: 'BDT' },
      compareAtUnitPrice: null,
      quantity: 2,
      lineTotal: { amount: 560000, currency: 'BDT' },
      maxQuantity: 10,
      stockStatus: 'in_stock',
    },
  ],
  subtotal: { amount: 560000, currency: 'BDT' },
  freeShippingRemaining: null,
  updatedAt: '2026-11-26T00:00:00Z',
};

const sampleCustomer: Customer = {
  id: 'cust_01',
  email: 'nadia@example.com',
  firstName: 'Nadia',
  lastName: 'Rahman',
  createdAt: '2026-11-26T00:00:00Z',
};

describe('SF-11 Store Shell', () => {
  beforeEach(() => {
    useCartStore.setState(initialCartState);
    useSessionStore.setState(initialSessionState);
    useUiStore.setState(initialUiState);
  });

  describe('SkipLink', () => {
    it('renders skip to content link with href #main', () => {
      render(<SkipLink />);
      const link = screen.getByRole('link', { name: /skip to content/i });
      expect(link).toHaveAttribute('href', '#main');
    });
  });

  describe('Header', () => {
    it('renders logo, main navigation with active category link, and shell controls', () => {
      render(<Header storeName="Aurelo" categories={mockCategories} />);

      const logo = screen.getByRole('link', { name: 'Aurelo home' });
      expect(logo).toHaveAttribute('href', '/');

      const mainNav = screen.getByRole('navigation', { name: 'Main' });
      expect(mainNav).toBeInTheDocument();

      const shopAllLink = screen.getByRole('link', { name: 'Shop all' });
      expect(shopAllLink).toHaveAttribute('href', '/shop');

      const linenLink = screen.getByRole('link', { name: 'Linen & Textiles' });
      expect(linenLink).toHaveAttribute('aria-current', 'page');
      expect(linenLink).toHaveAttribute('href', '/shop?category=linen');

      expect(screen.getByRole('button', { name: 'Search' })).toBeInTheDocument();
      expect(screen.getByRole('button', { name: 'Open menu' })).toBeInTheDocument();
      expect(screen.getByRole('button', { name: 'Cart, 0 items' })).toBeInTheDocument();
    });

    it('updates cart count and opens cart drawer on CartButton click', () => {
      render(<Header storeName="Aurelo" categories={mockCategories} />);

      act(() => {
        useCartStore.setState({ cart: sampleCart });
      });

      const cartBtn = screen.getByRole('button', { name: 'Cart, 2 items' });
      expect(cartBtn).toBeInTheDocument();

      fireEvent.click(cartBtn);
      expect(useCartStore.getState().drawerOpen).toBe(true);
    });

    it('routes AccountLink based on session status', () => {
      const { rerender } = render(<Header storeName="Aurelo" categories={mockCategories} />);

      const guestAccountLink = screen.getByRole('link', { name: 'Account' });
      expect(guestAccountLink).toHaveAttribute('href', '/account/sign-in');

      act(() => {
        useSessionStore.setState({ user: sampleCustomer, status: 'signed-in' });
      });

      rerender(<Header storeName="Aurelo" categories={mockCategories} />);
      const authAccountLink = screen.getByRole('link', { name: 'Account' });
      expect(authAccountLink).toHaveAttribute('href', '/account');
    });

    it('opens search dialog and mobile nav menu on button clicks', () => {
      render(<Header storeName="Aurelo" categories={mockCategories} />);

      const searchBtn = screen.getByRole('button', { name: 'Search' });
      fireEvent.click(searchBtn);
      expect(useUiStore.getState().searchOpen).toBe(true);

      const menuBtn = screen.getByRole('button', { name: 'Open menu' });
      fireEvent.click(menuBtn);
      expect(useUiStore.getState().mobileNavOpen).toBe(true);

      // Mobile nav dialog appears
      expect(screen.getByRole('dialog', { name: 'Menu' })).toBeInTheDocument();
      const closeBtn = screen.getByRole('button', { name: 'Close menu' });
      fireEvent.click(closeBtn);
      expect(useUiStore.getState().mobileNavOpen).toBe(false);
    });
  });

  describe('Footer', () => {
    it('renders brand, category links, help links, contact mailto, and copyright', () => {
      render(<Footer store={mockStore} categories={mockCategories} />);

      expect(screen.getByText('Aurelo')).toBeInTheDocument();
      expect(screen.getByText(mockStore.tagline)).toBeInTheDocument();

      const contactLink = screen.getByRole('link', { name: /contact/i });
      expect(contactLink).toHaveAttribute('href', `mailto:${mockStore.supportEmail}`);

      const deliveryLink = screen.getByRole('link', { name: /delivery/i });
      expect(deliveryLink).toHaveAttribute('href', '/shop');
      expect(deliveryLink).toHaveAttribute('title', 'Policy pages are coming soon');

      expect(screen.getByText(/© 2026 Aurelo/)).toBeInTheDocument();
      expect(document.getElementById('newsletter-slot')).toBeInTheDocument();
    });
  });
});
