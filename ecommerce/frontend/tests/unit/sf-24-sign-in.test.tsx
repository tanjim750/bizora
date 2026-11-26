import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import AuthForm from '@/components/account/AuthForm';
import { safeNextPath } from '@/lib/auth/redirect';
import { validateSignIn, validateRegister } from '@/lib/auth/validation';
import { ApiError } from '@/lib/api/errors';
import { useSessionStore, initialSessionState } from '@/stores/session-store';
import { useCartStore, initialCartState } from '@/stores/cart-store';

const mockReplace = vi.fn();
const mockSignIn = vi.fn();
const mockMe = vi.fn();
const mockCartGet = vi.fn();

vi.mock('next/navigation', () => ({
  useRouter: () => ({ replace: mockReplace, push: vi.fn() }),
  useSearchParams: () => new URLSearchParams('next=/checkout'),
}));

vi.mock('@/lib/api/browser', () => ({
  browserApi: {
    auth: {
      signIn: (args: any) => mockSignIn(args),
      me: () => mockMe(),
    },
    cart: {
      get: () => mockCartGet(),
    },
  },
}));

describe('SF-24 Auth validation, safe redirect and sign-in page', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    useSessionStore.setState(initialSessionState);
    useCartStore.setState(initialCartState);
  });

  describe('safeNextPath', () => {
    it('handles valid and invalid paths correctly', () => {
      expect(safeNextPath('/checkout')).toBe('/checkout');
      expect(safeNextPath('//evil.com')).toBe('/account');
      expect(safeNextPath('https://evil.com')).toBe('/account');
      expect(safeNextPath('/\\evil')).toBe('/account');
      expect(safeNextPath('javascript:alert(1)')).toBe('/account');
      expect(safeNextPath('')).toBe('/account');
      expect(safeNextPath(null)).toBe('/account');
      expect(safeNextPath('/account/sign-in')).toBe('/account');
      expect(safeNextPath(undefined, '/x')).toBe('/x');
    });
  });

  describe('Validation', () => {
    it('validates sign in values', () => {
      const res = validateSignIn({ email: '', password: '' });
      expect(res.ok).toBe(false);
      if (!res.ok) {
        expect(res.errors).toEqual({
          email: 'Enter your email address.',
          password: 'Enter your password.',
        });
      }
    });

    it('validates register values', () => {
      const res = validateRegister({
        firstName: 'A',
        lastName: 'B',
        email: 'a@b.co',
        password: 'short',
      });
      expect(res.ok).toBe(false);
      if (!res.ok) {
        expect(res.errors.password).toBe('Use at least 8 characters.');
      }
    });
  });

  describe('AuthForm component', () => {
    it('validates empty inputs and focuses email input on submit', () => {
      render(<AuthForm mode="sign-in" />);

      fireEvent.click(screen.getByRole('button', { name: 'Sign in' }));

      expect(screen.getByText('Enter your email address.')).toBeInTheDocument();
      expect(screen.getByText('Enter your password.')).toBeInTheDocument();

      const emailInput = screen.getByLabelText('Email');
      expect(document.activeElement).toBe(emailInput);
    });

    it('submits valid credentials and calls router.replace with safe next path', async () => {
      mockSignIn.mockResolvedValueOnce({
        id: 'cust_1',
        email: 'demo@aurelo.test',
        firstName: 'Demo',
        lastName: 'User',
        createdAt: '2026-11-26T00:00:00Z',
      });
      mockCartGet.mockResolvedValueOnce({
        id: 'cart_1',
        lines: [],
        itemCount: 0,
        subtotal: { amount: 0, currency: 'BDT' },
        freeShippingRemaining: null,
        updatedAt: null,
      });

      render(<AuthForm mode="sign-in" />);

      fireEvent.change(screen.getByLabelText('Email'), {
        target: { value: 'demo@aurelo.test' },
      });
      fireEvent.change(screen.getByLabelText('Password'), {
        target: { value: 'demo-pass-123' },
      });

      fireEvent.click(screen.getByRole('button', { name: 'Sign in' }));

      await waitFor(() => {
        expect(mockSignIn).toHaveBeenCalledWith({
          email: 'demo@aurelo.test',
          password: 'demo-pass-123',
        });
        expect(mockReplace).toHaveBeenCalledWith('/checkout');
      });
    });

    it('displays alert on INVALID_CREDENTIALS error', async () => {
      mockSignIn.mockRejectedValueOnce(
        new ApiError(401, 'INVALID_CREDENTIALS', 'Invalid credentials'),
      );

      render(<AuthForm mode="sign-in" />);

      fireEvent.change(screen.getByLabelText('Email'), {
        target: { value: 'demo@aurelo.test' },
      });
      fireEvent.change(screen.getByLabelText('Password'), {
        target: { value: 'wrong-pass' },
      });

      fireEvent.click(screen.getByRole('button', { name: 'Sign in' }));

      await waitFor(() => {
        expect(
          screen.getByText("That email and password don't match."),
        ).toBeInTheDocument();
      });
    });

    it('toggles password visibility with IconButton', () => {
      render(<AuthForm mode="sign-in" />);

      const passwordInput = screen.getByLabelText('Password');
      expect(passwordInput).toHaveAttribute('type', 'password');

      const toggleButton = screen.getByRole('button', { name: 'Show password' });
      fireEvent.click(toggleButton);

      expect(passwordInput).toHaveAttribute('type', 'text');
      expect(screen.getByRole('button', { name: 'Hide password' })).toBeInTheDocument();
    });

    it('renders link to register keeping next query parameter', () => {
      render(<AuthForm mode="sign-in" />);

      const createAccountLink = screen.getByRole('link', {
        name: 'Create an account',
      });
      expect(createAccountLink).toHaveAttribute(
        'href',
        '/account/register?next=%2Fcheckout',
      );
    });
  });
});
