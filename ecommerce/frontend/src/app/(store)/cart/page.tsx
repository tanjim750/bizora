import { serverApi } from '@/lib/api/server';
import CartPageView from '@/components/cart/CartPageView';

export const metadata = {
  title: 'Your cart',
};

export default async function CartPage() {
  const store = await serverApi.store.get();
  const codAvailable = store.paymentMethods.some((m) => m.id === 'cod' && m.enabled);

  return (
    <CartPageView
      freeShippingThreshold={store.freeShippingThreshold}
      codAvailable={codAvailable}
    />
  );
}
