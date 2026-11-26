'use client';

import * as React from 'react';
import { useAnnounceStore } from '@/stores/announce-store';

export default function Announcer() {
  const message = useAnnounceStore((s) => s.message);
  const nonce = useAnnounceStore((s) => s.nonce);

  return (
    <div aria-live="polite" aria-atomic="true" className="sr-only" data-testid="announcer">
      <span key={nonce}>{message}</span>
    </div>
  );
}
