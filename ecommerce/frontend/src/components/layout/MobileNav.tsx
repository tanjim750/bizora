'use client';

import * as React from 'react';
import Link from 'next/link';
import { Dialog } from 'radix-ui';
import { motion, AnimatePresence } from 'motion/react';
import { X } from 'lucide-react';
import { useUiStore } from '@/stores/ui-store';
import { usePrefersReducedMotion } from '@/lib/motion/use-reduced-motion';
import { spring } from '@/lib/motion/tokens';
import { IconButton } from '@/components/ui/IconButton';
import ThemeToggle from '@/components/layout/ThemeToggle';
import type { Category } from '@/lib/api/types';

export default function MobileNav({ categories }: { categories: Category[] }) {
  const mobileNavOpen = useUiStore((s) => s.mobileNavOpen);
  const setMobileNavOpen = useUiStore((s) => s.setMobileNavOpen);
  const reducedMotion = usePrefersReducedMotion();

  const close = () => setMobileNavOpen(false);

  return (
    <Dialog.Root open={mobileNavOpen} onOpenChange={setMobileNavOpen}>
      <AnimatePresence>
        {mobileNavOpen && (
          <Dialog.Portal forceMount>
            <Dialog.Overlay asChild>
              <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                transition={{ duration: 0.2 }}
                className="fixed inset-0 z-(--aur-z-overlay) bg-overlay backdrop-blur-xs"
              />
            </Dialog.Overlay>

            <Dialog.Content asChild>
              <motion.div
                initial={{ x: reducedMotion ? 0 : '-100%', opacity: reducedMotion ? 0 : 1 }}
                animate={{ x: 0, opacity: 1 }}
                exit={{ x: reducedMotion ? 0 : '-100%', opacity: reducedMotion ? 0 : 1 }}
                transition={reducedMotion ? { duration: 0.15 } : spring.snappy}
                className="fixed inset-y-0 left-0 z-(--aur-z-drawer) flex w-full max-w-sm flex-col bg-surface shadow-modal focus:outline-none"
              >
                <div className="flex h-16 items-center justify-between border-b border-border px-6">
                  <Dialog.Title className="font-display text-title">Menu</Dialog.Title>
                  <Dialog.Close asChild>
                    <IconButton aria-label="Close menu" onClick={close}>
                      <X size={20} strokeWidth={1.5} aria-hidden="true" />
                    </IconButton>
                  </Dialog.Close>
                </div>

                <div className="flex-1 overflow-y-auto px-6 py-6">
                  <nav aria-label="Mobile Navigation" className="flex flex-col gap-1">
                    <Link
                      href="/shop"
                      onClick={close}
                      className="rounded-lg px-3 py-3 text-body-lg font-medium text-fg hover:bg-surface-2 transition-colors"
                    >
                      Shop all
                    </Link>
                    {categories.map((cat) => (
                      <Link
                        key={cat.id}
                        href={`/shop?category=${cat.slug}`}
                        onClick={close}
                        className="rounded-lg px-3 py-3 text-body-lg font-medium text-fg hover:bg-surface-2 transition-colors"
                      >
                        {cat.name}
                      </Link>
                    ))}
                    <div className="my-4 border-t border-border" />
                    <Link
                      href="/account"
                      onClick={close}
                      className="rounded-lg px-3 py-3 text-body-lg font-medium text-fg hover:bg-surface-2 transition-colors"
                    >
                      Account
                    </Link>
                  </nav>
                </div>

                <div className="border-t border-border p-6 flex items-center justify-between">
                  <span className="text-body-sm text-fg-muted">Theme</span>
                  <ThemeToggle />
                </div>
              </motion.div>
            </Dialog.Content>
          </Dialog.Portal>
        )}
      </AnimatePresence>
    </Dialog.Root>
  );
}
