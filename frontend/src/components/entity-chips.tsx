import { cn } from "@/lib/utils"
import MaterialIcon from "@/components/material-icon"

type EntityChipsProps = {
  entities: string[]
  className?: string
}

export function EntityChips({ entities, className }: EntityChipsProps) {
  if (!entities || entities.length === 0) return null

  return (
    <div className={cn("bg-card border border-border rounded-lg p-lg", className)}>
      <h3 className="label-caps text-muted-foreground mb-md flex items-center gap-2">
        <MaterialIcon name="hub" size={18} />
        KEY ENTITIES
      </h3>
      <div className="flex flex-wrap gap-2">
        {entities.map((entity) => (
          <span
            key={entity}
            className="px-3 py-1.5 bg-surface-container text-on-surface text-sm border border-border rounded-full dark:bg-slate-800 dark:border-slate-700"
          >
            {entity}
          </span>
        ))}
      </div>
    </div>
  )
}
