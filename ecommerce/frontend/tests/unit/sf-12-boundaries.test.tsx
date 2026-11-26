import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import NotFound from '@/app/not-found';
import ErrorPage from '@/app/error';
import Template from '@/app/(store)/template';
import Loading from '@/app/(store)/loading';

vi.mock('next/link', () => ({
  default: ({
    href,
    children,
    ...props
  }: {
    href: string;
    children: React.ReactNode;
    [key: string]: unknown;
  }) => (
    <a href={href} {...props}>
      {children}
    </a>
  ),
}));

describe('SF-12 Boundaries, 404, Error and Page Transition', () => {
  it('renders NotFound with page title, copy, and navigation links', () => {
    render(<NotFound />);

    expect(screen.getByRole('main')).toHaveAttribute('id', 'main');
    expect(screen.getByRole('heading', { level: 1, name: 'Page not found' })).toBeInTheDocument();
    expect(
      screen.getByText("The page you're looking for has moved or never existed."),
    ).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'Go home' })).toHaveAttribute('href', '/');
    expect(screen.getByRole('link', { name: 'Browse the shop' })).toHaveAttribute('href', '/shop');
  });

  it('renders ErrorPage and triggers reset when Try again is clicked', () => {
    const reset = vi.fn();
    render(<ErrorPage error={new Error('Test failure')} reset={reset} />);

    expect(screen.getByRole('main')).toHaveAttribute('id', 'main');
    expect(
      screen.getByRole('heading', { level: 1, name: 'Something went wrong' }),
    ).toBeInTheDocument();
    expect(
      screen.getByText('Something went wrong on our side. Please try again.'),
    ).toBeInTheDocument();

    const tryAgainBtn = screen.getByRole('button', { name: 'Try again' });
    fireEvent.click(tryAgainBtn);
    expect(reset).toHaveBeenCalledTimes(1);

    expect(screen.getByRole('link', { name: 'Go home' })).toHaveAttribute('href', '/');
  });

  it('renders Template and mounts children, focusing #main after first load', () => {
    const main = document.createElement('main');
    main.id = 'main';
    main.tabIndex = -1;
    document.body.appendChild(main);
    const focusSpy = vi.spyOn(main, 'focus');

    // First load should not focus #main
    const { unmount } = render(
      <Template>
        <p>Child</p>
      </Template>,
    );
    expect(screen.getByText('Child')).toBeInTheDocument();
    expect(focusSpy).not.toHaveBeenCalled();
    unmount();

    // Subsequent navigation should focus #main without scrolling
    render(
      <Template>
        <p>Next Child</p>
      </Template>,
    );
    expect(screen.getByText('Next Child')).toBeInTheDocument();
    expect(focusSpy).toHaveBeenCalledWith({ preventScroll: true });

    main.remove();
  });

  it('renders Loading skeleton with aria-busy="true" and loading text', () => {
    const { container } = render(<Loading />);

    const busyElement = container.querySelector('[aria-busy="true"]');
    expect(busyElement).toBeInTheDocument();
    expect(screen.getByText('Loading…')).toBeInTheDocument();
  });
});
