import * as React from 'react';
import { cn } from '@/lib/cn';

export interface BadgeProps extends React.ComponentProps<'span'> {
  variant?: 'neutral' | 'accent' | 'success' | 'warning' | 'danger';
}

export function Badge({ variant = 'neutral', className, children, ...props }: BadgeProps) {
  const variantClasses = {
    neutral: 'bg-surface-2 text-fg',
    accent: 'bg-accent text-accent-fg',
    success: 'bg-surface text-success border border-success',
    warning: 'bg-surface text-warning border border-warning',
    danger: 'bg-surface text-danger border border-danger',
  }[variant];

  return (
    <span
      className={cn(
        'text-label-caps rounded-pill px-2.5 py-1 inline-flex items-center justify-center font-medium',
        variantClasses,
        className,
      )}
      {...props}
    >
      {children}
    </span>
  );
}
