import * as React from 'react';
import { cn } from '@/lib/cn';

export type VisuallyHiddenProps = React.ComponentProps<'span'>;

export function VisuallyHidden({ className, ...props }: VisuallyHiddenProps) {
  return <span className={cn('sr-only', className)} {...props} />;
}
