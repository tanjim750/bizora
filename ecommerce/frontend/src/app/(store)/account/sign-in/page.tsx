import * as React from 'react';
import AuthForm from '@/components/account/AuthForm';

export const metadata = {
  title: 'Sign in',
};

export default function SignInPage() {
  return (
    <React.Suspense>
      <AuthForm mode="sign-in" />
    </React.Suspense>
  );
}
