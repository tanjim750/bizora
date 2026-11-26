'use client';

import * as React from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { useCartStore } from '@/stores/cart-store';
import { useSessionStore } from '@/stores/session-store';
import { browserApi } from '@/lib/api/browser';
import { isApiError, toUserMessage } from '@/lib/api/errors';
import { formatMoney } from '@/lib/format/money';
import {
  CHECKOUT_FIELDS,
  emptyCheckoutValues,
  validateCheckout,
  validateField,
  toPlaceOrderBody,
  mapApiFieldErrors,
  type CheckoutFormValues,
} from '@/lib/checkout/validation';
import { createAttemptKeys } from '@/lib/checkout/idempotency';
import { Container } from '@/components/ui/Container';
import { Field } from '@/components/ui/Field';
import { Input } from '@/components/ui/Input';
import { Select } from '@/components/ui/Select';
import { Button } from '@/components/ui/Button';
import { Skeleton } from '@/components/ui/Skeleton';
import ShippingMethodPicker from './ShippingMethodPicker';
import PaymentMethodPicker from './PaymentMethodPicker';
import OrderSummary from './OrderSummary';
import type { StoreConfig, Quote } from '@/lib/api/types';

export interface CheckoutFormProps {
  store: StoreConfig;
}

export default function CheckoutForm({ store }: CheckoutFormProps) {
  const router = useRouter();
  const cart = useCartStore((s) => s.cart);
  const cartStatus = useCartStore((s) => s.status);
  const sessionUser = useSessionStore((s) => s.user);
  const sessionStatus = useSessionStore((s) => s.status);

  const [values, setValues] = React.useState<CheckoutFormValues>(() =>
    emptyCheckoutValues(store, sessionUser?.email ?? ''),
  );
  const [errors, setErrors] = React.useState<Partial<Record<keyof CheckoutFormValues, string>>>({});
  const [quote, setQuote] = React.useState<Quote | null>(null);
  const [quoteStatus, setQuoteStatus] = React.useState<'loading' | 'ready' | 'error'>('loading');
  const [submitting, setSubmitting] = React.useState(false);
  const [mobileSummaryOpen, setMobileSummaryOpen] = React.useState(false);
  const [banner, setBanner] = React.useState<null | {
    kind: 'price' | 'stock' | 'network' | 'error';
    message: string;
    lines?: string[];
  }>(null);

  const keys = React.useRef(createAttemptKeys());
  const summaryRef = React.useRef<HTMLDivElement>(null);

  // Cart empty guard
  React.useEffect(() => {
    if (cartStatus === 'ready' && (!cart || cart.lines.length === 0)) {
      router.replace('/cart');
    }
  }, [cartStatus, cart, router]);

  // Sync user email if it becomes available
  const userEmail = sessionUser?.email;
  const [prevUserEmail, setPrevUserEmail] = React.useState(userEmail);
  if (userEmail && userEmail !== prevUserEmail) {
    setPrevUserEmail(userEmail);
    if (!values.email) {
      setValues((prev) => ({ ...prev, email: userEmail }));
    }
  }

  const shippingMethodId = values.shippingMethodId;
  const cartUpdatedAt = cart?.updatedAt;

  // Fetch quote
  const fetchQuote = React.useCallback(async () => {
    if (!cart || cart.lines.length === 0) return;
    setQuoteStatus('loading');
    try {
      const q = await browserApi.checkout.quote(shippingMethodId);
      setQuote(q);
      setQuoteStatus('ready');
    } catch (err) {
      if (isApiError(err) && err.code === 'CART_EMPTY') {
        router.replace('/cart');
        return;
      }
      setQuoteStatus('error');
    }
  }, [cart, shippingMethodId, router]);

  React.useEffect(() => {
    if (cart && cart.lines.length > 0) {
      void Promise.resolve().then(() => {
        fetchQuote();
      });
    }
  }, [cart, shippingMethodId, cartUpdatedAt, fetchQuote]);

  const handleFieldChange = (name: keyof CheckoutFormValues, value: string) => {
    setValues((prev) => ({ ...prev, [name]: value }));
    if (errors[name]) {
      setErrors((prev) => {
        const next = { ...prev };
        delete next[name];
        return next;
      });
    }
  };

  const handleBlur = (name: keyof CheckoutFormValues) => {
    const err = validateField(name, values, store);
    setErrors((prev) => ({ ...prev, [name]: err }));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setBanner(null);

    const result = validateCheckout(values, store);
    if (!result.ok) {
      setErrors(result.errors);
      summaryRef.current?.focus();
      return;
    }

    if (!quote) return;

    setSubmitting(true);

    try {
      const body = toPlaceOrderBody(result.body, quote.total);
      const attemptKey = keys.current.current();
      const res = await browserApi.checkout.placeOrder(body, attemptKey);

      useCartStore.getState().reset();
      router.push(
        `/order-confirmation/${res.order.number}?token=${encodeURIComponent(res.confirmationToken)}`,
      );
    } catch (err) {
      setSubmitting(false);

      if (isApiError(err)) {
        if (err.code === 'VALIDATION_FAILED') {
          const detailsObj =
            err.details && typeof err.details === 'object'
              ? (err.details as Record<string, unknown>)
              : null;
          const rawFields = (err.fields ?? detailsObj?.fields) as
            | Record<string, string[]>
            | null
            | undefined;
          const mapped = mapApiFieldErrors(rawFields);
          setErrors(mapped);
          summaryRef.current?.focus();
          keys.current.renew();
        } else if (err.code === 'PRICE_CHANGED') {
          const detailsObj =
            err.details && typeof err.details === 'object'
              ? (err.details as Record<string, unknown>)
              : null;
          const fieldsObj =
            err.fields && typeof err.fields === 'object'
              ? (err.fields as Record<string, unknown>)
              : null;
          const newQuote = (detailsObj?.quote ?? fieldsObj?.quote) as Quote | undefined;
          if (newQuote) {
            setQuote(newQuote);
          }
          setBanner({
            kind: 'price',
            message: 'Prices changed since you started checkout. Please review the new total.',
          });
          keys.current.renew();
        } else if (err.code === 'OUT_OF_STOCK') {
          const detailsObj =
            err.details && typeof err.details === 'object'
              ? (err.details as Record<string, unknown>)
              : null;
          const fieldsObj =
            err.fields && typeof err.fields === 'object'
              ? (err.fields as Record<string, unknown>)
              : null;
          const rawLines = (detailsObj?.lines ?? fieldsObj?.lines) as
            Array<{ lineId?: string }> | undefined;
          const lineNames = (rawLines ?? []).map((l: { lineId?: string }) => {
            const line = cart?.lines.find((cl) => cl.id === l.lineId);
            return line?.productName ?? 'Item';
          });
          setBanner({
            kind: 'stock',
            message: 'Some items are no longer available.',
            lines: lineNames,
          });
          await useCartStore.getState().hydrate();
          keys.current.renew();
        } else if (err.code === 'CART_EMPTY') {
          router.replace('/cart');
        } else if (err.code === 'SHIPPING_METHOD_UNAVAILABLE') {
          setErrors((prev) => ({
            ...prev,
            shippingMethodId: 'Choose a delivery method.',
          }));
          keys.current.renew();
        } else if (err.code === 'PAYMENT_METHOD_UNAVAILABLE') {
          setErrors((prev) => ({
            ...prev,
            paymentMethodId: 'Choose a payment method.',
          }));
          keys.current.renew();
        } else if (err.code === 'IDEMPOTENCY_CONFLICT') {
          keys.current.renew();
          setBanner({ kind: 'error', message: toUserMessage(err) });
        } else if (err.code === 'NETWORK_ERROR') {
          setBanner({
            kind: 'network',
            message: 'You seem to be offline. Your order was not placed. Try again.',
          });
          // key is NOT renewed on network error
        } else {
          setBanner({ kind: 'error', message: toUserMessage(err) });
        }
      } else {
        setBanner({ kind: 'error', message: toUserMessage(err) });
      }
    }
  };

  // Skeleton loading while cart is not ready
  if (cartStatus !== 'ready' && !cart) {
    return (
      <Container className="py-10">
        <div className="lg:grid lg:grid-cols-12 lg:gap-12">
          <div className="lg:col-span-7 space-y-6">
            <Skeleton className="h-40 w-full rounded-lg" />
            <Skeleton className="h-60 w-full rounded-lg" />
          </div>
          <div className="lg:col-span-5 mt-8 lg:mt-0">
            <Skeleton className="h-80 w-full rounded-lg" />
          </div>
        </div>
      </Container>
    );
  }

  if (!cart) return null;

  const totalStr = quote ? formatMoney(quote.total) : formatMoney(cart.subtotal);
  const hasErrors = Object.keys(errors).length > 0;

  return (
    <div>
      {/* Mobile summary accordion */}
      <div className="lg:hidden border-b border-border bg-surface-2 p-4">
        <button
          type="button"
          aria-expanded={mobileSummaryOpen}
          onClick={() => setMobileSummaryOpen((prev) => !prev)}
          className="flex w-full items-center justify-between text-body font-medium text-fg"
        >
          <span>
            {mobileSummaryOpen
              ? `Hide order summary ${totalStr}`
              : `Show order summary ${totalStr}`}
          </span>
          <span className="text-small text-accent underline">
            {mobileSummaryOpen ? 'Hide' : 'Show'}
          </span>
        </button>

        {mobileSummaryOpen && (
          <div className="mt-4">
            <OrderSummary
              cart={cart}
              quote={quote}
              status={quoteStatus}
              taxLabel={store.taxLabel}
              onRetry={fetchQuote}
            />
          </div>
        )}
      </div>

      <Container className="py-10 lg:grid lg:grid-cols-12 lg:gap-12 items-start">
        <div className="lg:col-span-7 space-y-8">
          {/* Banner alerts */}
          {banner && (
            <div
              role="alert"
              className={
                banner.kind === 'price' || banner.kind === 'stock'
                  ? 'border border-warning bg-warning/10 text-warning rounded-md p-4 space-y-2'
                  : 'border border-danger bg-danger/10 text-danger rounded-md p-4 space-y-2'
              }
            >
              <p className="font-medium text-body">{banner.message}</p>
              {banner.lines && banner.lines.length > 0 && (
                <ul className="list-disc pl-5 text-small">
                  {banner.lines.map((name, i) => (
                    <li key={i}>{name}</li>
                  ))}
                </ul>
              )}
              {banner.kind === 'stock' && (
                <p className="text-small">
                  <Link href="/cart" className="underline font-medium">
                    Edit cart
                  </Link>
                </p>
              )}
            </div>
          )}

          {/* Error Summary */}
          {hasErrors && (
            <div
              role="alert"
              tabIndex={-1}
              ref={summaryRef}
              className="rounded-md border border-danger/30 bg-danger/10 p-4 text-small text-danger outline-none space-y-2"
            >
              <p className="font-semibold">Please fix these fields:</p>
              <ul className="list-disc pl-5 space-y-1">
                {CHECKOUT_FIELDS.filter((k) => errors[k]).map((k) => (
                  <li key={k}>
                    <a href={`#field-${k}`} className="underline hover:opacity-80">
                      {errors[k]}
                    </a>
                  </li>
                ))}
              </ul>
            </div>
          )}

          <form noValidate onSubmit={handleSubmit}>
            <fieldset disabled={submitting} className="space-y-10">
              {/* 1. Contact */}
              <section aria-labelledby="section-contact" className="space-y-4">
                <h2 id="section-contact" className="text-title font-semibold text-fg">
                  1. Contact
                </h2>

                {sessionStatus === 'signed-in' ? (
                  <p className="text-small text-fg-muted">
                    Signed in as {sessionUser?.email ?? values.email}
                  </p>
                ) : (
                  <p className="text-small text-fg-muted">
                    Have an account?{' '}
                    <Link
                      href="/account/sign-in?next=/checkout"
                      className="text-accent underline font-medium hover:text-accent/80"
                    >
                      Sign in
                    </Link>
                  </p>
                )}

                <Field id="field-email" label="Email" error={errors.email}>
                  {(aria) => (
                    <Input
                      {...aria}
                      type="email"
                      autoComplete="email"
                      value={values.email}
                      onChange={(e) => handleFieldChange('email', e.target.value)}
                      onBlur={() => handleBlur('email')}
                    />
                  )}
                </Field>

                <Field id="field-phone" label="Phone" error={errors.phone}>
                  {(aria) => (
                    <Input
                      {...aria}
                      type="tel"
                      autoComplete="tel"
                      value={values.phone}
                      onChange={(e) => handleFieldChange('phone', e.target.value)}
                      onBlur={() => handleBlur('phone')}
                    />
                  )}
                </Field>
              </section>

              {/* 2. Delivery address */}
              <section
                aria-labelledby="section-delivery"
                className="space-y-4 pt-6 border-t border-border"
              >
                <h2 id="section-delivery" className="text-title font-semibold text-fg">
                  2. Delivery address
                </h2>

                <div className="grid grid-cols-2 gap-4">
                  <Field id="field-firstName" label="First name" error={errors.firstName}>
                    {(aria) => (
                      <Input
                        {...aria}
                        type="text"
                        autoComplete="given-name"
                        value={values.firstName}
                        onChange={(e) => handleFieldChange('firstName', e.target.value)}
                        onBlur={() => handleBlur('firstName')}
                      />
                    )}
                  </Field>

                  <Field id="field-lastName" label="Last name" error={errors.lastName}>
                    {(aria) => (
                      <Input
                        {...aria}
                        type="text"
                        autoComplete="family-name"
                        value={values.lastName}
                        onChange={(e) => handleFieldChange('lastName', e.target.value)}
                        onBlur={() => handleBlur('lastName')}
                      />
                    )}
                  </Field>
                </div>

                <Field id="field-line1" label="Address" error={errors.line1}>
                  {(aria) => (
                    <Input
                      {...aria}
                      type="text"
                      autoComplete="address-line1"
                      value={values.line1}
                      onChange={(e) => handleFieldChange('line1', e.target.value)}
                      onBlur={() => handleBlur('line1')}
                    />
                  )}
                </Field>

                <Field
                  id="field-line2"
                  label="Apartment, suite, etc."
                  optional
                  error={errors.line2}
                >
                  {(aria) => (
                    <Input
                      {...aria}
                      type="text"
                      autoComplete="address-line2"
                      value={values.line2}
                      onChange={(e) => handleFieldChange('line2', e.target.value)}
                      onBlur={() => handleBlur('line2')}
                    />
                  )}
                </Field>

                <div className="grid grid-cols-2 gap-4">
                  <Field id="field-city" label="City" error={errors.city}>
                    {(aria) => (
                      <Input
                        {...aria}
                        type="text"
                        autoComplete="address-level2"
                        value={values.city}
                        onChange={(e) => handleFieldChange('city', e.target.value)}
                        onBlur={() => handleBlur('city')}
                      />
                    )}
                  </Field>

                  <Field id="field-postalCode" label="Postal code" error={errors.postalCode}>
                    {(aria) => (
                      <Input
                        {...aria}
                        type="text"
                        autoComplete="postal-code"
                        value={values.postalCode}
                        onChange={(e) => handleFieldChange('postalCode', e.target.value)}
                        onBlur={() => handleBlur('postalCode')}
                      />
                    )}
                  </Field>
                </div>

                <Field id="field-countryCode" label="Country" error={errors.countryCode}>
                  {(aria) => (
                    <Select
                      {...aria}
                      autoComplete="country"
                      value={values.countryCode}
                      onChange={(e) => handleFieldChange('countryCode', e.target.value)}
                      onBlur={() => handleBlur('countryCode')}
                    >
                      {store.countries.map((c) => (
                        <option key={c.code} value={c.code}>
                          {c.name}
                        </option>
                      ))}
                    </Select>
                  )}
                </Field>
              </section>

              {/* 3. Delivery method */}
              <section
                aria-labelledby="section-method"
                className="space-y-4 pt-6 border-t border-border"
              >
                <h2 id="section-method" className="text-title font-semibold text-fg">
                  3. Delivery method
                </h2>
                <ShippingMethodPicker
                  methods={store.shippingMethods}
                  selectedId={values.shippingMethodId}
                  quote={quote}
                  onChange={(id) => handleFieldChange('shippingMethodId', id)}
                  error={errors.shippingMethodId}
                />
              </section>

              {/* 4. Payment */}
              <section
                aria-labelledby="section-payment"
                className="space-y-4 pt-6 border-t border-border"
              >
                <h2 id="section-payment" className="text-title font-semibold text-fg">
                  4. Payment
                </h2>
                <PaymentMethodPicker
                  methods={store.paymentMethods}
                  selectedId={values.paymentMethodId}
                  onChange={(id) => handleFieldChange('paymentMethodId', id)}
                  error={errors.paymentMethodId}
                />
              </section>

              {/* Order note */}
              <section className="space-y-2 pt-6 border-t border-border">
                <Field id="field-note" label="Order note" optional error={errors.note}>
                  {(aria) => (
                    <div>
                      <textarea
                        {...aria}
                        rows={3}
                        value={values.note}
                        onChange={(e) => handleFieldChange('note', e.target.value)}
                        onBlur={() => handleBlur('note')}
                        className="w-full rounded-sm border border-border-strong bg-surface p-3 text-body text-fg placeholder:text-fg-muted focus-visible:outline-2 focus-visible:outline-focus focus-visible:outline-offset-2"
                      />
                      <p className="text-caption text-fg-muted text-right">
                        {values.note.length}/500
                      </p>
                    </div>
                  )}
                </Field>
              </section>

              <div className="pt-6">
                <Button
                  type="submit"
                  size="lg"
                  loading={submitting}
                  disabled={quoteStatus === 'loading'}
                  className="w-full"
                  onClick={handleSubmit}
                >
                  {submitting
                    ? 'Placing your order…'
                    : quote
                      ? `Place order — ${formatMoney(quote.total)}`
                      : 'Place order'}
                </Button>
                {quoteStatus === 'loading' && (
                  <p className="mt-2 text-center text-caption text-fg-muted">Calculating total…</p>
                )}
              </div>
            </fieldset>
          </form>
        </div>

        {/* Desktop summary */}
        <div className="hidden lg:block lg:col-span-5 lg:sticky lg:top-24 self-start">
          <OrderSummary
            cart={cart}
            quote={quote}
            status={quoteStatus}
            taxLabel={store.taxLabel}
            onRetry={fetchQuote}
          />
        </div>
      </Container>
    </div>
  );
}
