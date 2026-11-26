import React from 'react';
import { render, screen, act } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { ApiError } from '@/lib/api/errors';
import type { Cart, Customer } from '@/lib/api/types';
import { useCartStore, initialCartState } from '@/stores/cart-store';
import { useSessionStore, initialSessionState } from '@/stores/session-store';
import { useAnnounceStore, initialAnnounceState, announce } from '@/stores/announce-store';
import { useUiStore, initialUiState } from '@/stores/ui-store';
import Announcer from '@/components/providers/Announcer';
import CartHydrator from '@/components/providers/CartHydrator';
import SessionHydrator from '@/components/providers/SessionHydrator';

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

const mockCartGet = vi.fn();
const mockCartAddItem = vi.fn();
const mockCartUpdateLine = vi.fn();
const mockCartRemoveLine = vi.fn();

const mockAuthMe = vi.fn();
const mockAuthSignIn = vi.fn();
const mockAuthRegister = vi.fn();
const mockAuthSignOut = vi.fn();

vi.mock('@/lib/api/browser', () => ({
  browserApi: {
    cart: {
      get: () => mockCartGet(),
      addItem: (input: unknown) => mockCartAddItem(input),
      updateLine: (lineId: string, quantity: number) => mockCartUpdateLine(lineId, quantity),
      removeLine: (lineId: string) => mockCartRemoveLine(lineId),
    },
    auth: {
      me: () => mockAuthMe(),
      signIn: (input: unknown) => mockAuthSignIn(input),
      register: (input: unknown) => mockAuthRegister(input),
      signOut: () => mockAuthSignOut(),
    },
  },
}));

