import ThemeToggle from '@/components/layout/ThemeToggle';

export default function HomePage() {
  return (
    <main id="main" className="p-8">
      <div className="flex items-center gap-4">
        <h1 className="text-display-md">Aurelo</h1>
        <ThemeToggle />
      </div>
    </main>
  );
}
