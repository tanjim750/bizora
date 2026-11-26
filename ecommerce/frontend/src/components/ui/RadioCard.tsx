'use client';

import * as React from 'react';
import { RadioGroup } from 'radix-ui';
import { cn } from '@/lib/cn';

export interface RadioCardProps {
  value: string;
  title: React.ReactNode;
  description?: React.ReactNode;
  aside?: React.ReactNode;
  disabled?: boolean;
  className?: string;
}

export function RadioCard({
  value,
  title,
  description,
  aside,
  disabled,
  className,
}: RadioCardProps) {
  const generatedId = React.useId();
  const titleId = `${generatedId}-title`;
  const descId = description ? `${generatedId}-desc` : undefined;

  return (
    <RadioGroup.Item
      value={value}
      disabled={disabled}
      aria-labelledby={titleId}
      aria-describedby={descId}
      className={cn(
        'group w-full rounded-md border border-border p-4 text-left transition-[border-color,background-color] motion-reduce:transition-none flex items-start justify-between gap-4 data-[state=checked]:border-accent data-[state=checked]:bg-surface-2 focus-visible:outline-2 focus-visible:outline-focus focus-visible:outline-offset-2 disabled:cursor-not-allowed disabled:opacity-50 cursor-pointer',
        className,
      )}
    >
      <div className="flex items-start gap-3 min-w-0">
        <span className="relative mt-0.5 flex size-4 shrink-0 items-center justify-center rounded-pill border border-border-strong group-data-[state=checked]:border-accent transition-[border-color] motion-reduce:transition-none">
          <RadioGroup.Indicator className="size-2 rounded-pill bg-accent" />
        </span>
        <div className="flex flex-col gap-0.5 min-w-0">
          <span id={titleId} className="text-body font-medium text-fg">
            {title}
          </span>
          {description && (
            <span id={descId} className="text-small text-fg-muted">
              {description}
            </span>
          )}
        </div>
      </div>
      {aside && <div className="shrink-0">{aside}</div>}
    </RadioGroup.Item>
  );
}
