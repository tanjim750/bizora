'use client';

import * as React from 'react';
import { useRouter } from 'next/navigation';
import OrderHistory from '@/components/account/OrderHistory';
import { Button } from '@/components/ui/Button';
import { Container } from '@/components/ui/Container';
import { toUserMessage } from '@/lib/api/errors';
import { formatMonthYear } from '@/lib/format/date';
import { useSessionStore } from '@/stores/session-store';

export default function AccountView() {
  const router = useRouter();
  const user = useSessionStore((s) => s.user);
  const signOut = useSessionStore((s) => s.signOut);

  const [signingOut, setSigningOut] = React.useState<boolean>(false);
  const [error, setError] = React.useState<string | null>(null);

  if (!user) return null;

  const handleSignOut = async () => {
    setSigningOut(true);
    setError(null);
    try {
      await signOut();
      router.push('/');
    } catch (err) {
      setError(toUserMessage(err));
      setSigningOut(false);
    }
  };

  return (
    <Container className="py-12 max-w-4xl mx-auto">
      {/* Profile Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-6 pb-8 border-b border-border">
        <div>
          <h1 className="font-display text-display-lg text-fg">Hello, {user.firstName}</h1>
          <div className="mt-2 text-body text-fg-muted space-y-1">
            <p className="font-medium text-fg">
              {user.firstName} {user.lastName}
            </p>
            <p>{user.email}</p>
            <p>Member since {formatMonthYear(user.createdAt)}</p>
          </div>
        </div>

        <div>
          <Button variant="secondary" onClick={handleSignOut} loading={signingOut}>
            Sign out
          </Button>
        </div>
      </div>

      {error && (
        <div role="alert" className="mt-6 p-4 rounded-md bg-surface-2 text-danger">
          <p>{error}</p>
        </div>
      )}

      {/* Order History */}
      <OrderHistory />
    </Container>
  );
}
