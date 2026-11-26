import * as React from 'react';
import { serverApi } from '@/lib/api/server';
import SkipLink from '@/components/layout/SkipLink';
import Header from '@/components/layout/Header';
import Footer from '@/components/layout/Footer';
import CartDrawer from '@/components/cart/CartDrawer';

export default async function StoreLayout({ children }: { children: React.ReactNode }) {
  const [store, categories] = await Promise.all([
    serverApi.store.get(),
    serverApi.catalog.listCategories(),
  ]);

  return (
    <>
      <SkipLink />
      <Header storeName={store.name} categories={categories} />
      <main id="main" tabIndex={-1} className="min-h-dvh outline-none">
        {children}
      </main>
      <Footer store={store} categories={categories} />
      <CartDrawer freeShippingThreshold={store.freeShippingThreshold} />
    </>
  );
}
