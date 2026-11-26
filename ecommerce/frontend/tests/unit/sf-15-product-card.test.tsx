import React from 'react';
import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import productsFixture from '@/mocks/fixtures/products.json';
import { toSummary } from '@/mocks/server/catalog';
import ProductCard from '@/components/product/ProductCard';
import ProductCardSkeleton from '@/components/product/ProductCardSkeleton';
import ProductGrid from '@/components/product/ProductGrid';
import type { Product } from '@/lib/api/types';

const allProducts = ((productsFixture as { items?: Product[] }).items ?? productsFixture) as Product[];
const tideDinnerPlates = toSummary(allProducts.find((p) => p.slug === 'tide-dinner-plates')!);
const emberTeapot = toSummary(allProducts.find((p) => p.slug === 'ember-teapot')!);
const wickCandleTrio = toSummary(allProducts.find((p) => p.slug === 'wick-candle-trio')!);

describe('SF-15 ProductCard, ProductGrid and Skeletons', () => {
  it('renders card for tide-dinner-plates with link, sale badge, price and color swatches', () => {
    render(<ProductCard product={tideDinnerPlates} />);

    const link = screen.getByRole('link', { name: /tide dinner plates/i });
    expect(link).toHaveAttribute('href', '/products/tide-dinner-plates');

    expect(screen.getByText('Sale')).toBeInTheDocument();
    expect(screen.getByText('Sale price ৳5,400, was ৳6,200')).toBeInTheDocument();
    expect(screen.getByText('Colours: Ash, Ink')).toBeInTheDocument();
  });

  it('renders Sold out badge for ember-teapot when out of stock', () => {
    render(<ProductCard product={emberTeapot} />);

    expect(screen.getByText('Sold out')).toBeInTheDocument();
  });

  it('does not render Colours text for products without color swatches', () => {
    render(<ProductCard product={wickCandleTrio} />);

    expect(screen.queryByText(/Colours:/i)).not.toBeInTheDocument();
  });

  it('renders ProductGrid with 6 products and listitems', () => {
    const products = allProducts.slice(0, 6).map(toSummary);
    render(<ProductGrid products={products} />);

    const listItems = screen.getAllByRole('listitem');
    expect(listItems).toHaveLength(6);

    const links = screen.getAllByRole('link');
    expect(links).toHaveLength(6);
  });

  it('renders ProductCardSkeleton with aria-hidden="true"', () => {
    const { container } = render(<ProductCardSkeleton />);
    const skeletonElement = container.querySelector('[aria-hidden="true"]');
    expect(skeletonElement).toBeInTheDocument();
  });
});
