'use client';

import * as React from 'react';
import Link from 'next/link';
import { User } from 'lucide-react';
import { useSessionStore } from '@/stores/session-store';

export default function AccountLink() {
  const status = useSessionStore((s) => s.status);
  const href = status === 'signed-in' ? '/account' : '/account/sign-in';

  return (
    <Link
      href={href}
      aria-label="Account"
      className="inline-flex size-11 items-center justify-center rounded-pill text-fg hover:bg-surface-2 transition-colors"
    >
      <User size={20} strokeWidth={1.5} aria-hidden="true" />
    </Link>
  );
}
