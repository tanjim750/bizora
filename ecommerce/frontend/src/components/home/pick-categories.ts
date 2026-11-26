import type { Category } from '@/lib/api/types';

export function pick(slugs: string[], categories: Category[]): Category[] {
  const map = new Map<string, Category>();
  for (const cat of categories) {
    map.set(cat.slug, cat);
  }
  const result: Category[] = [];
  for (const slug of slugs) {
    const cat = map.get(slug);
    if (cat) {
      result.push(cat);
    }
  }
  return result;
}
