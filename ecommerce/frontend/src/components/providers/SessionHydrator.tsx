'use client';

import * as React from 'react';
import { useSessionStore } from '@/stores/session-store';

export default function SessionHydrator() {
  React.useEffect(() => {
    void useSessionStore.getState().hydrate();
  }, []);

  return null;
}
