import { serverApi } from '@/lib/api/server';
import { Container } from '@/components/ui/Container';
import Hero from '@/components/home/Hero';
import CategoryTiles from '@/components/home/CategoryTiles';
import FeaturedRail from '@/components/home/FeaturedRail';
import EditorialBand from '@/components/home/EditorialBand';
import ValueStrip from '@/components/home/ValueStrip';
import Newsletter from '@/components/home/Newsletter';
import ProductGrid from '@/components/product/ProductGrid';
import { pick } from '@/components/home/pick-categories';

export default async function HomePage() {
  const [home, categories, featured, newIn] = await Promise.all([
    serverApi.content.home(),
    serverApi.catalog.listCategories(),
    serverApi.catalog.listProducts({ collection: 'featured', pageSize: 8 }),
    serverApi.catalog.listProducts({ collection: 'new', pageSize: 4 }),
  ]);

  return (
    <>
      <Hero hero={home.hero} />
      <CategoryTiles categories={pick(home.featuredCategorySlugs, categories)} />
      {featured.items.length > 0 && <FeaturedRail products={featured.items} />}
      <EditorialBand editorial={home.editorial} />
      {newIn.items.length > 0 && (
        <section aria-labelledby="new-title" className="py-24">
          <Container>
            <h2 id="new-title" className="font-display text-display-md text-fg mb-10">
              New in
            </h2>
            <ProductGrid products={newIn.items} columns="home" />
          </Container>
        </section>
      )}
      <ValueStrip values={home.values} />
      <Newsletter variant="band" />
    </>
  );
}
