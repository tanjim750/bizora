import type { Metadata } from 'next';
import { fraunces, instrumentSans, jetbrainsMono } from './fonts';
import { Providers } from '@/components/providers/Providers';
import './globals.css';

export const metadata: Metadata = {
  title: 'Aurelo',
};

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
