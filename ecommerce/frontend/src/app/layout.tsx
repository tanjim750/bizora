import type { Metadata } from 'next';
import { fraunces, instrumentSans, jetbrainsMono } from './fonts';
import { Providers } from '@/components/providers/Providers';
import { serverApi } from '@/lib/api/server';
import './globals.css';

export async function generateMetadata(): Promise<Metadata> {
  const store = await serverApi.store.get();
  return {
    title: {
      default: `${store.name} — ${store.tagline}`,
      template: `%s — ${store.name}`,
    },
    description: store.tagline,
    metadataBase: new URL(process.env.NEXT_PUBLIC_SITE_URL ?? 'http://localhost:3000'),
  };
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html
      lang="en"
      suppressHydrationWarning
      className={`${fraunces.variable} ${instrumentSans.variable} ${jetbrainsMono.variable}`}
    >
      <body className="min-h-dvh bg-bg text-fg font-sans antialiased">
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
