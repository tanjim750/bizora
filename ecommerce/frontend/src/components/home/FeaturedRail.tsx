'use client';

import * as React from 'react';
import Link from 'next/link';
import { ArrowRight } from 'lucide-react';
import { Container } from '@/components/ui/Container';
import ProductCard from '@/components/product/ProductCard';
import { gsap, useGSAP } from '@/lib/motion/gsap';
import type { ProductSummary } from '@/lib/api/types';

export interface FeaturedRailProps {
  products: ProductSummary[];
}

export default function FeaturedRail({ products }: FeaturedRailProps) {
  const sectionRef = React.useRef<HTMLElement>(null);
  const trackRef = React.useRef<HTMLUListElement>(null);

  useGSAP(
    () => {
      if (!gsap?.matchMedia || !sectionRef.current || !trackRef.current) return;

      const mm = gsap.matchMedia();

      mm.add('(min-width: 1024px) and (prefers-reduced-motion: no-preference)', () => {
        const track = trackRef.current;
        const section = sectionRef.current;
        if (!track || !section) return;

        track.style.overflowX = 'visible';

        gsap.to(track, {
          x: () => -(track.scrollWidth - track.clientWidth),
          ease: 'none',
          scrollTrigger: {
            trigger: section,
            start: 'top top',
            end: () => '+=' + (track.scrollWidth - track.clientWidth),
            pin: true,
            scrub: 0.6,
            invalidateOnRefresh: true,
          },
        });
      });
    },
    { scope: sectionRef },
  );

  return (
    <section ref={sectionRef} aria-labelledby="featured-rail-title" className="py-24">
      <Container>
        <div className="flex items-baseline justify-between mb-10">
          <h2 id="featured-rail-title" className="font-display text-display-md text-fg">
            Most loved
          </h2>
          <Link
            href="/shop?collection=featured"
            className="group inline-flex items-center gap-1 text-body font-medium text-fg hover:text-fg-muted transition-colors"
          >
            <span>Shop all</span>
            <ArrowRight
              className="size-4 transition-transform group-hover:translate-x-0.5"
              aria-hidden="true"
            />
          </Link>
        </div>

        <ul
          ref={trackRef}
          data-rail-track
          className="flex gap-4 overflow-x-auto snap-x snap-mandatory pb-4 lg:overflow-visible"
        >
          {products.map((product) => (
            <li key={product.id} className="w-3/4 shrink-0 snap-start sm:w-2/5 lg:w-1/4">
              <ProductCard product={product} />
            </li>
          ))}
        </ul>
      </Container>
    </section>
  );
}
