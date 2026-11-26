'use client';

import * as React from 'react';
import { motion } from 'motion/react';
import { Container } from '@/components/ui/Container';
import { Button } from '@/components/ui/Button';
import { Field } from '@/components/ui/Field';
import { Input } from '@/components/ui/Input';
import { browserApi } from '@/lib/api/browser';
import { isApiError, toUserMessage } from '@/lib/api/errors';
import { cn } from '@/lib/cn';

export interface NewsletterProps {
  variant: 'band' | 'footer';
  className?: string;
}

const EMAIL_REGEX = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

export default function Newsletter({ variant, className }: NewsletterProps) {
  const [email, setEmail] = React.useState('');
  const [fieldError, setFieldError] = React.useState<string | undefined>(undefined);
  const [formError, setFormError] = React.useState<string | undefined>(undefined);
  const [loading, setLoading] = React.useState(false);
  const [subscribed, setSubscribed] = React.useState(false);

  const id = `newsletter-email-${variant}`;
  const HeadingTag = variant === 'band' ? 'h2' : 'h3';

  const handleSubmit = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    setFieldError(undefined);
    setFormError(undefined);

    const trimmed = email.trim();
    if (!trimmed) {
      setFieldError('Enter your email address.');
      return;
    }

    if (!EMAIL_REGEX.test(trimmed)) {
      setFieldError('Enter a valid email address.');
      return;
    }

    setLoading(true);
    try {
      await browserApi.newsletter.subscribe(trimmed);
      setSubscribed(true);
    } catch (err) {
      if (isApiError(err) && err.code === 'VALIDATION_FAILED' && err.fields?.email?.[0]) {
        setFieldError(err.fields.email[0]);
      } else {
        setFormError(toUserMessage(err));
      }
    } finally {
      setLoading(false);
    }
  };

  const content = (
    <div className={cn(variant === 'band' && 'max-w-xl mx-auto text-center', className)}>
      <HeadingTag
        className={cn(
          'font-display text-fg',
          variant === 'band' ? 'text-display-md' : 'text-title font-semibold',
        )}
      >
        Letters from the workshop
      </HeadingTag>

      <p className={cn('text-fg-muted mt-2', variant === 'band' ? 'text-body-lg' : 'text-small')}>
        Studio notes, new arrivals, and quiet reflections on making things well.
      </p>

      {subscribed ? (
        <motion.p
          role="status"
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          className={cn(
            'text-fg font-medium mt-6',
            variant === 'band' ? 'text-body-lg' : 'text-body',
          )}
        >
          Thanks — you&apos;re on the list.
        </motion.p>
      ) : (
        <form noValidate onSubmit={handleSubmit} className="mt-6 text-left">
          {formError && (
            <p role="alert" className="text-small text-danger mb-3">
              {formError}
            </p>
          )}

          <div
            className={cn(
              'flex flex-col gap-3',
              variant === 'band' && 'sm:flex-row sm:items-start',
            )}
          >
            <div className="flex-1">
              <Field id={id} label="Email address" error={fieldError}>
                {(aria) => (
                  <Input
                    {...aria}
                    type="email"
                    autoComplete="email"
                    placeholder="Enter your email"
                    value={email}
                    onChange={(e) => {
                      setEmail(e.target.value);
                      if (fieldError) setFieldError(undefined);
                      if (formError) setFormError(undefined);
                    }}
                    disabled={loading}
                  />
                )}
              </Field>
            </div>

            <Button
              type="submit"
              loading={loading}
              className={cn('shrink-0', variant === 'band' ? 'mt-0 sm:mt-7.5 h-12' : 'w-full h-11')}
            >
              Subscribe
            </Button>
          </div>
        </form>
      )}
    </div>
  );

  if (variant === 'band') {
    return (
      <section aria-label="Newsletter" className="py-24 bg-surface border-t border-border">
        <Container>{content}</Container>
      </section>
    );
  }

  return content;
}
