'use client';

import * as React from 'react';
import { AnimatePresence, motion } from 'motion/react';
import { usePrefersReducedMotion } from '@/lib/motion/use-reduced-motion';
import { distance, spring, staggerDelay } from '@/lib/motion/tokens';
import ProductCard from './ProductCard';
import type { ProductSummary } from '@/lib/api/types';
import { cn } from '@/lib/cn';

export interface ProductGridProps {
  products: ProductSummary[];
  columns?: 'catalog' | 'home';
  animateLayout?: boolean;
  className?: string;
}

export default function ProductGrid({
  products,
  columns = 'catalog',
  animateLayout = false,
  className,
}: ProductGridProps) {
  const reduced = usePrefersReducedMotion();
  const isFirstMount = React.useRef(true);

  React.useEffect(() => {
    isFirstMount.current = false;
  }, []);

  const gridColsClass =
    columns === 'home'
      ? 'grid-cols-2 gap-x-4 gap-y-10 lg:grid-cols-4'
      : 'grid-cols-2 gap-x-4 gap-y-10 lg:grid-cols-3 2xl:grid-cols-4';

  return (
    <ul className={cn('grid', gridColsClass, className)}>
      <AnimatePresence mode="popLayout">
        {products.map((product, index) => {
          const priority = index < 4;

          if (reduced) {
            return (
              <li key={product.id}>
                <ProductCard product={product} priority={priority} />
              </li>
            );
          }

          return (
            <motion.li
              key={product.id}
              layout={animateLayout ? 'position' : undefined}
              initial={isFirstMount.current ? { opacity: 0, y: distance.reveal } : false}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0 }}
              transition={{
                ...spring.soft,
                delay: isFirstMount.current ? staggerDelay(index) : 0,
              }}
            >
              <ProductCard product={product} priority={priority} />
            </motion.li>
          );
        })}
      </AnimatePresence>
    </ul>
  );
}
