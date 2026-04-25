import { searchArticles } from "../../lib/api";
import Link from "next/link";

export const dynamic = "force-dynamic";

export default async function Page({ searchParams }: { searchParams: { q?: string } }) {
  const q = searchParams?.q ?? "";
  const results = q ? await searchArticles(q) : [];

  return (
    <>
      <h2 className="text-xl font-semibold mb-4">
        {q ? `Search results for "${q}"` : "Search"}
      </h2>
      {!q && <p className="text-muted-foreground">Enter a query to search articles.</p>}
      {q && results.length === 0 && (
        <p className="text-muted-foreground">No results found.</p>
      )}
      {results.length > 0 && (
        <ul className="divide-y divide-border">
          {results.map((r) => (
            <li key={r.id} className="py-4">
              <Link href={r.cluster_id ? `/story/${r.cluster_id}` : "#"} className="flex flex-col gap-1">
                <span className="text-sm font-semibold">{r.title}</span>
                <span className="text-xs text-muted-foreground">
                  {r.source} &middot; {new Date(r.published_at).toLocaleDateString()}
                </span>
                {r.summary && <span className="text-sm text-muted-foreground">{r.summary}</span>}
              </Link>
            </li>
          ))}
        </ul>
      )}
    </>
  );
}
