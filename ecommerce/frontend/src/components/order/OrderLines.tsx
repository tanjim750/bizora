import * as React from 'react';
import Image from 'next/image';
import Link from 'next/link';
import type { OrderLine } from '@/lib/api/types';
import { formatMoney } from '@/lib/format/money';

export default function OrderLines({ lines }: { lines: OrderLine[] }) {
  return (
    <ul className="divide-y divide-border">
      {lines.map((line) => (
        <li key={line.id} className="py-4 flex items-center gap-4">
          {line.image ? (
            <Image
              src={line.image.url}
              alt={line.image.alt || line.productName}
              width={64}
              height={80}
              className="w-16 h-20 object-cover rounded-sm bg-surface-2 shrink-0"
            />
          ) : (
            <div
              className="w-16 h-20 rounded-sm bg-surface-2 shrink-0"
              aria-hidden="true"
            />
          )}
          <div className="flex-1 min-w-0">
            <Link
              href={`/products/${line.productSlug}`}
              className="font-medium text-body hover:underline block truncate text-fg"
            >
              {line.productName}
            </Link>
            <p className="text-body-sm text-fg-muted mt-0.5">{line.variantTitle}</p>
            <p className="text-body-sm text-fg-muted mt-0.5">Qty {line.quantity}</p>
          </div>
          <div className="text-right shrink-0">
            <span className="font-medium text-body text-fg">{formatMoney(line.lineTotal)}</span>
          </div>
        </li>
      ))}
    </ul>
  );
}
