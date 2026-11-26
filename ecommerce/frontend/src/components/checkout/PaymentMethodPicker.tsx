import * as React from 'react';
import { RadioGroup } from 'radix-ui';
import { RadioCard } from '@/components/ui/RadioCard';
import type { PaymentMethod } from '@/lib/api/types';

export interface PaymentMethodPickerProps {
  methods: PaymentMethod[];
  selectedId: string;
  onChange: (id: string) => void;
  error?: string;
}

export default function PaymentMethodPicker({
  methods,
  selectedId,
  onChange,
  error,
}: PaymentMethodPickerProps) {
  return (
    <div className="space-y-2">
      <RadioGroup.Root
        aria-label="Payment method"
        value={selectedId}
        onValueChange={onChange}
        className="space-y-3"
      >
        {methods.map((method) => (
          <RadioCard
            key={method.id}
            value={method.id}
            title={method.label}
            description={method.description}
            disabled={!method.enabled}
          />
        ))}
      </RadioGroup.Root>
      {error && (
        <p role="alert" className="text-small text-danger">
          {error}
        </p>
      )}
    </div>
  );
}
