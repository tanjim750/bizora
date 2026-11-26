'use client';

import * as React from 'react';
import { motion } from 'motion/react';
import { distance, duration, ease } from '@/lib/motion/tokens';
import { usePrefersReducedMotion } from '@/lib/motion/use-reduced-motion';

export interface RevealProps {
  children: React.ReactNode;
  as?: 'div' | 'section' | 'li';
  delay?: number;
  className?: string;
}

const emptySubscribe = () => () => {};

export function Reveal({ children, as = 'div', delay, className }: RevealProps) {
  const shouldReduceMotion = usePrefersReducedMotion();
  const mounted = React.useSyncExternalStore(
    emptySubscribe,
    () => true,
    () => false,
  );

  if (!mounted || shouldReduceMotion) {
    const PlainComponent = as;
    return <PlainComponent className={className}>{children}</PlainComponent>;
  }

  const MotionComponent = motion[as];

  return (
    <MotionComponent
      initial={{ opacity: 0, y: distance.reveal }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true, margin: '0px 0px -10% 0px' }}
      transition={{ duration: duration.slow, ease: ease.out, delay }}
      className={className}
    >
      {children}
    </MotionComponent>
  );
}
