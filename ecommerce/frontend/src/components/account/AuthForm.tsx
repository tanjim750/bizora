'use client';

import * as React from 'react';
import Link from 'next/link';
import { useRouter, useSearchParams } from 'next/navigation';
import { Eye, EyeOff } from 'lucide-react';
import { useSessionStore } from '@/stores/session-store';
import { isApiError, toUserMessage } from '@/lib/api/errors';
import { safeNextPath } from '@/lib/auth/redirect';
import { validateSignIn, validateRegister, type RegisterValues } from '@/lib/auth/validation';
import { Field } from '@/components/ui/Field';
import { Input } from '@/components/ui/Input';
import { Button } from '@/components/ui/Button';
import { IconButton } from '@/components/ui/IconButton';

export interface AuthFormProps {
  mode: 'sign-in' | 'register';
}

export default function AuthForm({ mode }: AuthFormProps) {
  const router = useRouter();
  const searchParams = useSearchParams();
  const nextParam = searchParams.get('next');

  const sessionStatus = useSessionStore((s) => s.status);
  const submittedRef = React.useRef(false);

  const [values, setValues] = React.useState<RegisterValues>({
    firstName: '',
    lastName: '',
    email: '',
    password: '',
  });

  const [errors, setErrors] = React.useState<Record<string, string>>({});
  const [formAlert, setFormAlert] = React.useState<string | null>(null);
  const [emailTaken, setEmailTaken] = React.useState(false);
  const [showPassword, setShowPassword] = React.useState(false);
  const [submitting, setSubmitting] = React.useState(false);

  // If already signed in when arriving, redirect to /account
  React.useEffect(() => {
    if (sessionStatus === 'signed-in' && !submittedRef.current) {
      router.replace('/account');
    }
  }, [sessionStatus, router]);

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { name, value } = e.target;
    setValues((prev) => ({ ...prev, [name]: value }));
    if (errors[name]) {
      setErrors((prev) => {
        const next = { ...prev };
        delete next[name];
        return next;
      });
    }
    if (name === 'email' && emailTaken) {
      setEmailTaken(false);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setFormAlert(null);
    setEmailTaken(false);

    if (mode === 'sign-in') {
      const res = validateSignIn({
        email: values.email,
        password: values.password,
      });

      if (!res.ok) {
        setErrors(res.errors);
        const firstKey = Object.keys(res.errors)[0];
        const el = document.getElementById(`sign-in-${firstKey}`);
        el?.focus();
        return;
      }

      setErrors({});
      setSubmitting(true);
      submittedRef.current = true;

      try {
        await useSessionStore.getState().signIn(res.data);
        const destination = safeNextPath(nextParam);
        router.replace(destination);
      } catch (err) {
        setSubmitting(false);
        submittedRef.current = false;
        if (isApiError(err)) {
          if (err.code === 'INVALID_CREDENTIALS') {
            setFormAlert("That email and password don't match.");
          } else if (err.code === 'RATE_LIMITED') {
            setFormAlert(toUserMessage(err));
          } else if (err.code === 'VALIDATION_FAILED') {
            const fieldErrs: Record<string, string> = {};
            if (err.details && typeof err.details === 'object') {
              for (const [k, v] of Object.entries(err.details)) {
                if (Array.isArray(v) && v[0]) fieldErrs[k] = v[0];
                else if (typeof v === 'string') fieldErrs[k] = v;
              }
            }
            setErrors(fieldErrs);
          } else {
            setFormAlert(toUserMessage(err));
          }
        } else {
          setFormAlert(toUserMessage(err));
        }
      }
    } else {
      // register mode
      const res = validateRegister(values);

      if (!res.ok) {
        setErrors(res.errors);
        const firstKey = Object.keys(res.errors)[0];
        const el = document.getElementById(`register-${firstKey}`);
        el?.focus();
        return;
      }

      setErrors({});
      setSubmitting(true);
      submittedRef.current = true;

      try {
        await useSessionStore.getState().register(res.data);
        const destination = safeNextPath(nextParam);
        router.replace(destination);
      } catch (err) {
        setSubmitting(false);
        submittedRef.current = false;
        if (isApiError(err)) {
          if (err.code === 'EMAIL_TAKEN') {
            setErrors((prev) => ({
              ...prev,
              email: 'An account with this email already exists.',
            }));
            setEmailTaken(true);
          } else if (err.code === 'RATE_LIMITED') {
            setFormAlert(toUserMessage(err));
          } else if (err.code === 'VALIDATION_FAILED') {
            const fieldErrs: Record<string, string> = {};
            if (err.details && typeof err.details === 'object') {
              for (const [k, v] of Object.entries(err.details)) {
                if (Array.isArray(v) && v[0]) fieldErrs[k] = v[0];
                else if (typeof v === 'string') fieldErrs[k] = v;
              }
            }
            setErrors(fieldErrs);
          } else {
            setFormAlert(toUserMessage(err));
          }
        } else {
          setFormAlert(toUserMessage(err));
        }
      }
    }
  };

  const nextQuery = nextParam ? `?next=${encodeURIComponent(nextParam)}` : '';

  return (
    <div className="mx-auto max-w-md py-16 px-4">
      <div className="mb-8 text-center space-y-2">
        <h1 className="font-display text-display-lg text-fg">
          {mode === 'sign-in' ? 'Sign in' : 'Create your account'}
        </h1>
        <p className="text-body text-fg-muted">
          {mode === 'sign-in' ? 'Welcome back.' : 'Track orders and check out faster.'}
        </p>
      </div>

      <form noValidate onSubmit={handleSubmit} className="space-y-6">
        {formAlert && (
          <p
            role="alert"
            className="rounded-md border border-danger/30 bg-danger/10 p-4 text-small text-danger font-medium"
          >
            {formAlert}
          </p>
        )}

        {mode === 'register' && (
          <div className="grid grid-cols-2 gap-4">
            <Field id="register-firstName" label="First name" error={errors.firstName}>
              {(aria) => (
                <Input
                  {...aria}
                  name="firstName"
                  type="text"
                  autoComplete="given-name"
                  value={values.firstName}
                  onChange={handleChange}
                />
              )}
            </Field>

            <Field id="register-lastName" label="Last name" error={errors.lastName}>
              {(aria) => (
                <Input
                  {...aria}
                  name="lastName"
                  type="text"
                  autoComplete="family-name"
                  value={values.lastName}
                  onChange={handleChange}
                />
              )}
            </Field>
          </div>
        )}

        <Field id={`${mode}-email`} label="Email" error={errors.email}>
          {(aria) => (
            <div>
              <Input
                {...aria}
                name="email"
                type="email"
                autoComplete="email"
                value={values.email}
                onChange={handleChange}
              />
              {emailTaken && (
                <p className="mt-2 text-small">
                  <Link
                    href={`/account/sign-in${nextQuery}`}
                    className="text-accent underline font-medium hover:text-accent/80"
                  >
                    Sign in instead
                  </Link>
                </p>
              )}
            </div>
          )}
        </Field>

        <Field
          id={`${mode}-password`}
          label="Password"
          hint={mode === 'register' ? 'At least 8 characters.' : undefined}
          error={errors.password}
        >
          {(aria) => (
            <div className="relative flex items-center">
              <Input
                {...aria}
                name="password"
                type={showPassword ? 'text' : 'password'}
                autoComplete={mode === 'sign-in' ? 'current-password' : 'new-password'}
                value={values.password}
                onChange={handleChange}
                className="pr-12"
              />
              <IconButton
                type="button"
                variant="ghost"
                aria-label={showPassword ? 'Hide password' : 'Show password'}
                aria-pressed={showPassword}
                onClick={() => setShowPassword((prev) => !prev)}
                className="absolute right-1 text-fg-muted hover:text-fg"
              >
                {showPassword ? (
                  <EyeOff size={18} aria-hidden="true" />
                ) : (
                  <Eye size={18} aria-hidden="true" />
                )}
              </IconButton>
            </div>
          )}
        </Field>

        <Button type="submit" size="lg" loading={submitting} className="w-full">
          {mode === 'sign-in' ? 'Sign in' : 'Create account'}
        </Button>
      </form>

      <div className="mt-8 text-center text-small text-fg-muted">
        {mode === 'sign-in' ? (
          <p>
            New here?{' '}
            <Link
              href={`/account/register${nextQuery}`}
              className="text-accent underline font-medium hover:text-accent/80"
            >
              Create an account
            </Link>
          </p>
        ) : (
          <p>
            Already have an account?{' '}
            <Link
              href={`/account/sign-in${nextQuery}`}
              className="text-accent underline font-medium hover:text-accent/80"
            >
              Sign in
            </Link>
          </p>
        )}
      </div>
    </div>
  );
}
