import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import ConfirmationView from '@/components/order/ConfirmationView';
import { ApiError } from '@/lib/api/errors';
import type { Order } from '@/lib/api/types';
import { initialSessionState, useSessionStore } from '@/stores/session-store';

const mockTl = {
  to: vi.fn().mockReturnThis(),
  from: vi.fn().mockReturnThis(),
  set: vi.fn().mockReturnThis(),
};

vi.mock('@/lib/motion/gsap', () => ({
  useGSAP: () => {},
  gsap: {
    matchMedia: () => ({
      add: (_condition: string, callback: () => void) => {
        callback();
      },
    }),
    timeline: () => mockTl,
    fromTo: () => {},
    to: () => {},
    set: () => {},
  },
  SplitText: {
    create: () => ({
      lines: [],
      revert: () => {},
    }),
  },
  ScrollTrigger: {},
}));

vi.mock('next/navigation', () => ({
  useRouter: () => ({
    push: vi.fn(),
    replace: vi.fn(),
  }),
  usePathname: () => '/order-confirmation/AUR-100200',
}));

const mockGet = vi.fn();
const mockMe = vi.fn();

vi.mock('@/lib/api/browser', () => ({
  browserApi: {
    orders: {
      get: (...args: unknown[]) => mockGet(...args),
    },
    auth: {
      me: (...args: unknown[]) => mockMe(...args),
    },
  },
}));

const mockOrder: Order = {
  id: 'ord_0200',
  number: 'AUR-100200',
  status: 'placed',
  paymentStatus: 'pending',
  placedAt: '2026-11-26T08:20:00Z',
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
    price: { amount: 8000, currency: 'BDT' },
  },
  paymentMethod: { id: 'cod', label: 'Cash on delivery' },
  lines: [
    {
      id: 'oline_1',
      productSlug: 'ondo-stoneware-mug',
      productName: 'Ondo Stoneware Mug',
      variantTitle: 'Sand',
      sku: 'AUR-001-SAN',
      image: null,
      unitPrice: { amount: 145000, currency: 'BDT' },
      quantity: 2,
      lineTotal: { amount: 290000, currency: 'BDT' },
    },
  ],
  subtotal: { amount: 290000, currency: 'BDT' },
  shipping: { amount: 8000, currency: 'BDT' },
  tax: { amount: 14900, currency: 'BDT' },
  total: { amount: 312900, currency: 'BDT' },
  note: null,
};

describe('SF-28 Order confirmation page', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    useSessionStore.setState({ ...initialSessionState, status: 'guest' });
    mockGet.mockResolvedValue(mockOrder);
    mockMe.mockRejectedValue(new ApiError(401, 'UNAUTHORIZED', 'Not authenticated'));
  });

  it('renders order confirmation with details for guest user', async () => {
    render(<ConfirmationView orderNumber="AUR-100200" token="tok_x" />);

    await waitFor(() => {
      expect(screen.getByRole('heading', { level: 1 })).toHaveTextContent('Thank you, Nadia!');
    });

    expect(screen.getByRole('img', { name: 'Order confirmed' })).toBeInTheDocument();
    expect(screen.getByText('AUR-100200')).toBeInTheDocument();
    expect(
      screen.getByText('A confirmation will be sent to nadia@example.com.'),
    ).toBeInTheDocument();
    expect(screen.getByText('It ships with Standard delivery')).toBeInTheDocument();
    expect(screen.getByText('You pay ৳3,129 in cash on delivery')).toBeInTheDocument();
    expect(screen.getByText('Bangladesh')).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'Create an account' })).toBeInTheDocument();

    const bodyText = document.body.textContent || '';
    expect(bodyText).not.toContain('has been sent');
    expect(bodyText).not.toContain("We've sent");
  });

  it('calls orders.get with orderNumber and token', async () => {
    render(<ConfirmationView orderNumber="AUR-100200" token="tok_x" />);

    await waitFor(() => {
      expect(mockGet).toHaveBeenCalledWith('AUR-100200', 'tok_x');
    });
  });

  it('shows 404 state when order is not found', async () => {
    mockGet.mockRejectedValue(new ApiError(404, 'NOT_FOUND', 'Order not found'));

    render(<ConfirmationView orderNumber="AUR-999999" />);

    await waitFor(() => {
      expect(screen.getByRole('heading', { level: 1 })).toHaveTextContent(
        "We couldn't find this order.",
      );
    });

    expect(screen.getByRole('link', { name: 'Go to the shop' })).toHaveTextContent(
      'Go to the shop',
    );
  });
});
