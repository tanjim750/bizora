import * as React from 'react';
import { Container, Skeleton, VisuallyHidden } from '@/components/ui';

export default function Loading() {
  return (
    <Container className="py-12 md:py-16" aria-busy="true">
      <VisuallyHidden>Loading…</VisuallyHidden>
      <Skeleton className="h-10 w-64 mb-8" />
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-6">
        {Array.from({ length: 8 }).map((_, index) => (
          <Skeleton key={index} className="aspect-4/5 w-full rounded-md" />
        ))}
      </div>
    </Container>
  );
}
