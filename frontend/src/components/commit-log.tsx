"use client"

import { CommitResponse } from "@/lib/api"
import { cn } from "@/lib/utils"

type CommitLogProps = {
  commits: CommitResponse[]
}

function formatCommitDate(dateStr: string) {
  const d = new Date(dateStr)
  const now = new Date()
  const isToday = d.toDateString() === now.toDateString()
  const prefix = isToday ? "TODAY" : d.toLocaleDateString("en-US", { month: "short", day: "numeric" }).toUpperCase()
  const time = d.toLocaleTimeString("en-US", { hour: "2-digit", minute: "2-digit", hour12: false, timeZone: "UTC" })
  return `${prefix}, ${time} UTC`
}

function CommitLog({ commits }: CommitLogProps) {
  return (
    <div>
      <h3 className="headline-md mb-lg">Commit History</h3>
      <div className="relative">
        <div className="absolute left-[7px] top-3 bottom-3 w-px bg-border" />
        <div className="flex flex-col gap-lg">
          {commits.map((c, idx) => {
            const isLatest = idx === 0
            return (
              <div key={c.id} className="relative pl-10">
                <span
                  className={cn(
                    "absolute rounded-full border-2 border-background",
                    isLatest
                      ? "left-0 top-1 h-[14px] w-[14px] bg-secondary"
                      : "left-[3px] top-1.5 h-2 w-2 bg-muted-foreground/50"
                  )}
                />
                <div className="flex flex-col gap-1">
                  <span className="label-caps-sm text-muted-foreground">
                    {formatCommitDate(c.commit_date)}
                  </span>
                  {isLatest && (
                    <span className="metadata italic text-secondary">Major Revision</span>
                  )}
                  <h4 className="headline-md">{c.message}</h4>
                  <p className="body-md text-muted-foreground">{c.detail}</p>
                  <span className="metadata text-muted-foreground mt-1">
                    {c.source_count} source{c.source_count === 1 ? "" : "s"}
                  </span>
                  {c.source_urls && c.source_urls.length > 0 && (
                    <details className="mt-1">
                      <summary className="metadata text-secondary hover:text-secondary/80 cursor-pointer transition-colors">
                        View sources
                      </summary>
                      <ul className="list-disc pl-5 mt-2 space-y-1">
                        {c.source_urls.map((u) => (
                          <li key={u}>
                            <a
                              href={u}
                              target="_blank"
                              rel="noreferrer"
                              className="metadata text-secondary hover:underline break-all"
                            >
                              {u}
                            </a>
                          </li>
                        ))}
                      </ul>
                    </details>
                  )}
                </div>
              </div>
            )
          })}
        </div>
      </div>
    </div>
  )
}

export { CommitLog }
