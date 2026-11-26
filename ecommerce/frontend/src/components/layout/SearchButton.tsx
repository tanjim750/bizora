'use client';

import * as React from 'react';
import { Search } from 'lucide-react';
import { useUiStore } from '@/stores/ui-store';

const emptySubscribe = () => () => {};

function getShortcutSnapshot(): string {
  if (typeof window === 'undefined') return 'Ctrl K';
  const isMac = /(Mac|iPhone|iPod|iPad)/i.test(navigator.platform || navigator.userAgent);
  return isMac ? '⌘K' : 'Ctrl K';
}

function getServerSnapshot(): string {
  return 'Ctrl K';
}

export default function SearchButton() {
  const setSearchOpen = useUiStore((s) => s.setSearchOpen);
  const kbdShortcut = React.useSyncExternalStore(
    emptySubscribe,
    getShortcutSnapshot,
    getServerSnapshot,
  );

  return (
    <button
      type="button"
      aria-label="Search"
      onClick={() => setSearchOpen(true)}
      className="inline-flex size-11 items-center justify-center rounded-pill text-fg hover:bg-surface-2 transition-colors relative lg:w-auto lg:px-3 lg:gap-2 lg:h-10 border border-transparent lg:border-border lg:bg-surface"
    >
      <Search size={20} strokeWidth={1.5} aria-hidden="true" />
      <span className="hidden lg:inline text-body-sm text-fg-muted">Search...</span>
      <kbd className="hidden lg:inline-flex items-center px-1.5 py-0.5 text-caption rounded bg-surface-2 text-fg-muted border border-border font-mono">
        {kbdShortcut}
      </kbd>
    </button>
  );
}
