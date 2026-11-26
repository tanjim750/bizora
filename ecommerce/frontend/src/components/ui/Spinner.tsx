import * as React from 'react';
import { cn } from '@/lib/cn';

export interface SpinnerProps extends React.ComponentProps<'span'> {
  decorative?: boolean;
}

export function Spinner({ decorative, className, ...props }: SpinnerProps) {
  return (
    <span
      role={decorative ? undefined : 'status'}
      aria-hidden={decorative ? 'true' : undefined}
      aria-label={decorative ? undefined : 'Loading'}
      className={cn(
        'inline-block size-4 animate-spin rounded-pill border-2 border-current border-t-transparent motion-reduce:animate-none',
        className,
      )}
      {...props}
    />
  );
}
