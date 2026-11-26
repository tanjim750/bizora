import React from 'react';
import { render, screen, fireEvent, waitFor, within } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import CheckoutForm from '@/components/checkout/CheckoutForm';
import storeJson from '@/mocks/fixtures/store.json';
import { StoreConfigSchema } from '@/lib/api/schemas';
import { ApiError } from '@/lib/api/errors';
import { useCartStore } from '@/stores/cart-store';
import { useSessionStore, initialSessionState } from '@/stores/session-store';
import type { Cart, Quote } from '@/lib/api/types';

const store = StoreConfigSchema.parse(storeJson);

const mockPush = vi.fn();
const mockReplace = vi.fn();
const mockQuote = vi.fn();
const mockPlaceOrder = vi.fn();
const mockCartGet = vi.fn();
const mockMe = vi.fn();

vi.mock('next/navigation', () => ({
  useRouter: () => ({ push: mockPush, replace: mockReplace }),
  usePathname: () => '/checkout',
  useSearchParams: () => new URLSearchParams(),
}));

vi.mock('@/lib/api/browser', () => ({
  browserApi: {
    checkout: {
      quote: (id: string) => mockQuote(id),
      placeOrder: (body: unknown, key: string) => mockPlaceOrder(body, key),
    },
    cart: {
      get: () => mockCartGet(),
    },
    auth: {
      me: () => mockMe(),
    },
  },
}));

