'use client';

import * as React from 'react';
import Image from 'next/image';
import Link from 'next/link';
import { Button } from '@/components/ui/Button';
import { Container } from '@/components/ui/Container';
import { gsap, SplitText, useGSAP } from '@/lib/motion/gsap';
import { duration, gsapEase, MEDIA_FULL, MEDIA_REDUCED } from '@/lib/motion/tokens';
import type { HomeContent } from '@/lib/api/types';

export interface HeroProps {
  hero: HomeContent['hero'];
}

export default function Hero({ hero }: HeroProps) {
  const containerRef = React.useRef<HTMLElement>(null);

  useGSAP(
    () => {
      if (!gsap?.matchMedia) return;

      const mm = gsap.matchMedia();

      mm.add(MEDIA_FULL, () => {
        let split: { revert?: () => void; lines?: Element[] } | null = null;
        try {
          if (typeof SplitText !== 'undefined' && SplitText?.create) {
            split = SplitText.create('[data-hero-title]', {
              type: 'lines',
              mask: 'lines',
              linesClass: 'hero-line',
            });
          }
        } catch {
          // In test/unsupported environments
        }

        const tl = gsap.timeline();

        if (split?.lines && split.lines.length > 0) {
          tl.from(split.lines, {
            yPercent: 100,
            duration: duration.hero,
            ease: gsapEase.out,
            stagger: 0.08,
          });
        }

        tl.from(
          '[data-hero-image]',
          {
            scale: 1.08,
            duration: 1.4,
            ease: gsapEase.out,
          },
          0,
        );

        tl.from(
          '[data-hero-eyebrow], [data-hero-sub]',
          {
            opacity: 0,
            y: 12,
            duration: duration.base,
            ease: gsapEase.out,
          },
          0.3,
        );

        tl.from(
          '[data-hero-cta]',
          {
            opacity: 0,
            duration: duration.base,
            ease: gsapEase.out,
          },
          0.6,
        );

        return () => {
          if (split?.revert) {
            split.revert();
          }
        };
      });

      mm.add(MEDIA_REDUCED, () => {
        // Reduced motion: no-op
      });
    },
    { scope: containerRef },
  );

  return (
    <Container>
      <section ref={containerRef} aria-labelledby="hero-title" className="relative -mx-5 md:mx-0">
        {/* Media Wrapper */}
        <div className="relative w-full aspect-4/5 md:aspect-video max-h-224 overflow-hidden md:rounded-lg bg-surface-2">
          <Image
            src={hero.image.url}
            alt={hero.image.alt}
            fill
            priority
            sizes="100vw"
            className="object-cover"
            data-hero-image
          />
        </div>

        {/* Text Panel */}
        <div className="md:absolute md:bottom-8 md:left-8 md:max-w-xl bg-bg p-6 md:p-10 md:rounded-md">
          <p className="text-label-caps text-fg-muted" data-hero-eyebrow>
            {hero.eyebrow}
          </p>
          <h1 id="hero-title" className="font-display text-display-xl" data-hero-title>
            {hero.headline}
          </h1>
          <p className="text-body-lg text-fg-muted mt-4" data-hero-sub>
            {hero.subheadline}
          </p>
          <Button asChild size="lg" className="mt-8" data-hero-cta>
            <Link href={hero.cta.href}>{hero.cta.label}</Link>
          </Button>
        </div>
      </section>
    </Container>
  );
}
