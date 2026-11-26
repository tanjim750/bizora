import * as React from 'react';
import { ChevronDown } from 'lucide-react';
import { cn } from '@/lib/cn';

export type SelectProps = React.ComponentProps<'select'>;

export const Select = React.forwardRef<HTMLSelectElement, SelectProps>(
  ({ className, children, ...props }, ref) => {
    return (
      <div className="relative w-full">
        <select
          ref={ref}
          className={cn(
            'peer h-12 w-full appearance-none rounded-sm border border-border-strong bg-surface px-4 pr-10 text-body text-fg transition-[border-color,background-color] motion-reduce:transition-none focus-visible:outline-2 focus-visible:outline-focus focus-visible:outline-offset-2 aria-[invalid=true]:border-danger disabled:cursor-not-allowed disabled:opacity-50',
            className,
          )}
          {...props}
        >
          {children}
        </select>
        <ChevronDown
          size={18}
          strokeWidth={1.5}
          aria-hidden="true"
          className="pointer-events-none absolute right-4 top-1/2 -translate-y-1/2 text-fg-muted transition-opacity peer-disabled:opacity-50"
        />
      </div>
    );
  },
);

Select.displayName = 'Select';
