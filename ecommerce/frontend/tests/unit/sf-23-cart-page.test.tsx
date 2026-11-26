import React from 'react';
import { render, screen, fireEvent, within, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import CartPageView from '@/components/cart/CartPageView';
import { useCartStore, initialCartState } from '@/stores/cart-store';
import type { Cart, ProductSummary } from '@/lib/api/types';

const mockCartGet = vi.fn();
const mockListProducts = vi.fn();

vi.mock('@/lib/api/browser', () => ({
  browserApi: {
    cart: {
      get: () => mockCartGet(),
    },
    catalog: {
      listProducts: (args: any) => mockListProducts(args),
    },
  },
}));

vi.mock('next/navigation', () => ({
  useRouter: () => ({ push: vi.fn(), replace: vi.fn() }),
  usePathname: () => '/cart',
  useSearchParams: () => new URLSearchParams(),
}));

const sampleCart: Cart = {
  id: 'cart_1',
  itemCount: 2,
  lines: [
    {
      id: 'line_01',
      variantId: 'var_mug',
      productSlug: 'ondo-stoneware-mug',
      productName: 'Ondo Stoneware Mug',
      variantTitle: 'Sand / Standard',
      image: {
        url: '/mock/mug.webp',
        alt: 'Ondo Stoneware Mug',
        width: 800,
        height: 1000,
      },
      unitPrice: { amount: 145000, currency: 'BDT' },
      compareAtUnitPrice: null,
      quantity: 2,
      lineTotal: { amount: 290000, currency: 'BDT' },
      maxQuantity: 10,
      stockStatus: 'in_stock',
    },
  ],
  subtotal: { amount: 290000, currency: 'BDT' },
  freeShippingRemaining: { amount: 210000, currency: 'BDT' },
  updatedAt: '2026-11-26T00:00:00Z',
};

const mockFeaturedProducts: ProductSummary[] = [
  {
    id: 'prod_1',
    slug: 'featured-item-1',
    name: 'Featured Item 1',
    subtitle: 'Subtitle 1',
    category: {
      slug: 'ceramics',
      name: 'Ceramics',
    },
    images: [
      {
        url: '/mock/prod1.webp',
        alt: 'Featured Item 1',
        width: 800,
        height: 1000,
      },
    ],
    price: { amount: 120000, currency: 'BDT' },
    compareAtPrice: null,
    badges: [],
    stockStatus: 'in_stock',
    swatches: [],
  },
];

describe('SF-23 Cart page', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    useCartStore.setState(initialCartState);
  });

  it('renders cart with lines, subtotal, checkout button, and COD indicator', () => {
    useCartStore.setState({ cart: sampleCart, status: 'ready' });

    render(
      <CartPageView
        freeShippingThreshold={{ amount: 500000, currency: 'BDT' }}
        codAvailable={true}
      />,
    );

    expect(screen.getByRole('heading', { level: 1, name: 'Your cart' })).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'Ondo Stoneware Mug' })).toBeInTheDocument();

    const summaryAside = screen.getByRole('complementary', { name: 'Summary' });
    expect(within(summaryAside).getByText('Subtotal')).toBeInTheDocument();
    expect(within(summaryAside).getByText('৳2,900')).toBeInTheDocument();

    const checkoutLink = screen.getByRole('link', { name: 'Checkout' });
    expect(checkoutLink).toHaveAttribute('href', '/checkout');

    expect(screen.getByText('Cash on delivery available')).toBeInTheDocument();
  });

  it('renders empty cart state and loads featured products under Most loved', async () => {
    mockListProducts.mockResolvedValueOnce({ items: mockFeaturedProducts });

    const emptyCart: Cart = {
      ...sampleCart,
      itemCount: 0,
      lines: [],
      subtotal: { amount: 0, currency: 'BDT' },
    };
    useCartStore.setState({ cart: emptyCart, status: 'ready' });

    render(
      <CartPageView
        freeShippingThreshold={{ amount: 500000, currency: 'BDT' }}
        codAvailable={true}
      />,
    );

    expect(screen.getByText('Your cart is empty.')).toBeInTheDocument();
    const shopLink = screen.getByRole('link', { name: 'Start shopping' });
    expect(shopLink).toHaveAttribute('href', '/shop');

    expect(mockListProducts).toHaveBeenCalledWith({
      collection: 'featured',
      pageSize: 4,
    });

    await waitFor(() => {
      expect(screen.getByRole('heading', { level: 2, name: 'Most loved' })).toBeInTheDocument();
    });
  });

  it('renders error state and clicking Try again calls cart.get', async () => {
    mockCartGet.mockResolvedValueOnce(sampleCart);
    useCartStore.setState({ cart: null, status: 'error', error: 'Network error' });

    render(
      <CartPageView
        freeShippingThreshold={{ amount: 500000, currency: 'BDT' }}
        codAvailable={true}
      />,
    );

    expect(screen.getByText("We couldn't load your cart.")).toBeInTheDocument();
    const retryBtn = screen.getByRole('button', { name: 'Try again' });
    fireEvent.click(retryBtn);

    expect(mockCartGet).toHaveBeenCalled();
  });
});
