'use client';

import * as React from 'react';
import { Minus, Plus } from 'lucide-react';
import { IconButton } from '@/components/ui/IconButton';
import { cn } from '@/lib/cn';

export interface QuantityStepperProps {
  value: number;
  min?: number;
  max: number;
  onChange: (n: number) => void;
  label: string;
  disabled?: boolean;
  size?: 'sm' | 'md';
  className?: string;
}

export default function QuantityStepper({
  value,
  min = 1,
  max,
  onChange,
  label,
  disabled = false,
  size = 'md',
  className,
}: QuantityStepperProps) {
  const [prevValue, setPrevValue] = React.useState(value);
  const [localValue, setLocalValue] = React.useState(String(value));

  if (value !== prevValue) {
    setPrevValue(value);
    setLocalValue(String(value));
  }

  const commitValue = (valStr: string) => {
    const parsed = parseInt(valStr, 10);
    if (isNaN(parsed)) {
      setLocalValue(String(value));
      return;
    }
    const clamped = Math.min(Math.max(parsed, min), max);
    setLocalValue(String(clamped));
    onChange(clamped);
  };

  const isMin = value <= min;
  const isMax = value >= max;

  return (
    <div className={cn('inline-flex items-center gap-2', className)}>
      <div
        className={cn(
          'rounded-pill border border-border inline-flex items-center bg-bg',
          size === 'sm' ? 'h-8 px-1' : 'h-10 px-1.5',
        )}
      >
        <IconButton
          aria-label="Decrease quantity"
          disabled={disabled || isMin}
          onClick={() => onChange(Math.max(min, value - 1))}
          className={cn(size === 'sm' ? 'size-7' : 'size-8', 'rounded-pill min-h-0')}
        >
          <Minus size={14} strokeWidth={2} aria-hidden="true" />
        </IconButton>

        <input
          type="number"
          inputMode="numeric"
          aria-label={`Quantity for ${label}`}
          disabled={disabled}
          value={localValue}
          onChange={(e) => setLocalValue(e.target.value)}
          onBlur={() => commitValue(localValue)}
          onKeyDown={(e) => {
            if (e.key === 'Enter') {
              commitValue(localValue);
            }
          }}
          className={cn(
            'w-10 text-center text-body font-mono font-medium bg-transparent focus:outline-none [-moz-appearance:textfield] [&::-webkit-inner-spin-button]:m-0 [&::-webkit-inner-spin-button]:appearance-none [&::-webkit-outer-spin-button]:m-0 [&::-webkit-outer-spin-button]:appearance-none',
            size === 'sm' ? 'text-body-sm' : 'text-body',
          )}
        />

        <IconButton
          aria-label="Increase quantity"
          disabled={disabled || isMax}
          onClick={() => onChange(Math.min(max, value + 1))}
          className={cn(size === 'sm' ? 'size-7' : 'size-8', 'rounded-pill min-h-0')}
        >
          <Plus size={14} strokeWidth={2} aria-hidden="true" />
        </IconButton>
      </div>

      {isMax && <span className="text-small text-fg-muted">Max {max}</span>}
    </div>
  );
}
