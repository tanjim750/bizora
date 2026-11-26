'use client';

import * as React from 'react';
import Image from 'next/image';
import Link from 'next/link';
import { Container } from '@/components/ui/Container';
import { gsap, useGSAP } from '@/lib/motion/gsap';
import { distance, duration, gsapEase, MEDIA_FULL } from '@/lib/motion/tokens';
import type { Category } from '@/lib/api/types';

export interface CategoryTilesProps {
  categories: Category[];
}

export default function CategoryTiles({ categories }: CategoryTilesProps) {
  const sectionRef = React.useRef<HTMLElement>(null);

  useGSAP(
    () => {
      if (!gsap?.matchMedia || !sectionRef.current) return;

      const mm = gsap.matchMedia();

      mm.add(MEDIA_FULL, () => {
        gsap.from('[data-tile]', {
          opacity: 0,
          y: distance.reveal,
          duration: duration.slow,
          ease: gsapEase.out,
          stagger: 0.08,
          scrollTrigger: {
            trigger: sectionRef.current,
            start: 'top 80%',
            once: true,
          },
        });
      });
    },
    { scope: sectionRef },
  );

  return (
    <Container>
      <section ref={sectionRef} aria-labelledby="cat-title" className="py-24">
        <h2 id="cat-title" className="font-display text-display-md text-fg">
          Shop by category
        </h2>

        <ul className="mt-10 grid grid-cols-2 gap-4 lg:grid-cols-4">
          {categories.map((category) => (
            <li key={category.id} data-tile>
              <Link href={`/shop?category=${category.slug}`} className="group block">
                <div className="relative aspect-4/5 overflow-hidden rounded-md bg-surface-2">
                  {category.image && (
                    <Image
                      src={category.image.url}
                      alt={category.image.alt || category.name}
                      fill
                      sizes="(min-width: 1024px) 25vw, 50vw"
                      className="object-cover transition-transform duration-500 ease-out group-hover:scale-[1.04]"
                    />
                  )}
                </div>

                <h3 className="text-title font-display mt-3 text-fg">
                  <span className="relative inline-block">
                    {category.name}
                    <span className="absolute inset-x-0 bottom-0 h-px bg-fg origin-left scale-x-0 group-hover:scale-x-100 transition-transform duration-200" />
                  </span>
                </h3>

                <p className="text-small text-fg-muted mt-0.5">{category.productCount} pieces</p>
              </Link>
            </li>
          ))}
        </ul>
      </section>
    </Container>
  );
}