const sampleCart: Cart = {
  id: 'cart_1',
  itemCount: 2,
  lines: [
    {
      id: 'line_01',
      variantId: 'var_ondo-stoneware-mug_sand',
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

const sampleQuote: Quote = {
  subtotal: { amount: 290000, currency: 'BDT' },
  shipping: { amount: 8000, currency: 'BDT' },
  tax: { amount: 14900, currency: 'BDT' },
  total: { amount: 312900, currency: 'BDT' },
  shippingMethodId: 'standard',
  freeShippingApplied: false,
  taxRateBps: 500,
  itemCount: 2,
};

describe('SF-27 Checkout page', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    useCartStore.setState({ cart: sampleCart, status: 'ready' });
    useSessionStore.setState(initialSessionState);
    mockQuote.mockResolvedValue(sampleQuote);
    mockCartGet.mockResolvedValue(sampleCart);
    mockMe.mockRejectedValue(new ApiError(401, 'UNAUTHENTICATED', 'Not logged in'));
  });

  it('renders checkout form sections, disabled card payment, VAT, and total button', async () => {
    render(<CheckoutForm store={store} />);

    expect(screen.getByRole('heading', { name: '1. Contact' })).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: '2. Delivery address' })).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: '3. Delivery method' })).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: '4. Payment' })).toBeInTheDocument();

    const cardRadio = screen.getByRole('radio', { name: /card payment/i });
    expect(cardRadio).toBeDisabled();

    await waitFor(() => {
      expect(screen.getByText('VAT (5%)')).toBeInTheDocument();
      expect(screen.getByRole('button', { name: 'Place order — ৳3,129' })).toBeInTheDocument();
    });
  });

  it('submits empty form and shows error alert with link', async () => {
    render(<CheckoutForm store={store} />);

    await waitFor(() => {
      expect(screen.getByRole('button', { name: 'Place order — ৳3,129' })).toBeInTheDocument();
    });

    fireEvent.click(screen.getByRole('button', { name: 'Place order — ৳3,129' }));

    await waitFor(() => {
      expect(screen.getByText('Please fix these fields:')).toBeInTheDocument();
      const emailErrLink = screen.getByRole('link', {
        name: 'Enter your email address.',
      });
      expect(emailErrLink).toHaveAttribute('href', '#field-email');
      expect(mockPlaceOrder).not.toHaveBeenCalled();
    });
  });

  it('submits valid values, calls placeOrder, resets cart, and redirects', async () => {
    mockPlaceOrder.mockResolvedValueOnce({
      order: {
        number: 'AUR-100200',
        createdAt: '2026-11-26T00:00:00Z',
        lines: [],
        totals: {
          subtotal: { amount: 290000, currency: 'BDT' },
          shipping: { amount: 8000, currency: 'BDT' },
          tax: { amount: 14900, currency: 'BDT' },
          total: { amount: 312900, currency: 'BDT' },
        },
        shippingAddress: {
          firstName: 'Nadia',
          lastName: 'Rahman',
          line1: 'House 12, Road 5',
          line2: null,
          city: 'Dhaka',
          postalCode: '1209',
          countryCode: 'BD',
        },
        shippingMethod: { id: 'standard', label: 'Standard delivery' },
        paymentMethod: { id: 'cod', label: 'Cash on delivery' },
        status: 'placed',
        paymentStatus: 'pending',
      },
      confirmationToken: 'tok_abc',
    });

    render(<CheckoutForm store={store} />);

    await waitFor(() => {
      expect(screen.getByRole('button', { name: 'Place order — ৳3,129' })).toBeInTheDocument();
    });

    fireEvent.change(screen.getByLabelText('Email'), {
      target: { value: 'nadia@example.com' },
    });
    fireEvent.change(screen.getByLabelText('Phone'), {
      target: { value: '+8801712345678' },
    });
    fireEvent.change(screen.getByLabelText('First name'), {
      target: { value: 'Nadia' },
    });
    fireEvent.change(screen.getByLabelText('Last name'), {
      target: { value: 'Rahman' },
    });
    fireEvent.change(screen.getByLabelText('Address'), {
      target: { value: 'House 12, Road 5' },
    });
    fireEvent.change(screen.getByLabelText('City'), {
      target: { value: 'Dhaka' },
    });
    fireEvent.change(screen.getByLabelText('Postal code'), {
      target: { value: '1209' },
    });

    fireEvent.click(screen.getByRole('button', { name: 'Place order — ৳3,129' }));

    await waitFor(() => {
      expect(mockPlaceOrder).toHaveBeenCalled();
      const [body, key] = mockPlaceOrder.mock.calls[0];
      expect(body.expectedTotal.amount).toBe(312900);
      expect(key).toMatch(/^[0-9a-f-]{36}$/);

      expect(mockPush).toHaveBeenCalledWith('/order-confirmation/AUR-100200?token=tok_abc');
      expect(useCartStore.getState().cart).toBeNull();
    });
  });

  it('handles PRICE_CHANGED error and renews key on next submit', async () => {
    const updatedQuote: Quote = {
      ...sampleQuote,
      total: { amount: 330000, currency: 'BDT' },
    };

    mockPlaceOrder.mockRejectedValueOnce(
      new ApiError(409, 'PRICE_CHANGED', 'Price changed', null, {
        quote: updatedQuote,
      }),
    );

    render(<CheckoutForm store={store} />);

    await waitFor(() => {
      expect(screen.getByRole('button', { name: 'Place order — ৳3,129' })).toBeInTheDocument();
    });

    fireEvent.change(screen.getByLabelText('Email'), {
      target: { value: 'nadia@example.com' },
    });
    fireEvent.change(screen.getByLabelText('Phone'), {
      target: { value: '+8801712345678' },
    });
    fireEvent.change(screen.getByLabelText('First name'), {
      target: { value: 'Nadia' },
    });
    fireEvent.change(screen.getByLabelText('Last name'), {
      target: { value: 'Rahman' },
    });
    fireEvent.change(screen.getByLabelText('Address'), {
      target: { value: 'House 12, Road 5' },
    });
    fireEvent.change(screen.getByLabelText('City'), {
      target: { value: 'Dhaka' },
    });
    fireEvent.change(screen.getByLabelText('Postal code'), {
      target: { value: '1209' },
    });

    fireEvent.click(screen.getByRole('button', { name: 'Place order — ৳3,129' }));

    await waitFor(() => {
      expect(
        screen.getByText('Prices changed since you started checkout. Please review the new total.'),
      ).toBeInTheDocument();
      expect(screen.getByRole('button', { name: 'Place order — ৳3,300' })).toBeInTheDocument();
    });

    // Next submit uses new key
    mockPlaceOrder.mockResolvedValueOnce({
      order: { number: 'AUR-1' },
      confirmationToken: 'tok_1',
    });

    fireEvent.click(screen.getByRole('button', { name: 'Place order — ৳3,300' }));

    await waitFor(() => {
      expect(mockPlaceOrder).toHaveBeenCalledTimes(2);
      const key1 = mockPlaceOrder.mock.calls[0][1];
      const key2 = mockPlaceOrder.mock.calls[1][1];
      expect(key1).not.toBe(key2);
    });
  });

  it('handles NETWORK_ERROR and reuses the same key on retry', async () => {
    mockPlaceOrder.mockRejectedValueOnce(new ApiError(0, 'NETWORK_ERROR', 'Network down'));

    render(<CheckoutForm store={store} />);

    await waitFor(() => {
      expect(screen.getByRole('button', { name: 'Place order — ৳3,129' })).toBeInTheDocument();
    });

    fireEvent.change(screen.getByLabelText('Email'), {
      target: { value: 'nadia@example.com' },
    });
    fireEvent.change(screen.getByLabelText('Phone'), {
      target: { value: '+8801712345678' },
    });
    fireEvent.change(screen.getByLabelText('First name'), {
      target: { value: 'Nadia' },
    });
    fireEvent.change(screen.getByLabelText('Last name'), {
      target: { value: 'Rahman' },
    });
    fireEvent.change(screen.getByLabelText('Address'), {
      target: { value: 'House 12, Road 5' },
    });
    fireEvent.change(screen.getByLabelText('City'), {
      target: { value: 'Dhaka' },
    });
    fireEvent.change(screen.getByLabelText('Postal code'), {
      target: { value: '1209' },
    });

    fireEvent.click(screen.getByRole('button', { name: 'Place order — ৳3,129' }));

    await waitFor(() => {
      expect(
        screen.getByText('You seem to be offline. Your order was not placed. Try again.'),
      ).toBeInTheDocument();
    });

    mockPlaceOrder.mockResolvedValueOnce({
      order: { number: 'AUR-2' },
      confirmationToken: 'tok_2',
    });

    fireEvent.click(screen.getByRole('button', { name: 'Place order — ৳3,129' }));

    await waitFor(() => {
      expect(mockPlaceOrder).toHaveBeenCalledTimes(2);
      const key1 = mockPlaceOrder.mock.calls[0][1];
      const key2 = mockPlaceOrder.mock.calls[1][1];
      expect(key1).toBe(key2);
    });
  });

  it('handles OUT_OF_STOCK error and shows out of stock banner with edit cart link', async () => {
    mockPlaceOrder.mockRejectedValueOnce(
      new ApiError(409, 'OUT_OF_STOCK', 'Out of stock', null, {
        lines: [
          {
            lineId: 'line_01',
            variantId: 'var_ondo-stoneware-mug_sand',
            available: 0,
          },
        ],
      }),
    );

    render(<CheckoutForm store={store} />);

    await waitFor(() => {
      expect(screen.getByRole('button', { name: 'Place order — ৳3,129' })).toBeInTheDocument();
    });

    fireEvent.change(screen.getByLabelText('Email'), {
      target: { value: 'nadia@example.com' },
    });
    fireEvent.change(screen.getByLabelText('Phone'), {
      target: { value: '+8801712345678' },
    });
    fireEvent.change(screen.getByLabelText('First name'), {
      target: { value: 'Nadia' },
    });
    fireEvent.change(screen.getByLabelText('Last name'), {
      target: { value: 'Rahman' },
    });
    fireEvent.change(screen.getByLabelText('Address'), {
      target: { value: 'House 12, Road 5' },
    });
    fireEvent.change(screen.getByLabelText('City'), {
      target: { value: 'Dhaka' },
    });
    fireEvent.change(screen.getByLabelText('Postal code'), {
      target: { value: '1209' },
    });

    fireEvent.click(screen.getByRole('button', { name: 'Place order — ৳3,129' }));

    await waitFor(() => {
      const alert = screen.getByRole('alert');
      expect(within(alert).getByText('Some items are no longer available.')).toBeInTheDocument();
      expect(within(alert).getByText('Ondo Stoneware Mug')).toBeInTheDocument();
      expect(within(alert).getByRole('link', { name: 'Edit cart' })).toHaveAttribute(
        'href',
        '/cart',
      );
    });
  });

  it('redirects to /cart if cart is empty', () => {
    useCartStore.setState({
      cart: { ...sampleCart, lines: [], itemCount: 0 },
      status: 'ready',
    });

    render(<CheckoutForm store={store} />);

    expect(mockReplace).toHaveBeenCalledWith('/cart');
  });
});
