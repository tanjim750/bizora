import type { Money } from '@/lib/api/types';

export function formatMoney(m: Money, locale = 'en-BD'): string {
  const isWhole = m.amount % 100 === 0;
  const digits = isWhole ? 0 : 2;
  return new Intl.NumberFormat(locale, {
    style: 'currency',
    currency: m.currency,
    currencyDisplay: 'narrowSymbol',
    minimumFractionDigits: digits,
    maximumFractionDigits: digits,
  }).format(m.amount / 100);
}

export function toMinor(major: number): number {
  return Math.round(major * 100);
}

export function toMajor(minor: number): number {
  return minor / 100;
}

export function addMoney(a: Money, b: Money): Money {
  if (a.currency !== b.currency) {
    throw new Error(`Cannot add different currencies: ${a.currency} and ${b.currency}`);
  }
  return {
    amount: a.amount + b.amount,
    currency: a.currency,
  };
}

export function multiplyMoney(m: Money, n: number): Money {
  return {
    amount: Math.round(m.amount * n),
    currency: m.currency,
  };
}
