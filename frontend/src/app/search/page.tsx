import { searchArticles } from "../../lib/api";
import Link from "next/link";
import SearchBar from "@/components/search-bar";
import FilterBar from "@/components/filter-bar";
import EmptyState from "@/components/empty-state";
import SearchResultCard from "@/components/search-result-card";
import { cn } from "@/lib/utils";
import type { SearchResult } from "@/lib/api";

export const dynamic = "force-dynamic";

export default async function Page({ searchParams }: { searchParams: { q?: string } }) {
  const q = searchParams?.q ?? "";
  const results = q ? await searchArticles(q) : [];

  const trending = [
    { label: "AI Regulation" },
    { label: "Climate Policy" },
    { label: "Tech Earnings" },
    { label: "Geopolitics" },
    { label: "Energy" },
  ];

  return (
    <main className={cn("py-8")}>
      <section className="text-center mb-6">
        <h1 className="headline-lg">Information Synthesis</h1>
        <p className="body-md text-muted-foreground mt-2">Intelligence analysis powered by multi-source synthesis</p>
      </section>

      <section className="mb-6">
        <SearchBar initialQuery={q} />
      </section>

      <section className="mb-6">
        <h3 className="text-sm font-semibold text-muted-foreground uppercase tracking-wide mb-4">Trending Now</h3>
        <div className="flex flex-wrap gap-2 justify-center">
          {trending.map((t) => (
            <Link key={t.label} href={`/search?q=${encodeURIComponent(t.label)}`}>
              <span className="label-caps-sm bg-surface-container-high rounded-full px-3 py-1.5">
                {t.label}
              </span>
            </Link>
          ))}
        </div>
      </section>

      <section className="mt-6">
        {q && (
          <h4 className="mb-4 label-caps text-muted-foreground">Active Signals ({results.length})</h4>
        )}
        <FilterBar />
        {q && results.length === 0 ? (
          <EmptyState
            icon="search"
            title="No results found"
            description={`We couldn't find any results for "${q}". Try a broader term.`}
          />
        ) : null}
        {results.length > 0 && (
          <ul className="grid grid-cols-1 gap-4 mt-4">
            {results.map((r: SearchResult) => (
              <li key={r.id}>
                <SearchResultCard result={r} query={q} />
              </li>
            ))}
          </ul>
        )}
      </section>
    </main>
  );
}
