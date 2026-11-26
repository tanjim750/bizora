import * as React from 'react';
import { RadioGroup } from 'radix-ui';
import { RadioCard } from '@/components/ui/RadioCard';
import { formatMoney } from '@/lib/format/money';
import type { ShippingMethod, Quote } from '@/lib/api/types';

export interface ShippingMethodPickerProps {
  methods: ShippingMethod[];
  selectedId: string;
  quote: Quote | null;
  onChange: (id: string) => void;
  error?: string;
}

export default function ShippingMethodPicker({
  methods,
  selectedId,
  quote,
  onChange,
  error,
}: ShippingMethodPickerProps) {
  return (
    <div className="space-y-2">
      <RadioGroup.Root
        aria-label="Delivery method"
        value={selectedId}
        onValueChange={onChange}
        className="space-y-3"
      >
        {methods.map((method) => {
          const isQuoteMethod = quote?.shippingMethodId === method.id;
          const isFree = isQuoteMethod && quote?.freeShippingApplied;
          const aside = isFree ? 'Free' : formatMoney(method.price);

          return (
            <RadioCard
              key={method.id}
              value={method.id}
              title={method.label}
              description={method.description}
              aside={aside}
            />
          );
        })}
      </RadioGroup.Root>
      {error && (
        <p role="alert" className="text-small text-danger">
          {error}
        </p>
      )}
    </div>
  );
}
