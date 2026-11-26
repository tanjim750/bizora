'use client';

import { gsap } from './gsap';
import { duration, gsapEase } from './tokens';

export async function flyToCart(
  source: HTMLElement | null,
  options: { reduced: boolean },
): Promise<void> {
  if (typeof document === 'undefined') return;

  const target = document.getElementById('header-cart-button');
  if (!source || !target) return;

  if (options.reduced) {
    return new Promise<void>((resolve) => {
      gsap.fromTo(
        target,
        { opacity: 0.4 },
        {
          opacity: 1,
          duration: duration.fast,
          onComplete: () => resolve(),
        },
      );
    });
  }

  let clone: HTMLElement | null = null;
  try {
    const srcRect = source.getBoundingClientRect();
    const tgtRect = target.getBoundingClientRect();

    clone = source.cloneNode(true) as HTMLElement;
    Object.assign(clone.style, {
      position: 'fixed',
      left: `${srcRect.left}px`,
      top: `${srcRect.top}px`,
      width: `${srcRect.width}px`,
      height: `${srcRect.height}px`,
      pointerEvents: 'none',
      zIndex: '70',
      borderRadius: '12px',
      overflow: 'hidden',
      margin: '0',
    });

    document.body.appendChild(clone);

    const srcCentreX = srcRect.left + srcRect.width / 2;
    const srcCentreY = srcRect.top + srcRect.height / 2;
    const tgtCentreX = tgtRect.left + tgtRect.width / 2;
    const tgtCentreY = tgtRect.top + tgtRect.height / 2;

    const dx = tgtCentreX - srcCentreX;
    const dy = tgtCentreY - srcCentreY;

    return new Promise<void>((resolve) => {
      const tl = gsap.timeline({
        onComplete: () => {
          if (clone && clone.parentNode) {
            clone.parentNode.removeChild(clone);
            clone = null;
          }
          gsap.fromTo(
            target,
            { scale: 1 },
            {
              scale: 1.18,
              duration: 0.15,
              yoyo: true,
              repeat: 1,
              ease: 'power2.out',
            },
          );
          resolve();
        },
      });

      tl.to(
        clone,
        {
          x: dx,
          duration: 0.7,
          ease: gsapEase.inOut,
        },
        0,
      ).to(
        clone,
        {
          y: dy,
          scale: 0.12,
          opacity: 0.6,
          duration: 0.7,
          ease: 'power2.in',
        },
        0,
      );
    });
  } catch {
    if (clone && clone.parentNode) {
      clone.parentNode.removeChild(clone);
    }
  }
}
