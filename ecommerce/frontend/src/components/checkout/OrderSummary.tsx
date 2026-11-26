import * as React from 'react';
import Image from 'next/image';
import { formatMoney } from '@/lib/format/money';
import { Skeleton } from '@/components/ui/Skeleton';
import { Button } from '@/components/ui/Button';
import type { Cart, Quote } from '@/lib/api/types';

export interface OrderSummaryProps {
  cart: Cart;
  quote: Quote | null;
  status: 'loading' | 'ready' | 'error';
  taxLabel: string;
  onRetry: () => void;
}

export default function OrderSummary({
  cart,
  quote,
  status,
  taxLabel,
  onRetry,
}: OrderSummaryProps) {
  const taxRatePercent = quote ? quote.taxRateBps / 100 : 5;

  return (
    <div className="rounded-lg border border-border bg-surface p-6 space-y-6">
      <h2 className="text-title font-semibold text-fg">Order summary</h2>

      <ul className="divide-y divide-border">
        {cart.lines.map((line) => (
          <li key={line.id} className="flex gap-4 py-3">
            <div className="relative shrink-0 overflow-hidden rounded-sm bg-surface-2 self-start">
              {line.image ? (
                <Image
                  src={line.image.url}
                  alt={line.image.alt || line.productName}
                  width={64}
                  height={80}
                  className="object-cover"
                />
              ) : (
                <div className="w-16 h-20 bg-surface-2" />
              )}
              <span className="absolute -top-1.5 -right-1.5 flex size-5 items-center justify-center rounded-pill bg-fg-muted text-bg text-caption font-semibold">
                {line.quantity}
              </span>
            </div>

            <div className="flex flex-1 flex-col justify-center min-w-0">
              <p className="font-medium text-body text-fg truncate">{line.productName}</p>
              <p className="text-small text-fg-muted truncate">{line.variantTitle}</p>
            </div>

            <div className="self-center font-medium text-body text-fg shrink-0">
              {formatMoney(line.lineTotal)}
            </div>
          </li>
        ))}
      </ul>

      {status === 'error' ? (
        <div className="space-y-3 pt-4 border-t border-border">
          <p className="text-small text-danger">We couldn&apos;t calculate the total.</p>
          <Button
            type="button"
            variant="ghost"
            onClick={onRetry}
            className="p-0 h-auto text-accent underline"
          >
            Try again
          </Button>
        </div>
      ) : (
        <div className="space-y-3 pt-4 border-t border-border text-body">
          <div className="flex justify-between items-center">
            <span className="text-fg-muted">Subtotal</span>
            {status === 'loading' && !quote ? (
              <Skeleton className="h-5 w-16" />
            ) : (
              <span className="font-medium text-fg">
                {formatMoney(quote ? quote.subtotal : cart.subtotal)}
              </span>
            )}
          </div>

          <div className="flex justify-between items-center">
            <span className="text-fg-muted">Delivery</span>
            {status === 'loading' && !quote ? (
              <Skeleton className="h-5 w-16" />
            ) : (
              <span className="font-medium text-fg">
                {quote ? (quote.freeShippingApplied ? 'Free' : formatMoney(quote.shipping)) : '—'}
              </span>
            )}
          </div>

          <div className="flex justify-between items-center">
            <span className="text-fg-muted">
              {taxLabel} ({taxRatePercent}%)
            </span>
            {status === 'loading' && !quote ? (
              <Skeleton className="h-5 w-16" />
            ) : (
              <span className="font-medium text-fg">{quote ? formatMoney(quote.tax) : '—'}</span>
            )}
          </div>

          <div className="flex justify-between items-center pt-3 border-t border-border text-title font-semibold text-fg">
            <span>Total</span>
            {status === 'loading' && !quote ? (
              <Skeleton className="h-6 w-20" />
            ) : (
              <span>{quote ? formatMoney(quote.total) : '—'}</span>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