describe('SF-10 Client Stores and Hydrators', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    useCartStore.setState(initialCartState);
    useSessionStore.setState(initialSessionState);
    useAnnounceStore.setState(initialAnnounceState);
    useUiStore.setState(initialUiState);

    mockCartGet.mockResolvedValue(sampleCart);
  });

  describe('useAnnounceStore & Announcer', () => {
    it('sets message and increments nonce on announce', () => {
      announce('First message');
      expect(useAnnounceStore.getState().message).toBe('First message');
      expect(useAnnounceStore.getState().nonce).toBe(1);

      announce('First message');
      expect(useAnnounceStore.getState().message).toBe('First message');
      expect(useAnnounceStore.getState().nonce).toBe(2);
    });

    it('renders Announcer with aria-live polite and updates on announce', () => {
      render(<Announcer />);
      const liveRegion = screen.getByTestId('announcer');
      expect(liveRegion).toHaveAttribute('aria-live', 'polite');
      expect(liveRegion).toHaveAttribute('aria-atomic', 'true');

      act(() => {
        announce('Hello screen reader');
      });

      expect(liveRegion).toHaveTextContent('Hello screen reader');
    });
  });

  describe('useUiStore', () => {
    it('updates searchOpen and mobileNavOpen', () => {
      const store = useUiStore.getState();
      expect(store.searchOpen).toBe(false);
      expect(store.mobileNavOpen).toBe(false);

      act(() => {
        store.setSearchOpen(true);
      });
      expect(useUiStore.getState().searchOpen).toBe(true);

      act(() => {
        store.setMobileNavOpen(true);
      });
      expect(useUiStore.getState().mobileNavOpen).toBe(true);
    });
  });

  describe('useCartStore', () => {
    it('hydrates cart successfully', async () => {
      mockCartGet.mockResolvedValueOnce(sampleCart);

      await act(async () => {
        await useCartStore.getState().hydrate();
      });

      const state = useCartStore.getState();
      expect(state.status).toBe('ready');
      expect(state.cart?.itemCount).toBe(2);
      expect(state.error).toBeNull();
    });

    it('sets status to error on hydrate failure', async () => {
      mockCartGet.mockRejectedValueOnce(new ApiError(500, 'INTERNAL', 'Failed to fetch'));

      await act(async () => {
        await useCartStore.getState().hydrate();
      });

      const state = useCartStore.getState();
      expect(state.status).toBe('error');
      expect(state.error).toBe('Something went wrong on our side. Please try again.');
    });

    it('adds item successfully (non-optimistic) and announces', async () => {
      const updatedCart = {
        ...sampleCart,
        itemCount: 3,
      };
      mockCartAddItem.mockResolvedValueOnce(updatedCart);

      let result: { ok: boolean } = { ok: false };
      await act(async () => {
        result = await useCartStore.getState().addItem({
          variantId: 'var_mug_sand',
          quantity: 1,
          name: 'Ondo Stoneware Mug',
        });
      });

      expect(result.ok).toBe(true);
      expect(useCartStore.getState().cart?.itemCount).toBe(3);
      expect(useAnnounceStore.getState().message).toBe('Added Ondo Stoneware Mug to cart');
    });

    it('returns ok: false on addItem failure without changing cart', async () => {
      useCartStore.setState({ ...initialCartState, cart: sampleCart, status: 'ready' });
      mockCartAddItem.mockRejectedValueOnce(new ApiError(409, 'OUT_OF_STOCK', 'Stock exceeded'));

      let result: { ok: boolean; error?: unknown } = { ok: true };
      await act(async () => {
        result = await useCartStore.getState().addItem({
          variantId: 'var_mug_sand',
          quantity: 1,
          name: 'Ondo Stoneware Mug',
        });
      });

      expect(result.ok).toBe(false);
      expect(useCartStore.getState().cart?.itemCount).toBe(2);
    });

    it('updates quantity optimistically, handles server response, and clears pendingLineIds', async () => {
      useCartStore.setState({ ...initialCartState, cart: sampleCart, status: 'ready' });

      let resolveApi!: (val: Cart) => void;
      const apiPromise = new Promise<Cart>((resolve) => {
        resolveApi = resolve;
      });
      mockCartUpdateLine.mockReturnValueOnce(apiPromise);

      const updatePromise = act(async () => {
        await useCartStore.getState().updateQuantity('line_01', 5);
      });

      // Optimistic check before API resolves:
      expect(useCartStore.getState().cart?.lines[0].quantity).toBe(5);
      expect(useCartStore.getState().pendingLineIds).toContain('line_01');

      // Resolve server API
      const serverCart = {
        ...sampleCart,
        lines: [{ ...sampleCart.lines[0], quantity: 5 }],
      };
      resolveApi(serverCart);
      await updatePromise;

      expect(useCartStore.getState().cart?.lines[0].quantity).toBe(5);
      expect(useCartStore.getState().pendingLineIds).not.toContain('line_01');
      expect(useAnnounceStore.getState().message).toBe('Cart updated');
    });

    it('rolls back quantity on error and announces error message', async () => {
      useCartStore.setState({ ...initialCartState, cart: sampleCart, status: 'ready' });
      mockCartUpdateLine.mockRejectedValueOnce(new ApiError(500, 'INTERNAL', 'Internal error'));

      await act(async () => {
        await useCartStore.getState().updateQuantity('line_01', 5);
      });

      expect(useCartStore.getState().cart?.lines[0].quantity).toBe(2);
      expect(useCartStore.getState().pendingLineIds).toEqual([]);
      expect(useAnnounceStore.getState().message).toBe(
        'Something went wrong on our side. Please try again.',
      );
    });

    it('handles INSUFFICIENT_STOCK by updating line to available quantity', async () => {
      useCartStore.setState({ ...initialCartState, cart: sampleCart, status: 'ready' });
      mockCartUpdateLine
        .mockRejectedValueOnce(
          new ApiError(409, 'INSUFFICIENT_STOCK', 'Stock exceeded', null, { available: 3 }),
        )
        .mockResolvedValueOnce({
          ...sampleCart,
          lines: [{ ...sampleCart.lines[0], quantity: 3 }],
        });

      await act(async () => {
        await useCartStore.getState().updateQuantity('line_01', 5);
      });

      expect(mockCartUpdateLine).toHaveBeenCalledTimes(2);
      expect(mockCartUpdateLine).toHaveBeenNthCalledWith(1, 'line_01', 5);
      expect(mockCartUpdateLine).toHaveBeenNthCalledWith(2, 'line_01', 3);
      expect(useAnnounceStore.getState().message).toBe("Only 3 left — we've updated the quantity.");
    });

    it('removes line optimistically and restores on failure', async () => {
      useCartStore.setState({ ...initialCartState, cart: sampleCart, status: 'ready' });

      let rejectApi!: (err: unknown) => void;
      const apiPromise = new Promise<Cart>((_, reject) => {
        rejectApi = reject;
      });
      mockCartRemoveLine.mockReturnValueOnce(apiPromise);

      const removePromise = act(async () => {
        await useCartStore.getState().removeLine('line_01');
      });

      // Optimistically removed
      expect(useCartStore.getState().cart?.lines.length).toBe(0);

      // Rejection triggers rollback
      rejectApi(new ApiError(500, 'INTERNAL', 'Failed'));
      await removePromise;

      expect(useCartStore.getState().cart?.lines.length).toBe(1);
      expect(useAnnounceStore.getState().message).toBe(
        'Something went wrong on our side. Please try again.',
      );
    });

    it('toggles drawerOpen and resets state', () => {
      useCartStore.getState().openDrawer();
      expect(useCartStore.getState().drawerOpen).toBe(true);

      useCartStore.getState().closeDrawer();
      expect(useCartStore.getState().drawerOpen).toBe(false);

      useCartStore.setState({ ...initialCartState, cart: sampleCart, drawerOpen: true });
      useCartStore.getState().reset();
      expect(useCartStore.getState().cart).toBeNull();
      expect(useCartStore.getState().status).toBe('idle');
      expect(useCartStore.getState().drawerOpen).toBe(false);
    });
  });

  describe('useSessionStore', () => {
    it('sets status to guest on 401 unauthenticated', async () => {
      mockAuthMe.mockRejectedValueOnce(new ApiError(401, 'UNAUTHENTICATED', 'No session'));

      await act(async () => {
        await useSessionStore.getState().hydrate();
      });

      expect(useSessionStore.getState().status).toBe('guest');
      expect(useSessionStore.getState().user).toBeNull();
    });

    it('sets user and signed-in status on signIn and rehydrates cart', async () => {
      mockAuthSignIn.mockResolvedValueOnce(sampleCustomer);
      mockCartGet.mockResolvedValueOnce(sampleCart);

      await act(async () => {
        const user = await useSessionStore.getState().signIn({
          email: 'nadia@example.com',
          password: 'password123',
        });
        expect(user.email).toBe('nadia@example.com');
      });

      expect(useSessionStore.getState().status).toBe('signed-in');
      expect(useSessionStore.getState().user).toEqual(sampleCustomer);
      expect(mockCartGet).toHaveBeenCalled();
      expect(useAnnounceStore.getState().message).toBe('Signed in');
    });

    it('registers user, rehydrates cart, and announces Account created', async () => {
      mockAuthRegister.mockResolvedValueOnce(sampleCustomer);
      mockCartGet.mockResolvedValueOnce(sampleCart);

      await act(async () => {
        const user = await useSessionStore.getState().register({
          email: 'nadia@example.com',
          password: 'password123',
          firstName: 'Nadia',
          lastName: 'Rahman',
        });
        expect(user.id).toBe('cust_01');
      });

      expect(useSessionStore.getState().status).toBe('signed-in');
      expect(useAnnounceStore.getState().message).toBe('Account created');
    });

    it('signs out, resets and rehydrates cart, and sets guest status', async () => {
      useSessionStore.setState({ user: sampleCustomer, status: 'signed-in' });
      mockAuthSignOut.mockResolvedValueOnce(undefined);
      mockCartGet.mockResolvedValueOnce({ ...sampleCart, itemCount: 0, lines: [] });

      await act(async () => {
        await useSessionStore.getState().signOut();
      });

      expect(useSessionStore.getState().status).toBe('guest');
      expect(useSessionStore.getState().user).toBeNull();
      expect(useAnnounceStore.getState().message).toBe('Signed out');
    });
  });

  describe('Hydrator components', () => {
    it('runs hydrate on CartHydrator and SessionHydrator mount', async () => {
      mockCartGet.mockResolvedValueOnce(sampleCart);
      mockAuthMe.mockResolvedValueOnce(sampleCustomer);

      render(
        <>
          <CartHydrator />
          <SessionHydrator />
        </>,
      );

      await act(async () => {
        await Promise.resolve();
      });

      expect(mockCartGet).toHaveBeenCalled();
      expect(mockAuthMe).toHaveBeenCalled();
    });
  });
});
