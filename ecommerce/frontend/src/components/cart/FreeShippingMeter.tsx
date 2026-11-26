import * as React from 'react';
import { formatMoney } from '@/lib/format/money';
import type { Money } from '@/lib/api/types';
import { cn } from '@/lib/cn';

export interface FreeShippingMeterProps {
  remaining: Money | null;
  threshold: Money | null;
  className?: string;
}

export default function FreeShippingMeter({
  remaining,
  threshold,
  className,
}: FreeShippingMeterProps) {
  if (!remaining || !threshold || threshold.amount <= 0) {
    return null;
  }

  const isUnlocked = remaining.amount === 0;
  const rawPct = Math.round(((threshold.amount - remaining.amount) / threshold.amount) * 100);
  const pct = Math.min(Math.max(rawPct, 0), 100);

  return (
    <div className={cn('p-4 rounded-lg bg-surface-2 space-y-2', className)}>
      <p className="text-body-sm font-medium text-fg">
        {isUnlocked
          ? "You've unlocked free standard delivery."
          : `You're ${formatMoney(remaining)} away from free delivery.`}
      </p>

      <div
        role="progressbar"
        aria-label="Progress to free delivery"
        aria-valuemin={0}
        aria-valuemax={100}
        aria-valuenow={pct}
        className="h-1.5 w-full bg-border rounded-pill overflow-hidden"
      >
        <div
          className="h-full bg-accent origin-left transition-transform duration-500 rounded-pill"
          style={{ transform: `scaleX(${pct / 100})` }}
        />
      </div>
    </div>
  );
}
