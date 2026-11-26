import * as React from 'react';
import { cn } from '@/lib/cn';

export type SkeletonProps = React.ComponentProps<'div'>;

export function Skeleton({ className, ...props }: SkeletonProps) {
  return (
    <div
      aria-hidden="true"
      className={cn('rounded-sm bg-surface-2 motion-safe:animate-pulse', className)}
      {...props}
    />
  );
}
