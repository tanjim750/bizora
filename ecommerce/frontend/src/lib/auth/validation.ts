import { z } from 'zod';

const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

export type SignInValues = {
  email: string;
  password: string;
};

export type RegisterValues = {
  firstName: string;
  lastName: string;
  email: string;
  password: string;
};

export type ValidationResult<T> =
  | { ok: true; data: T }
  | { ok: false; errors: Record<string, string> };

export function validateSignIn(values: SignInValues): ValidationResult<SignInValues> {
  const errors: Record<string, string> = {};
  const email = (values.email ?? '').trim();
  const password = values.password ?? '';

  if (!email) {
    errors.email = 'Enter your email address.';
  } else if (!emailRegex.test(email)) {
    errors.email = 'Enter a valid email address.';
  }

  if (!password) {
    errors.password = 'Enter your password.';
  }

  if (Object.keys(errors).length > 0) {
    return { ok: false, errors };
  }

  return { ok: true, data: { email, password } };
}

export function validateRegister(values: RegisterValues): ValidationResult<RegisterValues> {
  const errors: Record<string, string> = {};
  const firstName = (values.firstName ?? '').trim();
  const lastName = (values.lastName ?? '').trim();
  const email = (values.email ?? '').trim();
  const password = values.password ?? '';

  if (!firstName) {
    errors.firstName = 'Enter your first name.';
  } else if (firstName.length > 60) {
    errors.firstName = 'Keep this under 60 characters.';
  }

  if (!lastName) {
    errors.lastName = 'Enter your last name.';
  } else if (lastName.length > 60) {
    errors.lastName = 'Keep this under 60 characters.';
  }

  if (!email) {
    errors.email = 'Enter your email address.';
  } else if (!emailRegex.test(email)) {
    errors.email = 'Enter a valid email address.';
  }

  if (!password || password.length < 8) {
    errors.password = 'Use at least 8 characters.';
  } else if (password.length > 128) {
    errors.password = 'Use at most 128 characters.';
  }

  if (Object.keys(errors).length > 0) {
    return { ok: false, errors };
  }

  return { ok: true, data: { firstName, lastName, email, password } };
}
