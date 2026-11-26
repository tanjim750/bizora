'use client';

import * as React from 'react';
import { ThemeProvider } from 'next-themes';
import { MotionConfig } from 'motion/react';
import CartHydrator from './CartHydrator';
import SessionHydrator from './SessionHydrator';
import Announcer from './Announcer';

export function Providers({ children }: { children: React.ReactNode }) {
  return (
    <ThemeProvider
      attribute="class"
      defaultTheme="system"
      enableSystem
      disableTransitionOnChange={false}
    >
      <MotionConfig reducedMotion="user">
        {children}
        <CartHydrator />
        <SessionHydrator />
        <Announcer />
      </MotionConfig>
    </ThemeProvider>
  );
}
