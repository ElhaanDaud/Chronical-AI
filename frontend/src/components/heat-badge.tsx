import React from "react"
import { Badge } from "@/components/ui/badge"
import { cn } from "@/lib/utils"

type HeatBadgeProps = {
  state: "active" | "cooling" | "hibernated"
  heat_score: number
  className?: string
}

function HeatBadge({ state, heat_score, className }: HeatBadgeProps) {
  const variant = state === "active" ? "destructive" : state === "hibernated" ? "secondary" : "default"
  const extra = state === "cooling" ? "bg-amber-500 text-amber-900" : undefined
  return (
    <Badge variant={variant} className={cn(extra, className)}>
      {state} • {heat_score.toFixed(1)}
    </Badge>
  )
}

export { HeatBadge }
