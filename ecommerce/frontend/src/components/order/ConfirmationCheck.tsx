'use client';

import * as React from 'react';
import { useGSAP } from '@gsap/react';
import { gsap } from '@/lib/motion/gsap';
import { gsapEase, MEDIA_FULL } from '@/lib/motion/tokens';

export default function ConfirmationCheck({ className }: { className?: string }) {
  const containerRef = React.useRef<SVGSVGElement>(null);
  const circleRef = React.useRef<SVGCircleElement>(null);
  const pathRef = React.useRef<SVGPathElement>(null);

  useGSAP(
    () => {
      const circle = circleRef.current;
      const path = pathRef.current;
      if (!circle || !path) return;

      const mm = gsap.matchMedia();
      mm.add(MEDIA_FULL, () => {
        const circleLen = circle.getTotalLength ? circle.getTotalLength() : 226.2;
        const pathLen = path.getTotalLength ? path.getTotalLength() : 43;

        gsap.set(circle, {
          strokeDasharray: circleLen,
          strokeDashoffset: circleLen,
        });
        gsap.set(path, {
          strokeDasharray: pathLen,
          strokeDashoffset: pathLen,
        });

        const tl = gsap.timeline();
        tl.to(circle, {
          strokeDashoffset: 0,
          duration: 0.6,
          ease: gsapEase.out,
        });
        tl.to(
          path,
          {
            strokeDashoffset: 0,
            duration: 0.4,
            ease: gsapEase.out,
          },
          '+=0.05',
        );
      });
    },
    { scope: containerRef },
  );

  return (
    <svg
      ref={containerRef}
      viewBox="0 0 80 80"
      className={className ?? 'size-20 text-success'}
      role="img"
      aria-label="Order confirmed"
    >
      <circle
        ref={circleRef}
        cx={40}
        cy={40}
        r={36}
        fill="none"
        stroke="currentColor"
        strokeWidth={3}
      />
      <path
        ref={pathRef}
        d="M24 41 L35 52 L57 29"
        fill="none"
        stroke="currentColor"
        strokeWidth={3}
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}
