import { create } from 'zustand';
import { browserApi } from '@/lib/api/browser';
import { isApiError, toUserMessage, type ApiError } from '@/lib/api/errors';
import type { Cart } from '@/lib/api/types';
import { announce } from './announce-store';

export type CartState = {
  cart: Cart | null;
  status: 'idle' | 'loading' | 'ready' | 'error';
  error: string | null;
  pendingLineIds: string[];
  drawerOpen: boolean;
  hydrate: () => Promise<void>;
  addItem: (input: {
    variantId: string;
    quantity: number;
    name: string;
  }) => Promise<{ ok: true } | { ok: false; error: ApiError | Error }>;
  updateQuantity: (lineId: string, quantity: number) => Promise<void>;
  removeLine: (lineId: string) => Promise<void>;
  openDrawer: () => void;
  closeDrawer: () => void;
  reset: () => void;
};

export const initialCartState: Omit<
  CartState,
  'hydrate' | 'addItem' | 'updateQuantity' | 'removeLine' | 'openDrawer' | 'closeDrawer' | 'reset'
> = {
  cart: null,
  status: 'idle',
  error: null,
  pendingLineIds: [],
  drawerOpen: false,
};

export const useCartStore = create<CartState>((set, get) => ({
  ...initialCartState,

  hydrate: async () => {
    set({ status: 'loading', error: null });
    try {
      const cart = await browserApi.cart.get();
      set({ cart, status: 'ready', error: null });
    } catch (err) {
      set({ status: 'error', error: toUserMessage(err) });
    }
  },

  addItem: async (input) => {
    try {
      const cart = await browserApi.cart.addItem({
        variantId: input.variantId,
        quantity: input.quantity,
      });
      set({ cart, status: 'ready', error: null });
      announce(`Added ${input.name} to cart`);
      return { ok: true };
    } catch (err) {
      return {
        ok: false,
        error: err instanceof Error ? err : new Error(String(err)),
      };
    }
  },

  updateQuantity: async (lineId, quantity) => {
    const prevCart = get().cart;
    if (!prevCart) return;

    // Optimistic update
    const updatedLines = prevCart.lines.map((line) =>
      line.id === lineId ? { ...line, quantity } : line,
    );

    set((state) => ({
      cart: { ...prevCart, lines: updatedLines },
      pendingLineIds: state.pendingLineIds.includes(lineId)
        ? state.pendingLineIds
        : [...state.pendingLineIds, lineId],
    }));

    try {
      const cart = await browserApi.cart.updateLine(lineId, quantity);
      set({ cart, status: 'ready' });
      announce('Cart updated');
    } catch (err) {
      if (isApiError(err)) {
        if (err.code === 'INSUFFICIENT_STOCK') {
          const available = typeof err.details?.available === 'number' ? err.details.available : 0;
          set((state) => ({
            pendingLineIds: state.pendingLineIds.filter((id) => id !== lineId),
          }));
          if (available > 0) {
            await get().updateQuantity(lineId, available);
          } else {
            await get().removeLine(lineId);
          }
          announce(toUserMessage(err));
          return;
        }

        if (err.code === 'LINE_NOT_FOUND') {
          await get().hydrate();
          announce('Your cart was updated.');
          set((state) => ({
            pendingLineIds: state.pendingLineIds.filter((id) => id !== lineId),
          }));
          return;
        }
      }

      // Rollback on other errors
      set({ cart: prevCart });
      announce(toUserMessage(err));
    } finally {
      set((state) => ({
        pendingLineIds: state.pendingLineIds.filter((id) => id !== lineId),
      }));
    }
  },

  removeLine: async (lineId) => {
    const prevCart = get().cart;
    if (!prevCart) return;

    const removedLine = prevCart.lines.find((line) => line.id === lineId);
    const productName = removedLine ? removedLine.productName : 'item';

    // Optimistic removal
    set((state) => ({
      cart: {
        ...prevCart,
        lines: prevCart.lines.filter((line) => line.id !== lineId),
      },
      pendingLineIds: state.pendingLineIds.includes(lineId)
        ? state.pendingLineIds
        : [...state.pendingLineIds, lineId],
    }));

    try {
      const cart = await browserApi.cart.removeLine(lineId);
      set({ cart, status: 'ready' });
      announce(`Removed ${productName}`);
    } catch (err) {
      set({ cart: prevCart });
      announce(toUserMessage(err));
    } finally {
      set((state) => ({
        pendingLineIds: state.pendingLineIds.filter((id) => id !== lineId),
      }));
    }
  },

  openDrawer: () => set({ drawerOpen: true }),
  closeDrawer: () => set({ drawerOpen: false }),

  reset: () =>
    set({
      cart: null,
      status: 'idle',
      error: null,
      pendingLineIds: [],
      drawerOpen: false,
    }),
}));
