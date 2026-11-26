'use client';

import * as React from 'react';
import Image from 'next/image';
import Link from 'next/link';
import { ArrowRight } from 'lucide-react';
import { Container } from '@/components/ui/Container';
import { Reveal } from '@/components/motion/Reveal';
import { gsap, useGSAP } from '@/lib/motion/gsap';
import { MEDIA_FULL } from '@/lib/motion/tokens';
import type { HomeContent } from '@/lib/api/types';

export interface EditorialBandProps {
  editorial: HomeContent['editorial'];
}

export default function EditorialBand({ editorial }: EditorialBandProps) {
  const sectionRef = React.useRef<HTMLElement>(null);
  const imageWrapperRef = React.useRef<HTMLDivElement>(null);

  useGSAP(
    () => {
      if (!gsap?.matchMedia || !imageWrapperRef.current) return;

      const mm = gsap.matchMedia();

      mm.add(MEDIA_FULL, () => {
        const imageWrapper = imageWrapperRef.current;
        if (!imageWrapper) return;

        gsap.fromTo(
          imageWrapper,
          { clipPath: 'inset(10% 10% 10% 10%)' },
          {
            clipPath: 'inset(0% 0% 0% 0%)',
            ease: 'none',
            scrollTrigger: {
              trigger: imageWrapper,
              start: 'top 85%',
              end: 'top 35%',
              scrub: true,
            },
          },
        );
      });
    },
    { scope: sectionRef },
  );

  return (
    <section ref={sectionRef} aria-labelledby="editorial-title" className="py-24">
      <Container>
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-10 items-center">
          {/* Image Well */}
          <div
            ref={imageWrapperRef}
            data-editorial-image
            className="relative aspect-4/5 overflow-hidden rounded-lg bg-surface-2"
          >
            <Image
              src={editorial.image.url}
              alt={editorial.image.alt}
              fill
              sizes="(min-width: 1024px) 50vw, 100vw"
              className="object-cover"
            />
          </div>

          {/* Text Content */}
          <Reveal className="space-y-6">
            <p className="text-label-caps text-fg-muted">{editorial.eyebrow}</p>
            <h2 id="editorial-title" className="font-display text-display-lg text-fg">
              {editorial.headline}
            </h2>
            <div className="space-y-4 text-body-lg text-fg-muted max-w-prose">
              {editorial.body.map((paragraph, index) => (
                <p key={index}>{paragraph}</p>
              ))}
            </div>
            <div className="pt-2">
              <Link
                href={editorial.cta.href}
                className="group inline-flex items-center gap-1.5 text-body font-medium text-fg hover:text-fg-muted transition-colors"
              >
                <span>{editorial.cta.label}</span>
                <ArrowRight
                  className="size-4 transition-transform group-hover:translate-x-1"
                  aria-hidden="true"
                />
              </Link>
            </div>
          </Reveal>
        </div>
      </Container>
    </section>
  );
}
