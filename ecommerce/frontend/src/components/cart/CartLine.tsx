'use client';

import * as React from 'react';
import Image from 'next/image';
import Link from 'next/link';
import { motion } from 'motion/react';
import { X } from 'lucide-react';
import { useCartStore } from '@/stores/cart-store';
import { usePrefersReducedMotion } from '@/lib/motion/use-reduced-motion';
import { formatMoney } from '@/lib/format/money';
import { Price } from '@/components/ui/Price';
import { Badge } from '@/components/ui/Badge';
import { IconButton } from '@/components/ui/IconButton';
import QuantityStepper from './QuantityStepper';
import type { CartLine as CartLineType } from '@/lib/api/types';
import { cn } from '@/lib/cn';

export interface CartLineProps {
  line: CartLineType;
  size?: 'md' | 'lg';
  className?: string;
}

export default function CartLine({ line, size = 'md', className }: CartLineProps) {
  const updateQuantity = useCartStore((s) => s.updateQuantity);
  const removeLine = useCartStore((s) => s.removeLine);
  const pendingLineIds = useCartStore((s) => s.pendingLineIds);
  const reduced = usePrefersReducedMotion();

  const isPending = pendingLineIds.includes(line.id);
  const imgWidth = size === 'lg' ? 120 : 80;
  const imgHeight = size === 'lg' ? 150 : 100;

  const content = (
    <div
      className={cn(
        'flex gap-4 py-4 border-b border-border transition-opacity',
        isPending && 'opacity-60',
        className,
      )}
      aria-busy={isPending ? 'true' : undefined}
    >
      <div className="relative shrink-0 overflow-hidden rounded-md bg-surface-2 self-start">
        {line.image ? (
          <Image
            src={line.image.url}
            alt={line.image.alt || line.productName}
            width={imgWidth}
            height={imgHeight}
            className="object-cover"
            style={{ width: `${imgWidth}px`, height: `${imgHeight}px` }}
          />
        ) : (
          <div
            className="flex items-center justify-center bg-surface-2 text-fg-muted text-caption"
            style={{ width: `${imgWidth}px`, height: `${imgHeight}px` }}
          >
            No image
          </div>
        )}
      </div>

      <div className="flex flex-1 flex-col justify-between min-w-0">
        <div className="flex justify-between items-start gap-2">
          <div className="min-w-0">
            <Link
              href={`/products/${line.productSlug}`}
              className="text-body font-medium text-fg hover:text-accent transition-colors line-clamp-1"
            >
              {line.productName}
            </Link>
            <p className="text-body-sm text-fg-muted mt-0.5">{line.variantTitle}</p>
            {line.stockStatus === 'low_stock' && (
              <div className="mt-1">
                <Badge variant="warning">Low stock</Badge>
              </div>
            )}
          </div>

          <IconButton
            aria-label={`Remove ${line.productName}`}
            onClick={() => removeLine(line.id)}
            disabled={isPending}
            className="size-8 -mr-1 -mt-1 text-fg-muted hover:text-fg"
          >
            <X size={16} strokeWidth={1.5} aria-hidden="true" />
          </IconButton>
        </div>

        <div className="flex items-center justify-between gap-4 mt-3">
          <QuantityStepper
            value={line.quantity}
            max={line.maxQuantity}
            onChange={(q) => updateQuantity(line.id, q)}
            label={line.productName}
            size={size === 'lg' ? 'md' : 'sm'}
            disabled={isPending}
          />

          <div className="text-right">
            <Price
              formatted={formatMoney(line.lineTotal)}
              compareAtFormatted={
                line.compareAtUnitPrice
                  ? formatMoney({
                      amount: line.compareAtUnitPrice.amount * line.quantity,
                      currency: line.compareAtUnitPrice.currency,
                    })
                  : null
              }
              size={size === 'lg' ? 'md' : 'sm'}
            />
          </div>
        </div>
      </div>
    </div>
  );

  if (reduced) {
    return <li>{content}</li>;
  }

  return (
    <motion.li
      layout
      initial={{ opacity: 1, x: 0 }}
      exit={{ opacity: 0, x: 24 }}
      transition={{ duration: 0.2 }}
    >
      {content}
    </motion.li>
  );
}
