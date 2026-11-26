'use client';

import * as React from 'react';
import { AnimatePresence, motion } from 'motion/react';
import { usePrefersReducedMotion } from '@/lib/motion/use-reduced-motion';
import { spring } from '@/lib/motion/tokens';
import { cn } from '@/lib/cn';

export interface RollingNumberProps {
  value: number | string;
  className?: string;
}

export default function RollingNumber({ value, className }: RollingNumberProps) {
  const reduced = usePrefersReducedMotion();

  if (reduced) {
    return <span className={cn('tabular-nums', className)}>{value}</span>;
  }

  return (
    <span className={cn('relative inline-flex overflow-hidden tabular-nums', className)}>
      <AnimatePresence mode="popLayout" initial={false}>
        <motion.span
          key={String(value)}
          initial={{ y: '100%', opacity: 0 }}
          animate={{ y: 0, opacity: 1 }}
          exit={{ y: '-100%', opacity: 0 }}
          transition={spring.snappy}
          className="inline-block"
        >
          {value}
        </motion.span>
      </AnimatePresence>
    </span>
  );
}
