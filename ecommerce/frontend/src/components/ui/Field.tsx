import * as React from 'react';
import { cn } from '@/lib/cn';

export interface FieldAriaProps {
  id: string;
  'aria-describedby'?: string;
  'aria-invalid'?: true;
}

export interface FieldProps {
  id: string;
  label: string;
  hint?: string;
  error?: string;
  children: (aria: FieldAriaProps) => React.ReactNode;
  optional?: boolean;
  className?: string;
}

export function Field({
  id,
  label,
  hint,
  error,
  children,
  optional = false,
  className,
}: FieldProps) {
  const describedByParts: string[] = [];
  if (hint) describedByParts.push(`${id}-hint`);
  if (error) describedByParts.push(`${id}-error`);

  const describedBy = describedByParts.length > 0 ? describedByParts.join(' ') : undefined;

  const aria: FieldAriaProps = {
    id,
    'aria-describedby': describedBy,
    'aria-invalid': error ? true : undefined,
  };

  return (
    <div className={cn('flex flex-col gap-1.5', className)}>
      <label htmlFor={id} className="text-small font-medium text-fg">
        {label}
        {optional ? ' (optional)' : ''}
      </label>
      {children(aria)}
      {hint && (
        <p id={`${id}-hint`} className="text-small text-fg-muted">
          {hint}
        </p>
      )}
      {error && (
        <p id={`${id}-error`} className="text-small text-danger">
          {error}
        </p>
      )}
    </div>
  );
}
