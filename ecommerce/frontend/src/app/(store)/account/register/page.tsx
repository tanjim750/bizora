import * as React from 'react';
import AuthForm from '@/components/account/AuthForm';

export const metadata = {
  title: 'Create your account',
};

export default function RegisterPage() {
  return (
    <React.Suspense>
      <AuthForm mode="register" />
    </React.Suspense>
  );
}
