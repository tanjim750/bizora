'use client';

import * as React from 'react';
import { Checkbox as RadixCheckbox } from 'radix-ui';
import { Check } from 'lucide-react';
import { cn } from '@/lib/cn';

export interface CheckboxProps {
  id: string;
  label: React.ReactNode;
  checked?: boolean;
  onCheckedChange?: (checked: boolean) => void;
  disabled?: boolean;
  className?: string;
}

export function Checkbox({
  id,
  label,
  checked,
  onCheckedChange,
  disabled,
  className,
}: CheckboxProps) {
  return (
    <div className={cn('min-h-11 inline-flex items-center gap-3', className)}>
      <RadixCheckbox.Root
        id={id}
        checked={checked}
        onCheckedChange={(val) => {
          if (typeof onCheckedChange === 'function') {
            onCheckedChange(val === true);
          }
        }}
        disabled={disabled}
        className="peer relative size-5 shrink-0 rounded-sm border border-border-strong bg-surface transition-[border-color,background-color] motion-reduce:transition-none data-[state=checked]:border-accent data-[state=checked]:bg-accent inline-flex items-center justify-center focus-visible:outline-2 focus-visible:outline-focus focus-visible:outline-offset-2 disabled:cursor-not-allowed disabled:opacity-50 before:absolute before:left-1/2 before:top-1/2 before:size-11 before:-translate-x-1/2 before:-translate-y-1/2 before:content-['']"
      >
        <RadixCheckbox.Indicator className="inline-flex items-center justify-center text-accent-fg">
          <Check size={14} strokeWidth={1.5} aria-hidden="true" />
        </RadixCheckbox.Indicator>
      </RadixCheckbox.Root>
      <label
        htmlFor={id}
        className="text-body text-fg select-none cursor-pointer peer-disabled:cursor-not-allowed peer-disabled:opacity-50"
      >
        {label}
      </label>
    </div>
  );
}
