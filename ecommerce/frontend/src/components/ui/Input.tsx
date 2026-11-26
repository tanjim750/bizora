import * as React from 'react';
import { cn } from '@/lib/cn';

export type InputProps = React.ComponentProps<'input'>;

export const Input = React.forwardRef<HTMLInputElement, InputProps>(
  ({ className, type = 'text', ...props }, ref) => {
    return (
      <input
        ref={ref}
        type={type}
        className={cn(
          'h-12 w-full rounded-sm border border-border-strong bg-surface px-4 text-body text-fg placeholder:text-fg-muted transition-[border-color,background-color] motion-reduce:transition-none focus-visible:outline-2 focus-visible:outline-focus focus-visible:outline-offset-2 aria-[invalid=true]:border-danger disabled:cursor-not-allowed disabled:opacity-50',
          className,
        )}
        {...props}
      />
    );
  },
);

Input.displayName = 'Input';
