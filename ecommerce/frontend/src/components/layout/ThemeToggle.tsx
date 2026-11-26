'use client';

import * as React from 'react';
import { useTheme } from 'next-themes';
import { Moon, Sun } from 'lucide-react';
import { AnimatePresence, motion } from 'motion/react';

const emptySubscribe = () => () => {};

export default function ThemeToggle() {
  const { resolvedTheme, setTheme } = useTheme();
  const mounted = React.useSyncExternalStore(
    emptySubscribe,
    () => true,
    () => false,
  );

  if (!mounted) {
    return (
      <span
        className="inline-flex size-11 items-center justify-center rounded-pill text-fg"
        aria-hidden="true"
      />
    );
  }

  const isLight = resolvedTheme === 'light';
  const label = isLight ? 'Switch to dark theme' : 'Switch to light theme';

  return (
    <button
      type="button"
      aria-label={label}
      onClick={() => setTheme(isLight ? 'dark' : 'light')}
      className="inline-flex size-11 items-center justify-center rounded-pill text-fg hover:bg-surface-2"
    >
      <AnimatePresence mode="wait" initial={false}>
        <motion.span
          key={resolvedTheme}
          initial={{ rotate: -90, opacity: 0 }}
          animate={{ rotate: 0, opacity: 1 }}
          exit={{ rotate: 90, opacity: 0 }}
          transition={{ duration: 0.2 }}
          className="inline-flex items-center justify-center"
        >
          {isLight ? (
            <Moon size={20} strokeWidth={1.5} aria-hidden="true" />
          ) : (
            <Sun size={20} strokeWidth={1.5} aria-hidden="true" />
          )}
        </motion.span>
      </AnimatePresence>
    </button>
  );
}
