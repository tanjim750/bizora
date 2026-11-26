'use client';

import * as React from 'react';
import Link from 'next/link';
import { ArrowLeft } from 'lucide-react';
import StatusBadge from '@/components/account/StatusBadge';
import OrderLines from '@/components/order/OrderLines';
import { Button } from '@/components/ui/Button';
import { Container } from '@/components/ui/Container';
import { browserApi } from '@/lib/api/browser';
import { isApiError, toUserMessage } from '@/lib/api/errors';
import type { Order, OrderStatus, PaymentStatus } from '@/lib/api/types';
import { cn } from '@/lib/cn';
import { formatDate } from '@/lib/format/date';
import { formatMoney } from '@/lib/format/money';
import { useSessionStore } from '@/stores/session-store';

const PROGRESS_STEPS: { id: OrderStatus; label: string }[] = [
  { id: 'placed', label: 'Placed' },
  { id: 'processing', label: 'Processing' },
  { id: 'shipped', label: 'Shipped' },
  { id: 'delivered', label: 'Delivered' },
];

const PAYMENT_LABEL: Record<PaymentStatus, string> = {
  pending: 'Payment pending',
  paid: 'Paid',
  refunded: 'Refunded',
};

const COUNTRY_MAP: Record<string, string> = {
  BD: 'Bangladesh',
};

