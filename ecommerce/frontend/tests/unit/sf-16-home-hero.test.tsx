import React from 'react';
import { render, screen, within } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import homeFixture from '@/mocks/fixtures/home.json';
import categoriesFixture from '@/mocks/fixtures/categories.json';
import Hero from '@/components/home/Hero';
import CategoryTiles from '@/components/home/CategoryTiles';
import { pick } from '@/components/home/pick-categories';
import type { Category, HomeContent } from '@/lib/api/types';

vi.mock('@/lib/motion/gsap', () => ({
  useGSAP: () => {},
  gsap: {
    matchMedia: () => ({
      add: () => {},
    }),
    timeline: () => ({
      from: () => {},
    }),
    from: () => {},
  },
  SplitText: {
    create: () => ({
      lines: [],
      revert: () => {},
    }),
  },
  ScrollTrigger: {},
}));

const home = homeFixture as unknown as HomeContent;
const categories = ((categoriesFixture as { items?: Category[] }).items ??
  categoriesFixture) as Category[];

describe('SF-16 Home hero and category tiles', () => {
  it('pick keeps slug order and skips unknown slugs', () => {
    const picked = pick(['ceramics', 'nope', 'bags'], categories);
    expect(picked.map((c) => c.slug)).toEqual(['ceramics', 'bags']);
  });

  it('renders Hero with heading level 1, CTA link and image with alt', () => {
    render(<Hero hero={home.hero} />);

    const heading = screen.getByRole('heading', { level: 1 });
    expect(heading).toHaveTextContent('Made slowly. Kept for years.');

    const ctaLink = screen.getByRole('link', { name: /shop the collection/i });
    expect(ctaLink).toHaveAttribute('href', '/shop');

    const image = screen.getByAltText(
      'Stoneware mugs and a linen throw on an oak table in morning light',
    );
    expect(image).toBeInTheDocument();
  });

  it('renders CategoryTiles with 4 featured categories and product count', () => {
    const featured = pick(home.featuredCategorySlugs, categories);
    render(<CategoryTiles categories={featured} />);

    const heading = screen.getByRole('heading', { level: 2 });
    expect(heading).toHaveTextContent('Shop by category');

    const links = screen.getAllByRole('link');
    expect(links).toHaveLength(4);

    expect(links[0]).toHaveAttribute('href', '/shop?category=ceramics');
    expect(within(links[0]).getByText('5 pieces')).toBeInTheDocument();
  });
});
