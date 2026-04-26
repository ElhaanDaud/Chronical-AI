import { searchArticles } from "../../lib/api";
import SearchBar from "@/components/search-bar";
import EmptyState from "@/components/empty-state";
import SearchResultCard from "@/components/search-result-card";
import { cn } from "@/lib/utils";
import type { SearchResult } from "@/lib/api";

export const dynamic = "force-dynamic";

export default async function Page({ searchParams }: { searchParams: { q?: string } }) {
  const q = searchParams?.q ?? "";
  let results: SearchResult[] = [];
  try {
    results = q ? await searchArticles(q) : [];
  } catch {
    results = [];
  }

  return (
    <main className={cn("py-8")}>
      <section className="text-center mb-6">
        <h1 className="headline-lg">Information Synthesis</h1>
        <p className="body-md text-muted-foreground mt-2">Intelligence analysis powered by multi-source synthesis</p>
      </section>

      <section className="mb-6">
        <SearchBar initialQuery={q} />
      </section>

      <section className="mt-6">
        {q && (
          <h4 className="mb-4 label-caps text-muted-foreground">Active Signals ({results.length})</h4>
        )}
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
