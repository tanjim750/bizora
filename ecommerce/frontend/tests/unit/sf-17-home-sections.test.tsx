import React from 'react';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import homeFixture from '@/mocks/fixtures/home.json';
import productsFixture from '@/mocks/fixtures/products.json';
import { toSummary } from '@/mocks/server/catalog';
import FeaturedRail from '@/components/home/FeaturedRail';
import EditorialBand from '@/components/home/EditorialBand';
import ValueStrip from '@/components/home/ValueStrip';
import Newsletter from '@/components/home/Newsletter';
import { browserApi } from '@/lib/api/browser';
import { ApiError } from '@/lib/api/errors';
import type { HomeContent, Product } from '@/lib/api/types';

vi.mock('@/lib/motion/gsap', () => ({
  useGSAP: () => {},
  gsap: {
    matchMedia: () => ({
      add: () => {},
    }),
    timeline: () => ({
      from: () => {},
      fromTo: () => {},
      to: () => {},
    }),
    from: () => {},
    fromTo: () => {},
    to: () => {},
  },
  SplitText: {
    create: () => ({
      lines: [],
      revert: () => {},
    }),
  },
  ScrollTrigger: {},
}));

vi.mock('@/lib/api/browser', () => ({
  browserApi: {
    newsletter: {
      subscribe: vi.fn(),
    },
  },
}));

const home = homeFixture as unknown as HomeContent;
const allProducts = ((productsFixture as { items?: Product[] }).items ??
  productsFixture) as Product[];
const featuredProducts = allProducts.slice(0, 8).map(toSummary);

describe('SF-17 Home page sections', () => {
  it('renders FeaturedRail with 8 products and Shop all link', () => {
    render(<FeaturedRail products={featuredProducts} />);

    expect(screen.getByRole('heading', { name: 'Most loved' })).toBeInTheDocument();
    const shopAllLink = screen.getByRole('link', { name: /shop all/i });
    expect(shopAllLink).toHaveAttribute('href', '/shop?collection=featured');

    const cardLinks = screen.getAllByRole('link');
    // 1 header link ("Shop all") + 8 product cards = 9 links
    expect(cardLinks).toHaveLength(9);
  });

  it('renders EditorialBand with headline and CTA link', () => {
    render(<EditorialBand editorial={home.editorial} />);

    expect(
      screen.getByRole('heading', { name: 'Every Ondo mug starts as 400 grams of clay' }),
    ).toBeInTheDocument();

    const ctaLink = screen.getByRole('link', { name: /shop ceramics/i });
    expect(ctaLink).toHaveAttribute('href', '/shop?category=ceramics');
  });

  it('renders ValueStrip with 4 values and Cash on delivery', () => {
    render(<ValueStrip values={home.values} />);

    const items = screen.getAllByRole('listitem');
    expect(items).toHaveLength(4);
    expect(screen.getByText('Cash on delivery')).toBeInTheDocument();
  });

  describe('Newsletter component', () => {
    it('validates empty and invalid email on client', async () => {
      render(<Newsletter variant="band" />);

      const submitButton = screen.getByRole('button', { name: /subscribe/i });
      fireEvent.click(submitButton);

      expect(screen.getByText('Enter your email address.')).toBeInTheDocument();

      const input = screen.getByLabelText(/email address/i);
      fireEvent.change(input, { target: { value: 'a@b' } });
      fireEvent.click(submitButton);

      expect(screen.getByText('Enter a valid email address.')).toBeInTheDocument();
    });

    it('subscribes with valid email and shows success message', async () => {
      const subscribeMock = vi.mocked(browserApi.newsletter.subscribe);
      subscribeMock.mockResolvedValueOnce({
        status: 'subscribed',
      });

      render(<Newsletter variant="band" />);

      const input = screen.getByLabelText(/email address/i);
      fireEvent.change(input, { target: { value: 'reader@example.com' } });

      const submitButton = screen.getByRole('button', { name: /subscribe/i });
      fireEvent.click(submitButton);

      await waitFor(() => {
        expect(subscribeMock).toHaveBeenCalledWith('reader@example.com');
        const status = screen.getByRole('status');
        expect(status).toHaveTextContent("Thanks — you're on the list.");
      });
    });

    it('handles ApiError VALIDATION_FAILED with field error', async () => {
      const subscribeMock = vi.mocked(browserApi.newsletter.subscribe);
      subscribeMock.mockRejectedValueOnce(
        new ApiError(400, 'VALIDATION_FAILED', 'Validation failed', {
          email: ['Enter a valid email address.'],
        }),
      );

      render(<Newsletter variant="footer" />);

      const input = screen.getByLabelText(/email address/i);
      fireEvent.change(input, { target: { value: 'invalid@example.com' } });

      const submitButton = screen.getByRole('button', { name: /subscribe/i });
      fireEvent.click(submitButton);

      await waitFor(() => {
        expect(screen.getByText('Enter a valid email address.')).toBeInTheDocument();
      });
    });
  });
});
