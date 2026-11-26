import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import AccountGuard from '@/components/account/AccountGuard';
import AccountView from '@/components/account/AccountView';
import StatusBadge from '@/components/account/StatusBadge';
import type { Customer, OrderList } from '@/lib/api/types';
import { initialSessionState, useSessionStore } from '@/stores/session-store';

const mockPush = vi.fn();
const mockReplace = vi.fn();

vi.mock('next/navigation', () => ({
  useRouter: () => ({
    push: mockPush,
    replace: mockReplace,
  }),
  usePathname: () => '/account',
}));

const mockOrdersList = vi.fn();
const mockSignOut = vi.fn();
const mockCartGet = vi.fn();

vi.mock('@/lib/api/browser', () => ({
  browserApi: {
    orders: {
      list: (...args: unknown[]) => mockOrdersList(...args),
    },
    auth: {
      signOut: (...args: unknown[]) => mockSignOut(...args),
    },
    cart: {
      get: (...args: unknown[]) => mockCartGet(...args),
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

const page1Orders: OrderList = {
  items: [
    {
      number: 'AUR-100142',
      status: 'processing',
      placedAt: '2026-11-20T14:30:00Z',
      itemCount: 1,
      total: { amount: 145000, currency: 'BDT' },
      previewImages: [],
    },
    {
      number: 'AUR-100128',
      status: 'delivered',
      placedAt: '2026-11-10T11:00:00Z',
      itemCount: 2,
      total: { amount: 280000, currency: 'BDT' },
      previewImages: [],
    },
    {
      number: 'AUR-100115',
      status: 'cancelled',
      placedAt: '2026-10-25T09:15:00Z',
      itemCount: 1,
      total: { amount: 95000, currency: 'BDT' },
      previewImages: [],
    },
  ],
  page: 1,
  pageSize: 3,
  totalItems: 4,
  totalPages: 2,
};

const page2Orders: OrderList = {
  items: [
    {
      number: 'AUR-100101',
      status: 'placed',
      placedAt: '2026-10-01T10:00:00Z',
      itemCount: 1,
      total: { amount: 80000, currency: 'BDT' },
      previewImages: [],
    },
  ],
  page: 2,
  pageSize: 3,
  totalItems: 4,
  totalPages: 2,
};

describe('SF-29 Account page and order history', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    useSessionStore.setState({ ...initialSessionState });
    mockOrdersList.mockResolvedValue(page1Orders);
    mockSignOut.mockResolvedValue(undefined);
    mockCartGet.mockResolvedValue({
      id: 'cart_01',
      items: [],
      subtotal: { amount: 0, currency: 'BDT' },
      itemCount: 0,
    });
  });

  it('redirects guest users to sign-in page with next parameter', () => {
    useSessionStore.setState({ status: 'guest', user: null });

    render(
      <AccountGuard>
        <div>Protected Content</div>
      </AccountGuard>,
    );

    expect(mockReplace).toHaveBeenCalledWith('/account/sign-in?next=%2Faccount');
    expect(screen.queryByText('Protected Content')).not.toBeInTheDocument();
  });

  it('renders account view with profile and orders for signed-in user', async () => {
    useSessionStore.setState({ status: 'signed-in', user: mockCustomer });

    render(
      <AccountGuard>
        <AccountView />
      </AccountGuard>,
    );

    expect(screen.getByRole('heading', { level: 1 })).toHaveTextContent('Hello, Nadia');
    expect(screen.getByText('Member since March 2026')).toBeInTheDocument();
    expect(screen.getByRole('heading', { level: 2, name: 'Your orders' })).toBeInTheDocument();

    await waitFor(() => {
      expect(
        screen.getByRole('link', { name: /Order AUR-100142, Processing/ }),
      ).toBeInTheDocument();
    });

    expect(screen.getByText('20 Nov 2026')).toBeInTheDocument();
  });

  it('loads more orders when clicking Load more and hides button on last page', async () => {
    useSessionStore.setState({ status: 'signed-in', user: mockCustomer });
    const user = userEvent.setup();

    render(<AccountView />);

    await waitFor(() => {
      expect(screen.getByRole('button', { name: 'Load more' })).toBeInTheDocument();
    });

    mockOrdersList.mockResolvedValueOnce(page2Orders);
    await user.click(screen.getByRole('button', { name: 'Load more' }));

    await waitFor(() => {
      expect(mockOrdersList).toHaveBeenCalledWith({ page: 2 });
    });

    expect(screen.getAllByRole('listitem')).toHaveLength(4);
    expect(screen.queryByRole('button', { name: 'Load more' })).not.toBeInTheDocument();
  });

  it('displays empty state when user has no orders', async () => {
    useSessionStore.setState({ status: 'signed-in', user: mockCustomer });
    mockOrdersList.mockResolvedValueOnce({
      items: [],
      page: 1,
      pageSize: 10,
      totalItems: 0,
      totalPages: 1,
    });

    render(<AccountView />);

    await waitFor(() => {
      expect(screen.getByText('No orders yet.')).toBeInTheDocument();
    });

    expect(screen.getByRole('link', { name: 'Start shopping' })).toHaveAttribute('href', '/shop');
  });

  it('handles sign out by calling auth.signOut and redirecting to home', async () => {
    useSessionStore.setState({ status: 'signed-in', user: mockCustomer });
    const user = userEvent.setup();

    render(<AccountView />);

    const signOutBtn = screen.getByRole('button', { name: 'Sign out' });
    await user.click(signOutBtn);

    await waitFor(() => {
      expect(mockSignOut).toHaveBeenCalled();
      expect(mockPush).toHaveBeenCalledWith('/');
    });
  });

  it('renders StatusBadge correctly', () => {
    render(<StatusBadge status="delivered" />);
    expect(screen.getByText('Delivered')).toBeInTheDocument();
  });
});
