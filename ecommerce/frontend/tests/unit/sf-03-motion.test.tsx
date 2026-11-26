import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';

let mockReduced = false;

vi.mock('motion/react', async (importOriginal) => {
  const actual = await importOriginal<typeof import('motion/react')>();
  return {
    ...actual,
    useReducedMotion: () => mockReduced,
  };
});

import {
  duration,
  ease,
  gsapEase,
  spring,
  stagger,
  distance,
  staggerDelay,
  MEDIA_REDUCED,
  MEDIA_FULL,
} from '@/lib/motion/tokens';
import { usePrefersReducedMotion } from '@/lib/motion/use-reduced-motion';
import { Reveal } from '@/components/motion/Reveal';
import { Providers } from '@/components/providers/Providers';
import { gsap, ScrollTrigger, SplitText, useGSAP } from '@/lib/motion/gsap';

describe('SF-03 Motion Foundation', () => {
  beforeEach(() => {
    mockReduced = false;
  });

  it('defines exact motion tokens adhering to design principles', () => {
    expect(duration.instant).toBe(0.12);
    expect(duration.fast).toBe(0.2);
    expect(duration.base).toBe(0.32);
    expect(duration.slow).toBe(0.56);
    expect(duration.hero).toBe(0.9);

    for (const [key, val] of Object.entries(duration)) {
      expect(val, `duration.${key} must not exceed 0.9s`).toBeLessThanOrEqual(0.9);
    }

    expect(ease.out).toEqual([0.16, 1, 0.3, 1]);
    expect(ease.inOut).toEqual([0.65, 0, 0.35, 1]);
    expect(ease.in).toEqual([0.7, 0, 0.84, 0]);

    expect(gsapEase.out).toBe('expo.out');
    expect(gsapEase.inOut).toBe('power3.inOut');
    expect(gsapEase.in).toBe('power3.in');

    expect(spring.snappy.stiffness).toBe(420);
    expect(spring.snappy.damping).toBe(34);
    expect(spring.snappy.mass).toBe(0.9);
    expect(spring.soft.stiffness).toBe(220);
    expect(spring.soft.damping).toBe(28);

    expect(stagger.list).toBe(0.04);
    expect(stagger.maxItems).toBe(12);

    expect(distance.reveal).toBe(24);
    expect(distance.page).toBe(12);

    expect(MEDIA_REDUCED).toBe('(prefers-reduced-motion: reduce)');
    expect(MEDIA_FULL).toBe('(prefers-reduced-motion: no-preference)');
  });

  it('calculates staggerDelay correctly with cap', () => {
    expect(staggerDelay(0)).toBe(0);
    expect(staggerDelay(3)).toBeCloseTo(0.12);
    // index 50 should be capped at index 11 (maxItems 12 -> 11 * 0.04 = 0.44)
    expect(staggerDelay(50)).toBeCloseTo(0.44);
  });

  it('exports usePrefersReducedMotion hook and tests return value', () => {
    expect(typeof usePrefersReducedMotion).toBe('function');
    function TestComponent() {
      const prefersReduced = usePrefersReducedMotion();
      return <div data-testid="reduced">{String(prefersReduced)}</div>;
    }
    const { unmount } = render(<TestComponent />);
    expect(screen.getByTestId('reduced')).toHaveTextContent('false');
    unmount();

    mockReduced = true;
    render(<TestComponent />);
    expect(screen.getByTestId('reduced')).toHaveTextContent('true');
  });

  it('renders Reveal component displaying children and supports custom elements', () => {
    const { rerender } = render(
      <Reveal as="section" className="test-reveal" delay={0.1}>
        <p>Hello Section</p>
      </Reveal>,
    );
    const p = screen.getByText('Hello Section');
    expect(p).toBeInTheDocument();
    expect(p.closest('section')).toHaveClass('test-reveal');

    rerender(
      <Reveal as="li" className="item-class">
        <span>List Item</span>
      </Reveal>,
    );
    const span = screen.getByText('List Item');
    expect(span.closest('li')).toHaveClass('item-class');
  });

  it('renders Reveal as plain component under reduced motion without animation style', () => {
    mockReduced = true;

    render(
      <Reveal as="div" className="reduced-class">
        <p>Reduced Content</p>
      </Reveal>,
    );

    const content = screen.getByText('Reduced Content');
    expect(content).toBeInTheDocument();
    expect(content.parentElement).toHaveClass('reduced-class');
    // It should render plain div without animation style attributes
    expect(content.parentElement).not.toHaveStyle({ opacity: '0' });
  });

  it('renders Providers with ThemeProvider and MotionConfig', () => {
    render(
      <Providers>
        <span data-testid="provider-child">Inside Providers</span>
      </Providers>,
    );
    expect(screen.getByTestId('provider-child')).toHaveTextContent('Inside Providers');
  });

  it('exports registered GSAP tools and hook', () => {
    expect(gsap).toBeDefined();
    expect(ScrollTrigger).toBeDefined();
    expect(SplitText).toBeDefined();
    expect(typeof useGSAP).toBe('function');
  });
});
