"use client";

import { CommitResponse } from "@/lib/api";
import { Separator } from "@/components/ui/separator";

type CommitLogProps = {
  commits: CommitResponse[];
};

function CommitLog({ commits }: CommitLogProps) {
  return (
    <div className="relative">
      <div className="absolute left-[5px] top-0 bottom-0 w-px bg-border" />
      <div className="flex flex-col gap-6">
        {commits.map((c, idx) => (
          <div key={c.id} className="relative pl-8">
            <span className="absolute left-0 top-1.5 h-3 w-3 rounded-full border-2 border-foreground bg-background" />
            <div className="flex flex-col gap-1">
              <span className="text-xs text-muted-foreground">
                {new Date(c.commit_date).toLocaleDateString("en-US", {
                  month: "short",
                  day: "numeric",
                  year: "numeric",
                })}
              </span>
              <div className="font-semibold">{c.message}</div>
              <div className="text-sm text-muted-foreground">{c.detail}</div>
              <div className="text-xs text-muted-foreground mt-1">
                {c.source_count} source{c.source_count === 1 ? "" : "s"}
              </div>
              {c.source_urls && c.source_urls.length > 0 && (
                <details className="mt-1 text-sm">
                  <summary className="cursor-pointer text-primary hover:underline">
                    View sources
                  </summary>
                  <ul className="list-disc pl-5 mt-1 space-y-0.5">
                    {c.source_urls.map((u) => (
                      <li key={u}>
                        <a
                          href={u}
                          target="_blank"
                          rel="noreferrer"
                          className="text-xs text-primary hover:underline break-all"
                        >
                          {u}
                        </a>
                      </li>
                    ))}
                  </ul>
                </details>
              )}
            </div>
            {idx < commits.length - 1 && <Separator className="mt-4" />}
          </div>
        ))}
      </div>
    </div>
  );
}

export { CommitLog };
