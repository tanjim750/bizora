import * as React from 'react';
import type { OrderStatus } from '@/lib/api/types';
import { Badge, type BadgeProps } from '@/components/ui/Badge';

export const STATUS_LABEL: Record<OrderStatus, string> = {
  placed: 'Placed',
  processing: 'Processing',
  shipped: 'Shipped',
  delivered: 'Delivered',
  cancelled: 'Cancelled',
};

const STATUS_VARIANT: Record<OrderStatus, NonNullable<BadgeProps['variant']>> = {
  placed: 'neutral',
  processing: 'neutral',
  shipped: 'accent',
  delivered: 'success',
  cancelled: 'danger',
};

export default function StatusBadge({
  status,
  className,
}: {
  status: OrderStatus;
  className?: string;
}) {
  return (
    <Badge variant={STATUS_VARIANT[status]} className={className}>
      {STATUS_LABEL[status]}
    </Badge>
  );
}
