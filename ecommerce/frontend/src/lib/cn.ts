import { clsx, type ClassValue } from 'clsx';
import { extendTailwindMerge } from 'tailwind-merge';

const customTwMerge = extendTailwindMerge({
  extend: {
    classGroups: {
      'font-size': [
        {
          text: [
            'display-xl',
            'display-lg',
            'display-md',
            'title',
            'body-lg',
            'body',
            'small',
            'label',
            'label-caps',
          ],
        },
      ],
      'font-family': [{ font: ['display', 'sans', 'mono'] }],
      'text-color': [
        {
          text: [
            'bg',
            'surface',
            'surface-2',
            'fg',
            'fg-muted',
            'border',
            'border-strong',
            'accent',
            'accent-fg',
            'success',
            'danger',
            'warning',
            'focus',
            'overlay',
          ],
        },
      ],
      rounded: [{ rounded: ['sm', 'md', 'lg', 'pill'] }],
      shadow: [{ shadow: ['float'] }],
    },
  },
});

export function cn(...inputs: ClassValue[]) {
  return customTwMerge(clsx(inputs));
}
