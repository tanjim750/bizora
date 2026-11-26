'use client';

import * as React from 'react';
import { motion } from 'motion/react';
import { usePrefersReducedMotion } from '@/lib/motion/use-reduced-motion';
import { distance, duration, ease } from '@/lib/motion/tokens';

let firstLoad = true;

export default function Template({ children }: { children: React.ReactNode }) {
  const reduced = usePrefersReducedMotion();

  React.useEffect(() => {
    if (firstLoad) {
      firstLoad = false;
      return;
    }
    if (typeof window !== 'undefined' && !window.location.hash) {
      document.getElementById('main')?.focus({ preventScroll: true });
    }
  }, []);

  return (
    <motion.div
      initial={reduced ? { opacity: 0.98 } : { opacity: 0, y: distance.page }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: reduced ? 0 : duration.base, ease: ease.out }}
    >
      {children}
    </motion.div>
  );
}
