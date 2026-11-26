import { serverApi } from '@/lib/api/server';
import CheckoutForm from '@/components/checkout/CheckoutForm';

export const metadata = {
  title: 'Checkout',
};

export default async function CheckoutPage() {
  const store = await serverApi.store.get();

  return <CheckoutForm store={store} />;
}
