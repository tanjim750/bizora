import * as React from 'react';
import { Skeleton } from '@/components/ui/Skeleton';
import { cn } from '@/lib/cn';

export default function ProductCardSkeleton({ className }: { className?: string }) {
  return (
    <div className={cn('flex flex-col space-y-3', className)} aria-hidden="true">
      <Skeleton className="aspect-4/5 w-full rounded-md" />
      <div className="space-y-2 pt-1">
        <Skeleton className="h-4 w-3/4 rounded" />
        <Skeleton className="h-4 w-1/3 rounded" />
      </div>
    </div>
  );
}
