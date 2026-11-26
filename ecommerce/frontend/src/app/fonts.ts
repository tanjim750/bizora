import { Fraunces, Instrument_Sans, JetBrains_Mono } from 'next/font/google';

export const fraunces = Fraunces({
  subsets: ['latin'],
  axes: ['opsz'],
  variable: '--font-fraunces',
  display: 'swap',
});

export const instrumentSans = Instrument_Sans({
  subsets: ['latin'],
  variable: '--font-instrument',
  display: 'swap',
});

export const jetbrainsMono = JetBrains_Mono({
  subsets: ['latin'],
  variable: '--font-jetbrains',
  display: 'swap',
});
