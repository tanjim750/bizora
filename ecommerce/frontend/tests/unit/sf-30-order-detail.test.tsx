import React from 'react';
import { render, screen, waitFor, within } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import OrderDetail from '@/components/account/OrderDetail';
import { ApiError } from '@/lib/api/errors';
import type { Customer, Order } from '@/lib/api/types';
import { initialSessionState, useSessionStore } from '@/stores/session-store';

const mockPush = vi.fn();
const mockReplace = vi.fn();

vi.mock('next/navigation', () => ({
  useRouter: () => ({
    push: mockPush,
    replace: mockReplace,
  }),
  usePathname: () => '/account/orders/AUR-100117',
}));

const mockGet = vi.fn();

vi.mock('@/lib/api/browser', () => ({
  browserApi: {
    orders: {
      get: (...args: unknown[]) => mockGet(...args),
    },
  },
}));

const mockCustomer: Customer = {
  id: 'cust_01',
  email: 'nadia@example.com',
  firstName: 'Nadia',
  lastName: 'Rahman',
  createdAt: '2026-03-15T10:00:00Z',
};

const mockOrderShipped: Order = {
  id: 'ord_0117',
  number: 'AUR-100117',
  status: 'shipped',
  paymentStatus: 'pending',
  placedAt: '2026-10-21T15:05:00Z',
  email: 'nadia@example.com',
  phone: '+8801712345678',
  shippingAddress: {
    firstName: 'Nadia',
    lastName: 'Rahman',
    line1: 'House 12, Road 5',
    line2: null,
    city: 'Dhaka',
    postalCode: '1209',
    countryCode: 'BD',
  },
  shippingMethod: {
    id: 'standard',
    label: 'Standard delivery',
    price: { amount: 0, currency: 'BDT' },
  },
  paymentMethod: {
    id: 'cod',
    label: 'Cash on delivery',
  },
  lines: [
    {
      id: 'oline_1',
      productSlug: 'ondo-stoneware-mug',
      productName: 'Ondo Stoneware Mug',
      variantTitle: 'Sand',
      sku: 'AUR-001-SAN',
      image: null,
      unitPrice: { amount: 145000, currency: 'BDT' },
      quantity: 1,
      lineTotal: { amount: 145000, currency: 'BDT' },
    },
  ],
  subtotal: { amount: 145000, currency: 'BDT' },
  shipping: { amount: 0, currency: 'BDT' },
  tax: { amount: 7250, currency: 'BDT' },
  total: { amount: 152250, currency: 'BDT' },
  note: null,
};

const mockOrderCancelled: Order = {
  ...mockOrderShipped,
  number: 'AUR-100115',
  status: 'cancelled',
};

describe('SF-30 Order detail page', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    useSessionStore.setState({ ...initialSessionState, status: 'signed-in', user: mockCustomer });
    mockGet.mockResolvedValue(mockOrderShipped);
  });

  it('renders order detail with progress track, free delivery and all orders link', async () => {
    render(<OrderDetail orderNumber="AUR-100117" />);

    await waitFor(() => {
      expect(screen.getByRole('heading', { level: 1 })).toHaveTextContent('Order AUR-100117');
    });

    expect(screen.getByText('Placed on 21 Oct 2026')).toBeInTheDocument();
    expect(screen.getAllByText('Shipped')).toHaveLength(2);
    expect(screen.getByText('Payment pending')).toBeInTheDocument();

    const progressList = screen.getByRole('list', { name: 'Order progress' });
    const currentStep = within(progressList).getByText('Shipped').closest('[aria-current="step"]');
    expect(currentStep).not.toBeNull();

    const deliveryMethodHeading = screen.getByRole('heading', {
      level: 2,
      name: 'Delivery method',
    });
    const deliveryMethodSection = deliveryMethodHeading.parentElement!;
    expect(within(deliveryMethodSection).getByText('Free')).toBeInTheDocument();

    expect(screen.getByRole('link', { name: /All orders/i })).toHaveAttribute('href', '/account');
  });

  it('renders cancelled order state without order progress list', async () => {
    mockGet.mockResolvedValueOnce(mockOrderCancelled);

    render(<OrderDetail orderNumber="AUR-100115" />);

    await waitFor(() => {
      expect(screen.getByText('This order was cancelled.')).toBeInTheDocument();
    });

    expect(screen.queryByRole('list', { name: 'Order progress' })).not.toBeInTheDocument();
  });

  it('renders 404 state when order is not found', async () => {
    mockGet.mockRejectedValueOnce(new ApiError(404, 'NOT_FOUND', 'Not found'));

    render(<OrderDetail orderNumber="AUR-999999" />);

    await waitFor(() => {
      expect(screen.getByRole('heading', { level: 1 })).toHaveTextContent(
        "We couldn't find this order.",
      );
    });

    expect(screen.getByRole('link', { name: /All orders/i })).toHaveAttribute('href', '/account');
  });
});
