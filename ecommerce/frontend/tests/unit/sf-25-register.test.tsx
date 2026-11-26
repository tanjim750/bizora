import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import RegisterPage, { metadata } from '@/app/(store)/account/register/page';
import { ApiError } from '@/lib/api/errors';
import { useSessionStore, initialSessionState } from '@/stores/session-store';
import { useCartStore, initialCartState } from '@/stores/cart-store';

const mockReplace = vi.fn();
const mockRegister = vi.fn();
const mockMe = vi.fn();
const mockCartGet = vi.fn();

vi.mock('next/navigation', () => ({
  useRouter: () => ({ replace: mockReplace, push: vi.fn() }),
  useSearchParams: () => new URLSearchParams(),
}));

vi.mock('@/lib/api/browser', () => ({
  browserApi: {
    auth: {
      register: (args: any) => mockRegister(args),
      me: () => mockMe(),
    },
    cart: {
      get: () => mockCartGet(),
    },
  },
}));

describe('SF-25 Registration page', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    useSessionStore.setState(initialSessionState);
    useCartStore.setState(initialCartState);
  });

  it('has metadata title Create your account', () => {
    expect(metadata.title).toBe('Create your account');
  });

  it('renders register form with inputs and hint', () => {
    render(<RegisterPage />);

    expect(
      screen.getByRole('heading', { level: 1, name: 'Create your account' }),
    ).toBeInTheDocument();
    expect(screen.getByLabelText('First name')).toBeInTheDocument();
    expect(screen.getByLabelText('Last name')).toBeInTheDocument();
    expect(screen.getByLabelText('Email')).toBeInTheDocument();
    expect(screen.getByLabelText('Password')).toBeInTheDocument();
    expect(screen.getByText('At least 8 characters.')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Create account' })).toBeInTheDocument();
    expect(
      screen.getByRole('link', { name: 'Sign in' }),
    ).toHaveAttribute('href', '/account/sign-in');
  });

  it('validates short password without calling auth.register', () => {
    render(<RegisterPage />);

    fireEvent.change(screen.getByLabelText('First name'), {
      target: { value: 'Jane' },
    });
    fireEvent.change(screen.getByLabelText('Last name'), {
      target: { value: 'Doe' },
    });
    fireEvent.change(screen.getByLabelText('Email'), {
      target: { value: 'jane@example.com' },
    });
    fireEvent.change(screen.getByLabelText('Password'), {
      target: { value: 'short' },
    });

    fireEvent.click(screen.getByRole('button', { name: 'Create account' }));

    expect(screen.getByText('Use at least 8 characters.')).toBeInTheDocument();
    expect(mockRegister).not.toHaveBeenCalled();
  });

  it('submits valid values and calls auth.register and replace(/account)', async () => {
    mockRegister.mockResolvedValueOnce({
      id: 'cust_2',
      email: 'jane@example.com',
      firstName: 'Jane',
      lastName: 'Doe',
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

    render(<RegisterPage />);

    fireEvent.change(screen.getByLabelText('First name'), {
      target: { value: 'Jane' },
    });
    fireEvent.change(screen.getByLabelText('Last name'), {
      target: { value: 'Doe' },
    });
    fireEvent.change(screen.getByLabelText('Email'), {
      target: { value: 'jane@example.com' },
    });
    fireEvent.change(screen.getByLabelText('Password'), {
      target: { value: 'long-secure-password' },
    });

    fireEvent.click(screen.getByRole('button', { name: 'Create account' }));

    await waitFor(() => {
      expect(mockRegister).toHaveBeenCalledWith({
        firstName: 'Jane',
        lastName: 'Doe',
        email: 'jane@example.com',
        password: 'long-secure-password',
      });
      expect(mockReplace).toHaveBeenCalledWith('/account');
    });
  });

  it('handles EMAIL_TAKEN by showing error message and sign in instead link', async () => {
    mockRegister.mockRejectedValueOnce(
      new ApiError(409, 'EMAIL_TAKEN', 'x', {
        email: ['An account with this email already exists.'],
      }),
    );

    render(<RegisterPage />);

    fireEvent.change(screen.getByLabelText('First name'), {
      target: { value: 'Jane' },
    });
    fireEvent.change(screen.getByLabelText('Last name'), {
      target: { value: 'Doe' },
    });
    fireEvent.change(screen.getByLabelText('Email'), {
      target: { value: 'taken@example.com' },
    });
    fireEvent.change(screen.getByLabelText('Password'), {
      target: { value: 'password-123' },
    });

    fireEvent.click(screen.getByRole('button', { name: 'Create account' }));

    await waitFor(() => {
      expect(
        screen.getByText('An account with this email already exists.'),
      ).toBeInTheDocument();
      const signInLink = screen.getByRole('link', { name: 'Sign in instead' });
      expect(signInLink).toHaveAttribute('href', '/account/sign-in');
    });
  });
});
