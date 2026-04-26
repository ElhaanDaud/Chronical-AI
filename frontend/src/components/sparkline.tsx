import type { CommitResponse } from "@/lib/api"
import { cn } from "@/lib/utils"

type SparklineProps = {
  commits: CommitResponse[]
  className?: string
}

export function Sparkline({ commits, className }: SparklineProps) {
  const now = Date.now()
  const windowMs = 72 * 60 * 60 * 1000
  const bucketMs = 6 * 60 * 60 * 1000
  const bucketCount = 12

  const buckets = new Array(bucketCount).fill(0)
  for (const c of commits) {
    const age = now - new Date(c.commit_date).getTime()
    if (age >= 0 && age < windowMs) {
      const idx = Math.min(bucketCount - 1, Math.floor(age / bucketMs))
      buckets[bucketCount - 1 - idx]++
    }
  }

  const max = Math.max(...buckets, 1)
  const w = 120
  const h = 40
  const padY = 4
  const usableH = h - padY * 2
  const stepX = w / (bucketCount - 1)

  const points = buckets.map((v, i) => {
    const x = i * stepX
    const y = padY + usableH - (v / max) * usableH
    return `${x},${y}`
  })

  return (
    <div className={cn("flex flex-col items-end gap-1", className)}>
      <span className="metadata text-muted-foreground">72hr Velocity</span>
      <svg
        width={w}
        height={h}
        viewBox={`0 0 ${w} ${h}`}
        fill="none"
        className="overflow-visible"
      >
        <polyline
          points={points.join(" ")}
          className="stroke-primary dark:stroke-secondary"
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
          fill="none"
        />
      </svg>
    </div>
  )
}
