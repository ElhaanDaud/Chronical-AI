import Link from "next/link";
import { formatRelativeTime } from "@/lib/utils";
import { cn } from "@/lib/utils";
import type { SearchResult } from "@/lib/api";

type Props = {
  result: SearchResult;
  query?: string;
};

function escapeRegExp(string: string) {
  return string.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

export default function SearchResultCard({ result, query }: Props) {
  const leftColor = result.cluster_id ? 'var(--secondary)' : 'var(--border)';
  const hasCluster = Boolean(result.cluster_id);
  const summary = result.summary ?? "";
  function renderExcerpt(txt: string) {
    if (!query) return <span className="body-md text-muted-foreground">{txt}</span>;
    const q = query.trim();
    if (!q) return <span className="body-md text-muted-foreground">{txt}</span>;
    const parts = txt.split(new RegExp(`(${escapeRegExp(q)})`, 'gi'));
    return (
      <span className="body-md text-muted-foreground">
        {parts.map((part, idx) =>
          part.toLowerCase() === q.toLowerCase() ? (
            <span key={idx} className="bg-secondary-fixed px-1 rounded">{part}</span>
          ) : (
            <span key={idx}>{part}</span>
          )
        )}
      </span>
    );
  }

  return (
    <article
      className={cn(
        "bg-card p-md rounded-lg whisper-shadow border border-border flex flex-col",
        "transition-all duration-200 hover:hover-shadow",
        "border-l-0 ml-0 pl-0"
      )}
      style={{ borderLeft: `3px solid ${leftColor}` }}
    >
      <div className="flex items-center text-sm text-muted-foreground mb-1">
        <span className="mr-auto">{result.source}</span>
        <span className="mx-2">·</span>
        <span className="ml-2 metadata">{formatRelativeTime(result.published_at)}</span>
        {hasCluster && (
          <span className="ml-4 label-caps-sm bg-surface-container px-2 py-0.5 rounded-full">AI Confidence</span>
        )}
      </div>

      <div className="mb-1">
        {hasCluster ? (
          <Link href={`/story/${result.cluster_id}`} className="headline-md text-foreground hover:underline">
            {result.title}
          </Link>
        ) : (
          <span className="headline-md text-foreground">{result.title}</span>
        )}
      </div>

      <div className="mb-2">{result.summary ? renderExcerpt(summary) : null}</div>

      {hasCluster && (
        <div className="mt-1">
          <Link href={`/story/${result.cluster_id}`} className="label-caps-sm text-secondary">
            Read Full Brief →
          </Link>
        </div>
      )}
    </article>
  );
}
