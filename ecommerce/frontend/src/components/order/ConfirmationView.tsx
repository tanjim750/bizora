'use client';

import * as React from 'react';
import Link from 'next/link';
import ConfirmationCheck from '@/components/order/ConfirmationCheck';
import OrderLines from '@/components/order/OrderLines';
import { Button } from '@/components/ui/Button';
import { Container } from '@/components/ui/Container';
import { Reveal } from '@/components/motion/Reveal';
import { browserApi } from '@/lib/api/browser';
import { isApiError, toUserMessage } from '@/lib/api/errors';
import type { Order } from '@/lib/api/types';
import { formatMoney } from '@/lib/format/money';
import { staggerDelay } from '@/lib/motion/tokens';
import { useSessionStore } from '@/stores/session-store';

const COUNTRY_MAP: Record<string, string> = {
  BD: 'Bangladesh',
};

interface ConfirmationViewProps {
  orderNumber: string;
  token?: string;
}

export default function ConfirmationView({ orderNumber, token }: ConfirmationViewProps) {
  const [order, setOrder] = React.useState<Order | null>(null);
  const [loading, setLoading] = React.useState<boolean>(true);
  const [errorStatus, setErrorStatus] = React.useState<number | null>(null);
  const [errorMessage, setErrorMessage] = React.useState<string | null>(null);

  const sessionStatus = useSessionStore((s) => s.status);

  const fetchOrder = React.useCallback(async () => {
    setLoading(true);
    setErrorStatus(null);
    setErrorMessage(null);
    try {
      const data = await browserApi.orders.get(orderNumber, token);
      setOrder(data);
    } catch (err) {
      if (isApiError(err)) {
        setErrorStatus(err.status);
        setErrorMessage(toUserMessage(err));
      } else {
        setErrorMessage(toUserMessage(err));
      }
    } finally {
      setLoading(false);
    }
  }, [orderNumber, token]);

  React.useEffect(() => {
    fetchOrder();
  }, [fetchOrder]);

  if (loading) {
    return (
      <Container className="py-12 max-w-2xl mx-auto">
        <div aria-busy="true" className="flex flex-col items-center gap-4">
          <div className="size-20 rounded-pill bg-surface-2 animate-pulse" />
          <div className="w-48 h-8 rounded-sm bg-surface-2 animate-pulse mt-4" />
          <div className="w-64 h-4 rounded-sm bg-surface-2 animate-pulse" />
          <div className="w-56 h-4 rounded-sm bg-surface-2 animate-pulse" />
          <div className="w-72 h-4 rounded-sm bg-surface-2 animate-pulse" />
        </div>
      </Container>
    );
  }

  if (errorStatus === 404) {
    return (
      <Container className="py-12 max-w-2xl mx-auto text-center">
        <h1 className="font-display text-display-md text-fg mb-4">
          We couldn&apos;t find this order.
        </h1>
        <Button asChild>
          <Link href="/shop">Go to the shop</Link>
        </Button>
      </Container>
    );
  }

  if (errorMessage && !order) {
    return (
      <Container className="py-12 max-w-2xl mx-auto text-center">
        <div role="alert" className="mb-6 p-4 rounded-md bg-surface-2 text-danger">
          <p>{errorMessage}</p>
        </div>
        <Button onClick={fetchOrder}>Try again</Button>
      </Container>
    );
  }

  if (!order) return null;

  const { shippingAddress, shippingMethod, paymentMethod, total, lines } = order;
  const isCod = paymentMethod.id === 'cod';
  const countryName = COUNTRY_MAP[shippingAddress.countryCode] || shippingAddress.countryCode;

  return (
    <Container className="py-12 max-w-2xl mx-auto space-y-10">
      {/* Moment Header */}
      <div className="flex flex-col items-center text-center">
        <ConfirmationCheck className="size-20 text-success mb-6" />
        <h1 className="font-display text-display-md text-fg mb-2">
          Thank you, {shippingAddress.firstName}!
        </h1>
        <p className="text-body text-fg">
          Order <span className="font-mono font-medium">{order.number}</span> is confirmed.
        </p>
        <p className="text-body text-fg-muted mt-1">
          A confirmation will be sent to {order.email}.
        </p>
      </div>

      {/* What happens next */}
      <Reveal delay={staggerDelay(0)} className="rounded-lg border border-border p-6 bg-surface">
        <h2 className="font-display text-title-md text-fg mb-4">What happens next</h2>
        <ol className="list-decimal list-inside space-y-2 text-body text-fg">
          <li>We prepare your order</li>
          <li>It ships with {shippingMethod.label}</li>
          {isCod && <li>You pay {formatMoney(total)} in cash on delivery</li>}
        </ol>
      </Reveal>

      {/* Delivery address */}
      <Reveal delay={staggerDelay(1)} className="rounded-lg border border-border p-6 bg-surface">
        <h2 className="font-display text-title-md text-fg mb-4">Delivery address</h2>
        <div className="text-body text-fg space-y-1">
          <p className="font-medium">
            {shippingAddress.firstName} {shippingAddress.lastName}
          </p>
          <p>{shippingAddress.line1}</p>
          {shippingAddress.line2 && <p>{shippingAddress.line2}</p>}
          <p>
            {shippingAddress.city} {shippingAddress.postalCode}
          </p>
          <p>{countryName}</p>
        </div>
      </Reveal>

      {/* Order Lines */}
      <Reveal delay={staggerDelay(2)} className="rounded-lg border border-border p-6 bg-surface">
        <h2 className="font-display text-title-md text-fg mb-4">Items</h2>
        <OrderLines lines={lines} />

        {/* Totals */}
        <div className="mt-6 pt-6 border-t border-border space-y-2 text-body">
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
      </Reveal>

      {/* Actions */}
      <Reveal delay={staggerDelay(3)} className="flex flex-col sm:flex-row gap-4 justify-center">
        <Button asChild variant="secondary">
          <Link href="/shop">Continue shopping</Link>
        </Button>
        {sessionStatus === 'signed-in' ? (
          <Button asChild>
            <Link href="/account">View your orders</Link>
          </Button>
        ) : (
          <Button asChild>
            <Link href="/account/register">Create an account</Link>
          </Button>
        )}
      </Reveal>
    </Container>
  );
}
