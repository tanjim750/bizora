import * as React from 'react';
import { Leaf, RefreshCw, ShieldCheck, Truck, type LucideIcon } from 'lucide-react';
import { Container } from '@/components/ui/Container';
import type { HomeContent } from '@/lib/api/types';

export interface ValueStripProps {
  values: HomeContent['values'];
}

const iconMap: Record<HomeContent['values'][number]['icon'], LucideIcon> = {
  truck: Truck,
  leaf: Leaf,
  refresh: RefreshCw,
  shield: ShieldCheck,
};

export default function ValueStrip({ values }: ValueStripProps) {
  return (
    <section aria-label="Store commitments" className="border-y border-border py-12">
      <Container>
        <ul className="grid grid-cols-2 lg:grid-cols-4 gap-8">
          {values.map((val) => {
            const Icon = iconMap[val.icon];
            return (
              <li key={val.title} className="flex flex-col gap-3">
                {Icon && (
                  <Icon
                    size={24}
                    strokeWidth={1.5}
                    className="text-fg shrink-0"
                    aria-hidden="true"
                  />
                )}
                <div>
                  <h3 className="text-body font-medium text-fg">{val.title}</h3>
                  <p className="text-small text-fg-muted mt-1">{val.body}</p>
                </div>
              </li>
            );
          })}
        </ul>
      </Container>
    </section>
  );
}
