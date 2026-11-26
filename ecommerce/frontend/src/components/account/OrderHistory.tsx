'use client';

import * as React from 'react';
import Image from 'next/image';
import Link from 'next/link';
import StatusBadge, { STATUS_LABEL } from '@/components/account/StatusBadge';
import { Button } from '@/components/ui/Button';
import { browserApi } from '@/lib/api/browser';
import { isApiError } from '@/lib/api/errors';
import type { OrderSummary } from '@/lib/api/types';
import { formatDate } from '@/lib/format/date';
import { formatMoney } from '@/lib/format/money';
import { useSessionStore } from '@/stores/session-store';

export default function OrderHistory() {
  const [items, setItems] = React.useState<OrderSummary[]>([]);
  const [page, setPage] = React.useState<number>(1);
  const [totalPages, setTotalPages] = React.useState<number>(1);
  const [loading, setLoading] = React.useState<boolean>(true);
  const [loadingMore, setLoadingMore] = React.useState<boolean>(false);
  const [error, setError] = React.useState<string | null>(null);

  const fetchOrders = React.useCallback(async (targetPage = 1) => {
    if (targetPage === 1) {
      setLoading(true);
      setError(null);
    } else {
      setLoadingMore(true);
    }

    try {
      const data = await browserApi.orders.list({ page: targetPage });
      if (targetPage === 1) {
        setItems(data.items);
      } else {
        setItems((prev) => [...prev, ...data.items]);
      }
      setPage(data.page);
      setTotalPages(data.totalPages);
    } catch (err) {
      if (isApiError(err) && err.status === 401) {
        useSessionStore.setState({ user: null, status: 'guest' });
        return;
      }
      setError("We couldn't load your orders.");
    } finally {
      setLoading(false);
      setLoadingMore(false);
    }
  }, []);

  React.useEffect(() => {
    fetchOrders(1);
  }, [fetchOrders]);

  const handleLoadMore = () => {
    if (page < totalPages && !loadingMore) {
      fetchOrders(page + 1);
    }
  };

  return (
    <section aria-labelledby="orders-heading" className="mt-12">
      <h2 id="orders-heading" className="font-display text-title-lg text-fg mb-6">
        Your orders
      </h2>

      {loading && (
        <div aria-busy="true" className="space-y-4">
          <div className="h-24 rounded-md bg-surface-2 animate-pulse" />
          <div className="h-24 rounded-md bg-surface-2 animate-pulse" />
          <div className="h-24 rounded-md bg-surface-2 animate-pulse" />
        </div>
      )}

      {error && !loading && (
        <div className="p-6 rounded-lg border border-border text-center space-y-4">
          <p className="text-body text-danger">{error}</p>
          <Button variant="secondary" onClick={() => fetchOrders(1)}>
            Try again
          </Button>
        </div>
      )}

      {!loading && !error && items.length === 0 && (
        <div className="p-8 rounded-lg border border-border text-center space-y-4">
          <p className="text-body text-fg-muted">No orders yet.</p>
          <Button asChild>
            <Link href="/shop">Start shopping</Link>
          </Button>
        </div>
      )}

      {!loading && !error && items.length > 0 && (
        <>
          <ul className="divide-y divide-border">
            {items.map((order) => {
              const statusLabel = STATUS_LABEL[order.status];
              return (
                <li key={order.number}>
                  <Link
                    href={`/account/orders/${order.number}`}
                    aria-label={`Order ${order.number}, ${statusLabel}, ${formatMoney(order.total)}`}
                    className="py-4 flex flex-col sm:flex-row sm:items-center justify-between gap-4 hover:bg-surface-2 transition-colors px-3 -mx-3 rounded-md"
                  >
                    <div className="space-y-1">
                      <div className="flex items-center gap-3">
                        <span className="font-mono font-medium text-fg">{order.number}</span>
                        <StatusBadge status={order.status} />
                      </div>
                      <p className="text-body-sm text-fg-muted">{formatDate(order.placedAt)}</p>
                    </div>

                    <div className="flex items-center gap-4 sm:gap-6 justify-between sm:justify-end">
                      {order.previewImages && order.previewImages.length > 0 && (
                        <div className="flex gap-1.5 shrink-0">
                          {order.previewImages.slice(0, 3).map((img, i) => (
                            <Image
                              key={i}
                              src={img.url}
                              alt={img.alt || ''}
                              width={48}
                              height={48}
                              className="size-12 rounded-sm object-cover bg-surface-2"
                            />
                          ))}
                        </div>
                      )}
                      <div className="text-right">
                        <p className="font-medium text-body text-fg">
                          {formatMoney(order.total)}
                        </p>
                        <p className="text-body-sm text-fg-muted">
                          {order.itemCount} {order.itemCount === 1 ? 'item' : 'items'}
                        </p>
                      </div>
                    </div>
                  </Link>
                </li>
              );
            })}
          </ul>

          {page < totalPages && (
            <div className="mt-8 text-center">
              <Button
                variant="secondary"
                onClick={handleLoadMore}
                loading={loadingMore}
              >
                Load more
              </Button>
            </div>
          )}
        </>
      )}
    </section>
  );
}
