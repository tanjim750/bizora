import React from 'react';
import { render, screen, fireEvent, within, act } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import CartDrawer from '@/components/cart/CartDrawer';
import QuantityStepper from '@/components/cart/QuantityStepper';
import FreeShippingMeter from '@/components/cart/FreeShippingMeter';
import { flyToCart } from '@/lib/motion/fly-to-cart';
import { useCartStore, initialCartState } from '@/stores/cart-store';
import type { Cart } from '@/lib/api/types';

const mockUpdateLine = vi.fn();
const mockRemoveLine = vi.fn();
const mockCartGet = vi.fn();

vi.mock('@/lib/api/browser', () => ({
  browserApi: {
    cart: {
      get: () => mockCartGet(),
      addItem: vi.fn(),
      updateLine: (id: string, q: number) => mockUpdateLine(id, q),
      removeLine: (id: string) => mockRemoveLine(id),
    },
  },
}));

vi.mock('next/navigation', () => ({
  useRouter: () => ({ push: vi.fn(), replace: vi.fn() }),
  usePathname: () => '/',
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
        alt: 'Mug',
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

describe('SF-13 Cart Drawer & Interactions', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    useCartStore.setState(initialCartState);
  });

  describe('CartDrawer', () => {
    it('renders drawer with cart items, free delivery meter, subtotal and links', () => {
      useCartStore.setState({ cart: sampleCart, status: 'ready', drawerOpen: true });

      render(<CartDrawer freeShippingThreshold={{ amount: 500000, currency: 'BDT' }} />);

      expect(screen.getByRole('dialog', { name: /your cart \(2\)/i })).toBeInTheDocument();
      expect(screen.getByText(/you're ৳2,100 away from free delivery/i)).toBeInTheDocument();

      const progress = screen.getByRole('progressbar', { name: /progress to free delivery/i });
      expect(progress).toHaveAttribute('aria-valuenow', '58');

      const productLink = screen.getByRole('link', { name: 'Ondo Stoneware Mug' });
      expect(productLink).toHaveAttribute('href', '/products/ondo-stoneware-mug');

      const checkoutLink = screen.getByRole('link', { name: 'Checkout' });
      expect(checkoutLink).toHaveAttribute('href', '/checkout');

      const subtotalRow = screen.getByText('Subtotal').parentElement;
      expect(subtotalRow).toBeDefined();
      expect(within(subtotalRow!).getByText('৳2,900')).toBeInTheDocument();
    });

    it('increases quantity and removes line on interaction', async () => {
      useCartStore.setState({ cart: sampleCart, status: 'ready', drawerOpen: true });
      mockUpdateLine.mockResolvedValueOnce({
        ...sampleCart,
        lines: [{ ...sampleCart.lines[0], quantity: 3 }],
      });
      mockRemoveLine.mockResolvedValueOnce({
        ...sampleCart,
        lines: [],
        itemCount: 0,
      });

      render(<CartDrawer freeShippingThreshold={{ amount: 500000, currency: 'BDT' }} />);

      const increaseBtn = screen.getByRole('button', { name: 'Increase quantity' });
      await act(async () => {
        fireEvent.click(increaseBtn);
      });
      expect(mockUpdateLine).toHaveBeenCalledWith('line_01', 3);

      const removeBtn = screen.getByRole('button', { name: 'Remove Ondo Stoneware Mug' });
      await act(async () => {
        fireEvent.click(removeBtn);
      });
      expect(mockRemoveLine).toHaveBeenCalledWith('line_01');
    });

    it('renders empty cart state with Start shopping link', () => {
      useCartStore.setState({
        cart: { ...sampleCart, lines: [], itemCount: 0 },
        status: 'ready',
        drawerOpen: true,
      });

      render(<CartDrawer freeShippingThreshold={{ amount: 500000, currency: 'BDT' }} />);

      expect(screen.getByText('Your cart is empty.')).toBeInTheDocument();
      const shopLink = screen.getByRole('link', { name: 'Start shopping' });
      expect(shopLink).toHaveAttribute('href', '/shop');
    });

    it('renders error state and retries on Try again click', () => {
      useCartStore.setState({ cart: null, status: 'error', drawerOpen: true });
      mockCartGet.mockResolvedValueOnce(sampleCart);

      render(<CartDrawer freeShippingThreshold={{ amount: 500000, currency: 'BDT' }} />);

      expect(screen.getByText("We couldn't load your cart.")).toBeInTheDocument();
      const retryBtn = screen.getByRole('button', { name: 'Try again' });
      fireEvent.click(retryBtn);
      expect(mockCartGet).toHaveBeenCalledTimes(1);
    });
  });

  describe('QuantityStepper', () => {
    it('disables increase when value reaches max and clamps input', () => {
      const onChange = vi.fn();
      render(<QuantityStepper value={10} max={10} onChange={onChange} label="Test Item" />);

      const increaseBtn = screen.getByRole('button', { name: 'Increase quantity' });
      expect(increaseBtn).toBeDisabled();
      expect(screen.getByText('Max 10')).toBeInTheDocument();

      const input = screen.getByRole('spinbutton', { name: 'Quantity for Test Item' });
      fireEvent.change(input, { target: { value: '50' } });
      fireEvent.blur(input);
      expect(onChange).toHaveBeenCalledWith(10);
    });
  });

  describe('FreeShippingMeter', () => {
    it('renders unlocked state when remaining is 0, and nothing when threshold is null', () => {
      const { rerender } = render(
        <FreeShippingMeter
          remaining={{ amount: 0, currency: 'BDT' }}
          threshold={{ amount: 500000, currency: 'BDT' }}
        />,
      );
      expect(screen.getByText("You've unlocked free standard delivery.")).toBeInTheDocument();

      rerender(
        <FreeShippingMeter remaining={{ amount: 100000, currency: 'BDT' }} threshold={null} />,
      );
      expect(screen.queryByText(/free/i)).not.toBeInTheDocument();
    });
  });

  describe('flyToCart', () => {
    it('resolves safely when source is null or target is missing', async () => {
      await expect(flyToCart(null, { reduced: false })).resolves.toBeUndefined();

      const div = document.createElement('div');
      document.body.appendChild(div);
      await expect(flyToCart(div, { reduced: false })).resolves.toBeUndefined();
      document.body.removeChild(div);
    });
  });
});
