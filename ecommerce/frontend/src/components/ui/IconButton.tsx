import * as React from 'react';
import { cn } from '@/lib/cn';
import { Button, type ButtonProps } from './Button';

export interface IconButtonProps extends Omit<ButtonProps, 'aria-label'> {
  'aria-label': string;
}

export function IconButton({ variant = 'ghost', className, ...props }: IconButtonProps) {
  return (
    <Button
      variant={variant}
      className={cn('size-11 p-0 rounded-pill min-h-0', className)}
      {...props}
    />
  );
}