export default function OrderDetail({ orderNumber }: { orderNumber: string }) {
  const [order, setOrder] = React.useState<Order | null>(null);
  const [loading, setLoading] = React.useState<boolean>(true);
  const [errorStatus, setErrorStatus] = React.useState<number | null>(null);
  const [errorMessage, setErrorMessage] = React.useState<string | null>(null);

  const fetchOrder = React.useCallback(async () => {
    setLoading(true);
    setErrorStatus(null);
    setErrorMessage(null);

    try {
      const data = await browserApi.orders.get(orderNumber);
      setOrder(data);
    } catch (err) {
      if (isApiError(err)) {
        if (err.status === 401) {
          useSessionStore.setState({ user: null, status: 'guest' });
          return;
        }
        setErrorStatus(err.status);
        setErrorMessage(toUserMessage(err));
      } else {
        setErrorMessage(toUserMessage(err));
      }
    } finally {
      setLoading(false);
    }
  }, [orderNumber]);

  React.useEffect(() => {
    fetchOrder();
  }, [fetchOrder]);

  if (loading) {
    return (
      <Container className="py-12 max-w-4xl mx-auto space-y-6">
        <div aria-busy="true" className="space-y-4">
          <div className="w-24 h-4 bg-surface-2 rounded-sm animate-pulse" />
          <div className="w-64 h-8 bg-surface-2 rounded-sm animate-pulse" />
          <div className="w-48 h-4 bg-surface-2 rounded-sm animate-pulse" />
          <div className="w-full h-40 bg-surface-2 rounded-md animate-pulse mt-8" />
        </div>
      </Container>
    );
  }

  if (errorStatus === 404) {
    return (
      <Container className="py-12 max-w-4xl mx-auto space-y-4 text-center">
        <h1 className="font-display text-display-md text-fg">We couldn&apos;t find this order.</h1>
        <div>
          <Button asChild variant="secondary">
            <Link href="/account">All orders</Link>
          </Button>
        </div>
      </Container>
    );
  }

  if (errorMessage && !order) {
    return (
      <Container className="py-12 max-w-4xl mx-auto text-center space-y-4">
        <div role="alert" className="p-4 rounded-md bg-surface-2 text-danger">
          <p>{errorMessage}</p>
        </div>
        <Button onClick={fetchOrder}>Try again</Button>
      </Container>
    );
  }

  if (!order) return null;

  const { shippingAddress, shippingMethod, paymentMethod, lines } = order;
  const currentIndex = PROGRESS_STEPS.findIndex((s) => s.id === order.status);
  const countryName = COUNTRY_MAP[shippingAddress.countryCode] || shippingAddress.countryCode;

  return (
    <Container className="py-12 max-w-4xl mx-auto space-y-8">
      {/* Back Link */}
      <div>
        <Link
          href="/account"
          className="inline-flex items-center gap-2 text-body-sm text-fg-muted hover:text-fg transition-colors"
        >
          <ArrowLeft size={16} aria-hidden="true" />
          All orders
        </Link>
      </div>

      {/* Header */}
      <div className="space-y-2 pb-6 border-b border-border">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <h1 className="font-display text-display-md text-fg">Order {order.number}</h1>
          <div className="flex items-center gap-3">
            <StatusBadge status={order.status} />
            <span className="text-body-sm text-fg-muted">{PAYMENT_LABEL[order.paymentStatus]}</span>
          </div>
        </div>
        <p className="text-body text-fg-muted">Placed on {formatDate(order.placedAt)}</p>
      </div>

      {/* Status Track */}
      <div className="p-6 rounded-lg border border-border bg-surface">
        {order.status === 'cancelled' ? (
          <p className="text-body font-medium text-danger">This order was cancelled.</p>
        ) : (
          <ol
            aria-label="Order progress"
            className="flex items-center justify-between max-w-lg mx-auto"
          >
            {PROGRESS_STEPS.map((step, i) => {
              const isCurrent = i === currentIndex;
              const isPastOrCurrent = i <= currentIndex;
              return (
                <li
                  key={step.id}
                  aria-current={isCurrent ? 'step' : undefined}
                  className="flex flex-col items-center gap-2 text-center flex-1"
                >
                  <span
                    className={cn(
                      'size-3 rounded-pill',
                      isPastOrCurrent ? 'bg-accent' : 'border border-border-strong bg-transparent',
                    )}
                    aria-hidden="true"
                  />
                  <span
                    className={cn(
                      'text-body-sm',
                      isCurrent
                        ? 'font-medium text-fg'
                        : isPastOrCurrent
                          ? 'text-fg'
                          : 'text-fg-muted',
                    )}
                  >
                    {step.label}
                  </span>
                </li>
              );
            })}
          </ol>
        )}
      </div>

      {/* Info Blocks Grid */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div className="p-6 rounded-lg border border-border bg-surface space-y-2">
          <h2 className="font-display text-title-sm text-fg">Delivery address</h2>
          <div className="text-body-sm text-fg-muted space-y-0.5">
            <p className="font-medium text-fg">
              {shippingAddress.firstName} {shippingAddress.lastName}
            </p>
            <p>{shippingAddress.line1}</p>
            {shippingAddress.line2 && <p>{shippingAddress.line2}</p>}
            <p>
              {shippingAddress.city} {shippingAddress.postalCode}
            </p>
            <p>{countryName}</p>
          </div>
        </div>

        <div className="p-6 rounded-lg border border-border bg-surface space-y-2">
          <h2 className="font-display text-title-sm text-fg">Delivery method</h2>
          <div className="text-body-sm text-fg-muted">
            <p className="font-medium text-fg">{shippingMethod.label}</p>
            <p className="mt-1">
              {shippingMethod.price.amount === 0 ? 'Free' : formatMoney(shippingMethod.price)}
            </p>
          </div>
        </div>

        <div className="p-6 rounded-lg border border-border bg-surface space-y-2">
          <h2 className="font-display text-title-sm text-fg">Payment method</h2>
          <div className="text-body-sm text-fg-muted">
            <p className="font-medium text-fg">{paymentMethod.label}</p>
          </div>
        </div>
      </div>

      {/* Items & Totals */}
      <div className="p-6 rounded-lg border border-border bg-surface space-y-6">
        <h2 className="font-display text-title-md text-fg">Items</h2>
        <OrderLines lines={lines} />

        <div className="pt-6 border-t border-border space-y-2 text-body">
          <div className="flex justify-between text-fg-muted">
            <span>Subtotal</span>
            <span className="text-fg">{formatMoney(order.subtotal)}</span>
          </div>
          <div className="flex justify-between text-fg-muted">
            <span>Delivery</span>
            <span className="text-fg">
              {order.shipping.amount === 0 ? 'Free' : formatMoney(order.shipping)}
            </span>
          </div>
          <div className="flex justify-between text-fg-muted">
            <span>VAT</span>
            <span className="text-fg">{formatMoney(order.tax)}</span>
          </div>
          <div className="flex justify-between font-medium text-title-sm text-fg pt-2 border-t border-border">
            <span>Total</span>
            <span>{formatMoney(order.total)}</span>
          </div>
        </div>
      </div>
    </Container>
  );
}
