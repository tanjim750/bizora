import type { Metadata } from 'next';
import ConfirmationView from '@/components/order/ConfirmationView';

export const metadata: Metadata = {
  title: 'Order confirmed',
  robots: { index: false },
};

export default async function OrderConfirmationPage({
  params,
  searchParams,
}: {
  params: Promise<{ orderNumber: string }>;
  searchParams: Promise<{ token?: string | string[] }>;
}) {
  const { orderNumber } = await params;
  const { token } = await searchParams;
  return (
    <ConfirmationView
      orderNumber={orderNumber}
      token={typeof token === 'string' ? token : undefined}
    />
  );
}
