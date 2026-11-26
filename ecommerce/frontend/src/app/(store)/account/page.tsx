import type { Metadata } from 'next';
import AccountGuard from '@/components/account/AccountGuard';
import AccountView from '@/components/account/AccountView';

export const metadata: Metadata = {
  title: 'Your account',
  robots: { index: false },
};

export default function AccountPage() {
  return (
    <AccountGuard>
      <AccountView />
    </AccountGuard>
  );
}
