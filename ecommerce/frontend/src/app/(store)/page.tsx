import { serverApi } from '@/lib/api/server';
import Hero from '@/components/home/Hero';
import CategoryTiles from '@/components/home/CategoryTiles';
import { pick } from '@/components/home/pick-categories';

export default async function HomePage() {
  const [home, categories] = await Promise.all([
    serverApi.content.home(),
    serverApi.catalog.listCategories(),
  ]);

  return (
    <>
      <Hero hero={home.hero} />
      <CategoryTiles categories={pick(home.featuredCategorySlugs, categories)} />
    </>
  );
}
