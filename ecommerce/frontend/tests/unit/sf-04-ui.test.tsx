import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import * as React from 'react';
import { RadioGroup } from 'radix-ui';

import { cn } from '@/lib/cn';
import {
  Button,
  IconButton,
  Input,
  Field,
  Select,
  Checkbox,
  RadioCard,
  Badge,
  Skeleton,
  Price,
  Spinner,
  VisuallyHidden,
  Container,
} from '@/components/ui';

describe('SF-04 UI Primitives', () => {
  it('merges class names and correctly resolves custom font-size and color utilities', () => {
    expect(cn('p-2', 'p-4')).toBe('p-4');
    expect(cn('text-fg', false && 'hidden', 'bg-bg')).toBe('text-fg bg-bg');

    // Regression check: custom font sizes must NOT collide with text colors
    const mergedButton = cn('bg-accent text-accent-fg', 'px-5 text-body');
    expect(mergedButton).toContain('text-accent-fg');
    expect(mergedButton).toContain('text-body');

    // Regression check: Badge text-label-caps must not be stripped by variant text colors
    const mergedBadge = cn('text-label-caps', 'text-success');
    expect(mergedBadge).toContain('text-label-caps');
    expect(mergedBadge).toContain('text-success');
  });

  it('renders Button with variants and loading state', () => {
    const { rerender } = render(<Button>Save</Button>);
    const button = screen.getByRole('button', { name: 'Save' });
    expect(button).toBeInTheDocument();
    expect(button).toHaveAttribute('type', 'button');
    expect(button).toHaveClass('bg-accent', 'text-accent-fg');

    rerender(<Button loading>Save</Button>);
    const loadingBtn = screen.getByRole('button', { name: 'Save' });
    expect(loadingBtn).toBeDisabled();
    expect(loadingBtn).toHaveAttribute('aria-busy', 'true');

    rerender(
      <Button variant="link" size="lg">
        Link Button
      </Button>,
    );
    const linkBtn = screen.getByRole('button', { name: 'Link Button' });
    expect(linkBtn).toHaveClass('min-h-0', 'text-accent');
  });

  it('renders Button asChild as a link', () => {
    render(
      <Button asChild>
        <a href="/shop">Shop</a>
      </Button>,
    );
    const link = screen.getByRole('link', { name: 'Shop' });
    expect(link).toBeInTheDocument();
    expect(link).toHaveAttribute('href', '/shop');
    expect(screen.queryByRole('button')).not.toBeInTheDocument();
  });

  it('renders IconButton with required aria-label', () => {
    render(
      <IconButton aria-label="Close dialog">
        <span>X</span>
      </IconButton>,
    );
    const btn = screen.getByRole('button', { name: 'Close dialog' });
    expect(btn).toBeInTheDocument();
    expect(btn).toHaveClass('size-11');
  });

  it('renders Spinner with role status or decorative aria-hidden', () => {
    const { rerender } = render(<Spinner />);
    expect(screen.getByRole('status', { name: 'Loading' })).toBeInTheDocument();

    rerender(<Spinner decorative data-testid="spinner-dec" />);
    const spinner = screen.getByTestId('spinner-dec');
    expect(spinner).toHaveAttribute('aria-hidden', 'true');
    expect(spinner).not.toHaveAttribute('role');
  });

  it('renders Field with error and wires accessible attributes to Input', () => {
    render(
      <Field id="email" label="Email" hint="Your work email" error="Enter a valid email address.">
        {(a) => <Input {...a} />}
      </Field>,
    );

    const input = screen.getByLabelText('Email');
    expect(input).toHaveAttribute('aria-invalid', 'true');
    expect(input.getAttribute('aria-describedby')).toContain('email-hint');
    expect(input.getAttribute('aria-describedby')).toContain('email-error');
    expect(screen.getByText('Your work email')).toBeInTheDocument();
    expect(screen.getByText('Enter a valid email address.')).toBeInTheDocument();
  });

  it('renders Field with optional label hint', () => {
    render(
      <Field id="line2" label="Apartment" optional>
        {(a) => <Input {...a} />}
      </Field>,
    );
    expect(screen.getByText('Apartment (optional)')).toBeInTheDocument();
  });

  it('renders Select with options and Chevron icon', () => {
    render(
      <Select defaultValue="one" aria-label="Choose number">
        <option value="one">One</option>
        <option value="two">Two</option>
      </Select>,
    );
    const select = screen.getByRole('combobox', { name: 'Choose number' });
    expect(select).toBeInTheDocument();
    expect(select).toHaveValue('one');
  });

  it('renders Checkbox with visible label and handles toggle', async () => {
    const user = userEvent.setup();
    const onCheckedChange = vi.fn();

    render(
      <Checkbox
        id="terms"
        label="Accept terms"
        checked={false}
        onCheckedChange={onCheckedChange}
      />,
    );

    const checkbox = screen.getByRole('checkbox', { name: 'Accept terms' });
    expect(checkbox).toBeInTheDocument();
    expect(checkbox).not.toBeChecked();

    await user.click(checkbox);
    expect(onCheckedChange).toHaveBeenCalledWith(true);
  });

  it('renders Price with compareAtFormatted and no aria-label on wrapper', () => {
    const { container, rerender } = render(
      <Price formatted="৳5,400" compareAtFormatted="৳6,200" />,
    );
    expect(screen.getByText('Sale price ৳5,400, was ৳6,200')).toBeInTheDocument();
    const wrapper = container.firstElementChild;
    expect(wrapper).not.toHaveAttribute('aria-label');

    rerender(<Price formatted="৳5,400" />);
    expect(screen.getByText('৳5,400')).toHaveClass('tabular-nums', 'text-fg');
  });

  it('renders Badge with variants', () => {
    const { rerender } = render(<Badge variant="success">In stock</Badge>);
    expect(screen.getByText('In stock')).toHaveClass('text-label-caps', 'text-success');

    rerender(<Badge variant="accent">Sale</Badge>);
    expect(screen.getByText('Sale')).toHaveClass('bg-accent', 'text-accent-fg');
  });

  it('renders Skeleton with pulse animation', () => {
    const { container } = render(<Skeleton className="h-6 w-32" />);
    const el = container.firstElementChild;
    expect(el).toHaveAttribute('aria-hidden', 'true');
    expect(el).toHaveClass('bg-surface-2', 'h-6', 'w-32');
  });

  it('renders VisuallyHidden and Container primitives', () => {
    render(
      <Container as="section" className="test-container">
        <VisuallyHidden>Hidden Notice</VisuallyHidden>
        <p>Visible Content</p>
      </Container>,
    );

    expect(screen.getByText('Hidden Notice')).toHaveClass('sr-only');
    expect(screen.getByText('Visible Content').closest('section')).toHaveClass(
      'max-w-360',
      'test-container',
    );
  });

  it('renders RadioCard inside RadioGroup.Root with accessible name', () => {
    render(
      <RadioGroup.Root defaultValue="card">
        <RadioCard value="card" title="Card payment" description="Coming soon." disabled />
      </RadioGroup.Root>,
    );
    const radio = screen.getByRole('radio', { name: 'Card payment' });
    expect(radio).toBeInTheDocument();
    expect(radio).toBeDisabled();
    expect(screen.getByText('Coming soon.')).toBeInTheDocument();
  });

  it('exports all 13 primitives from @/components/ui', () => {
    expect(Button).toBeDefined();
    expect(IconButton).toBeDefined();
    expect(Input).toBeDefined();
    expect(Field).toBeDefined();
    expect(Select).toBeDefined();
    expect(Checkbox).toBeDefined();
    expect(RadioCard).toBeDefined();
    expect(Badge).toBeDefined();
    expect(Skeleton).toBeDefined();
    expect(Price).toBeDefined();
    expect(Spinner).toBeDefined();
    expect(VisuallyHidden).toBeDefined();
    expect(Container).toBeDefined();
  });
});
