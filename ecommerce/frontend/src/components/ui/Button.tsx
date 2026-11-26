import * as React from 'react';
import { Slot } from 'radix-ui';
import { cn } from '@/lib/cn';
import { Spinner } from './Spinner';

export interface ButtonProps extends React.ComponentProps<'button'> {
  variant?: 'primary' | 'secondary' | 'ghost' | 'link';
  size?: 'sm' | 'md' | 'lg';
  loading?: boolean;
  asChild?: boolean;
}

export function Button({
  variant = 'primary',
  size = 'md',
  loading = false,
  asChild = false,
  type = 'button',
  disabled,
  className,
  children,
  ...props
}: ButtonProps) {
  const baseClasses =
    'inline-flex items-center justify-center gap-2 rounded-pill font-medium transition-[transform,scale,background-color,color,opacity] duration-200 ease-out active:scale-[0.98] motion-reduce:transition-none motion-reduce:active:scale-100 disabled:cursor-not-allowed disabled:opacity-50 min-h-11';

  const variantClasses = {
    primary: 'bg-accent text-accent-fg hover:opacity-90',
    secondary: 'border border-border-strong text-fg hover:bg-surface-2',
    ghost: 'text-fg hover:bg-surface-2',
    link: 'text-accent underline-offset-4 hover:underline min-h-0',
  }[variant];

  const sizeClasses = {
    sm: 'px-4 text-small',
    md: 'px-5 text-body',
    lg: 'px-7 text-body-lg min-h-13',
  }[size];

  const Component = asChild ? Slot.Root : 'button';

  if (asChild) {
    return (
      <Component className={cn(baseClasses, sizeClasses, variantClasses, className)} {...props}>
        {children}
      </Component>
    );
  }

  return (
    <button
      type={type}
      disabled={disabled || loading}
      aria-busy={loading ? 'true' : undefined}
      className={cn(baseClasses, sizeClasses, variantClasses, className)}
      {...props}
    >
      {loading && <Spinner decorative className="mr-1" />}
      {children}
    </button>
  );
}
