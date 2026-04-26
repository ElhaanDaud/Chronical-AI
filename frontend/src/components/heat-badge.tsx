import { cn } from "@/lib/utils"

type HeatBadgeProps = {
  heat_score: number
  state?: "active" | "cooling" | "hibernated"
  className?: string
}

function HeatBadge({ heat_score, className }: HeatBadgeProps) {
  let text = "COOLING";
  let color = "bg-muted text-muted-foreground";
  if (heat_score >= 3.0) {
    text = "HIGH HEAT";
    color = "bg-secondary/15 text-secondary";
  } else if (heat_score >= 1.0) {
    text = "RISING HEAT";
    color = "bg-amber-500/15 text-amber-600";
  }
  return (
    <span className={cn("rounded-full px-2.5 py-0.5 label-caps-sm", color, className)}>
      {text}
    </span>
  )
}

export { HeatBadge }
