"use client"

import { useState } from "react"
import { fetchCatchUp } from "@/lib/api"
import { Skeleton } from "@/components/ui/skeleton"
import MaterialIcon from "@/components/material-icon"
import { cn } from "@/lib/utils"

type ExecutiveSynthesisProps = {
  storyId: string
  className?: string
}

export function ExecutiveSynthesis({ storyId, className }: ExecutiveSynthesisProps) {
  const [loading, setLoading] = useState(false)
  const [narrative, setNarrative] = useState<string | null>(null)
  const [meta, setMeta] = useState<{ commit_count: number; time_span_days: number } | null>(null)
  const [error, setError] = useState<string | null>(null)

  const load = async () => {
    setLoading(true)
    setError(null)
    try {
      const res = await fetchCatchUp(storyId)
      setNarrative(res.narrative)
      setMeta({ commit_count: res.commit_count, time_span_days: res.time_span_days })
    } catch {
      setError("Unable to synthesize. Try again.")
    } finally {
      setLoading(false)
    }
  }

  const bullets = narrative
    ? narrative.split(/\.\s+/).filter((s) => s.trim().length > 0).map((s) => s.trim().replace(/\.$/, ""))
    : []

  return (
    <div className={cn("relative rounded-lg bg-card border border-border overflow-hidden", className)}>
      <div className="absolute left-0 top-0 bottom-0 w-[3px] bg-secondary" />
      <div className="p-lg pl-[calc(var(--space-lg)+3px)]">
        <div className="flex items-center justify-between mb-md">
          <h3 className="label-caps text-muted-foreground flex items-center gap-2">
            <MaterialIcon name="auto_awesome" size={18} />
            EXECUTIVE SYNTHESIS
          </h3>
          {!narrative && !loading && (
            <button
              onClick={load}
              className="label-caps-sm text-secondary hover:text-secondary/80 transition-colors"
            >
              Generate →
            </button>
          )}
        </div>

        {loading && (
          <div className="space-y-3">
            <Skeleton className="h-4 w-full rounded" />
            <Skeleton className="h-4 w-5/6 rounded" />
            <Skeleton className="h-4 w-4/6 rounded" />
          </div>
        )}

        {!loading && error && (
          <p className="body-md text-destructive">{error}</p>
        )}

        {!loading && narrative && (
          <div className="space-y-4">
            <ul className="space-y-3">
              {bullets.map((bullet, i) => (
                <li key={i} className="body-lg flex gap-3">
                  <span className="text-secondary mt-1 shrink-0">•</span>
                  <span>{bullet}</span>
                </li>
              ))}
            </ul>
            {meta && (
              <p className="metadata text-muted-foreground pt-2 border-t border-border">
                Based on {meta.commit_count} revision{meta.commit_count === 1 ? "" : "s"} over {meta.time_span_days} day{meta.time_span_days === 1 ? "" : "s"}
              </p>
            )}
          </div>
        )}
      </div>
    </div>
  )
}
