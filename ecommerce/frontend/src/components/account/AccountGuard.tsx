'use client';

import * as React from 'react';
import { usePathname, useRouter } from 'next/navigation';
import { useSessionStore } from '@/stores/session-store';

export default function AccountGuard({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const pathname = usePathname();
  const status = useSessionStore((s) => s.status);

  React.useEffect(() => {
    if (status === 'guest') {
      router.replace(`/account/sign-in?next=${encodeURIComponent(pathname || '/account')}`);
    }
  }, [status, pathname, router]);

  if (status !== 'signed-in') {
    return (
      <div aria-busy="true" className="py-12 max-w-4xl mx-auto px-4 space-y-6">
        <span className="sr-only">Loading your account…</span>
        <div className="w-64 h-8 bg-surface-2 rounded-sm animate-pulse" />
        <div className="w-48 h-4 bg-surface-2 rounded-sm animate-pulse" />
        <div className="w-full h-48 bg-surface-2 rounded-md animate-pulse mt-8" />
      </div>
    );
  }

  return <>{children}</>;
}
