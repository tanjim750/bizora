import * as React from 'react';
import { cn } from '@/lib/cn';

export interface ContainerProps extends React.ComponentProps<'div'> {
  as?: 'div' | 'section' | 'header' | 'footer' | 'main';
}

export function Container({
  as: Component = 'div',
  className,
  children,
  ...props
}: ContainerProps) {
  return (
    <Component
      className={cn('mx-auto w-full max-w-360 px-5 md:px-8 xl:px-12', className)}
      {...props}
    >
      {children}
    </Component>
  );
}
