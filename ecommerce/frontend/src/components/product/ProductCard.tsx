'use client';

import * as React from 'react';
import Image from 'next/image';
import Link from 'next/link';
import { formatMoney } from '@/lib/format/money';
import { Price } from '@/components/ui/Price';
import { Badge } from '@/components/ui/Badge';
import { VisuallyHidden } from '@/components/ui/VisuallyHidden';
import type { ProductSummary } from '@/lib/api/types';
import { cn } from '@/lib/cn';

export interface ProductCardProps {
  product: ProductSummary;
  priority?: boolean;
  sizes?: string;
  className?: string;
}

export default function ProductCard({
  product,
  priority = false,
  sizes = '(min-width: 1440px) 25vw, (min-width: 1024px) 33vw, 50vw',
  className,
}: ProductCardProps) {
  const isOutOfStock = product.stockStatus === 'out_of_stock';
  const firstImage = product.images[0];
  const secondImage = product.images.length > 1 ? product.images[1] : null;

  // Ordered badges: New, Sale, Bestseller
  const orderedBadges: Array<{ label: string; variant: 'neutral' | 'accent' | 'danger' }> = [];
  if (product.badges.includes('new')) {
    orderedBadges.push({ label: 'New', variant: 'neutral' });
  }
  if (product.badges.includes('sale')) {
    orderedBadges.push({ label: 'Sale', variant: 'accent' });
  }
  if (product.badges.includes('bestseller')) {
    orderedBadges.push({ label: 'Bestseller', variant: 'neutral' });
  }
  if (isOutOfStock) {
    orderedBadges.push({ label: 'Sold out', variant: 'danger' });
  }

  // Filter swatches that represent real colors (non-null swatch hex)
  const colorSwatches = product.swatches.filter((s) => s.swatch !== null);
  const visibleSwatches = colorSwatches.slice(0, 4);
  const remainingSwatchesCount = colorSwatches.length - 4;

  return (
    <article className={cn('group relative flex flex-col', className)}>
      {/* Image Well */}
      <div
        className={cn(
          'relative aspect-4/5 w-full overflow-hidden rounded-md bg-surface-2 transition-opacity',
          isOutOfStock && 'opacity-70',
        )}
      >
        {firstImage && (
          <Image
            src={firstImage.url}
            alt={firstImage.alt || product.name}
            fill
            sizes={sizes}
            priority={priority}
            className="object-cover"
          />
        )}

        {secondImage && (
          <Image
            src={secondImage.url}
            alt=""
            fill
            sizes={sizes}
            className="object-cover opacity-0 transition-opacity duration-200 group-hover:opacity-100"
            aria-hidden="true"
          />
        )}

        {/* Badges */}
        {orderedBadges.length > 0 && (
          <div className="absolute left-3 top-3 z-10 flex flex-wrap gap-1.5">
            {orderedBadges.map((badge) => (
              <Badge key={badge.label} variant={badge.variant}>
                {badge.label}
              </Badge>
            ))}
          </div>
        )}
      </div>

      {/* Meta */}
      <div className="mt-3 space-y-1">
        <h3 className="text-body font-medium text-fg">
          <Link href={`/products/${product.slug}`} className="after:absolute after:inset-0">
            <span className="relative">
              {product.name}
              <span className="absolute inset-x-0 bottom-0 h-px bg-fg origin-left scale-x-0 group-hover:scale-x-100 transition-transform duration-200" />
            </span>
          </Link>
        </h3>

        {product.subtitle && (
          <p className="text-small text-fg-muted line-clamp-1">{product.subtitle}</p>
        )}

        <div className="pt-0.5">
          <Price
            formatted={formatMoney(product.price)}
            compareAtFormatted={product.compareAtPrice ? formatMoney(product.compareAtPrice) : null}
          />
        </div>

        {/* Color Swatches */}
        {colorSwatches.length > 0 && (
          <div className="flex items-center gap-1.5 pt-1">
            <VisuallyHidden>Colours: {colorSwatches.map((s) => s.label).join(', ')}</VisuallyHidden>
            {visibleSwatches.map((s) => (
              <span
                key={s.label}
                aria-hidden="true"
                title={s.label}
                className="size-3 rounded-pill border border-border inline-block"
                style={{ backgroundColor: s.swatch ?? undefined }}
              />
            ))}
            {remainingSwatchesCount > 0 && (
              <span aria-hidden="true" className="text-caption text-fg-muted leading-none">
                +{remainingSwatchesCount}
              </span>
            )}
          </div>
        )}
      </div>
    </article>
  );
}
