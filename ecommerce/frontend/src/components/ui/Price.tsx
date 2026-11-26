import * as React from 'react';
import { cn } from '@/lib/cn';

export interface PriceProps {
  formatted: string;
  compareAtFormatted?: string | null;
  size?: 'sm' | 'md' | 'lg';
  className?: string;
}

export function Price({ formatted, compareAtFormatted, size = 'md', className }: PriceProps) {
  const sizeClasses = {
    sm: 'text-small',
    md: 'text-body',
    lg: 'text-title',
  }[size];

  if (!compareAtFormatted) {
    return (
      <span className={cn('tabular-nums font-medium text-fg', sizeClasses, className)}>
        {formatted}
      </span>
    );
  }

  return (
    <span
      className={cn(
        'tabular-nums font-medium inline-flex items-center gap-2',
        sizeClasses,
        className,
      )}
    >
      <span className="sr-only">
        Sale price {formatted}, was {compareAtFormatted}
      </span>
      <span aria-hidden="true" className="text-accent">
        {formatted}
      </span>
      <s aria-hidden="true" className="text-fg-muted font-normal">
        {compareAtFormatted}
      </s>
    </span>
  );
}
