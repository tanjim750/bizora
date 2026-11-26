import * as React from 'react';

export default function SkipLink() {
  return (
    <a
      href="#main"
      className="sr-only focus:not-sr-only focus:fixed focus:left-4 focus:top-4 focus:z-(--aur-z-skip) rounded-pill bg-accent px-4 py-2 text-accent-fg font-medium shadow-card transition-transform outline-none ring-2 ring-focus ring-offset-2 ring-offset-bg"
    >
      Skip to content
    </a>
  );
}
