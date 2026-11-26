import type { Metadata } from 'next';
import AccountGuard from '@/components/account/AccountGuard';
import OrderDetail from '@/components/account/OrderDetail';

export const metadata: Metadata = {
  title: 'Order details',
  robots: { index: false },
};

export default async function OrderDetailPage({
  params,
}: {
  params: Promise<{ orderNumber: string }>;
}) {
  const { orderNumber } = await params;
  return (
    <AccountGuard>
      <OrderDetail orderNumber={orderNumber} />
    </AccountGuard>
  );
}
