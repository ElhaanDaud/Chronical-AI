"use client";

import MaterialIcon from "@/components/material-icon";
import { cn } from "@/lib/utils";

const chips = [
  { label: "Topic: All" },
  { label: "Time: 24h" },
  { label: "Source: All" },
];

export default function FilterBar() {
  return (
    <div className="flex flex-wrap items-center gap-2 mb-4 overflow-x-auto md:overflow-visible">
      {chips.map((c) => (
        <div key={c.label} className="flex items-center gap-1 bg-surface-container rounded-full px-3 py-1.5 text-on-surface-variant">
          <span className="text-xs">{c.label}</span>
          <button aria-label="remove" className={cn("ml-1 text-foreground hover:text-foreground rounded-full hover:bg-muted p-0.5")}>
            <MaterialIcon name="close" size={16} />
          </button>
        </div>
      ))}
      <div className="flex items-center gap-2 border border-dashed border-border rounded-full px-3 py-1.5 ml-auto cursor-default">
        <span className="label-caps-sm text-muted-foreground">+ Add Filter</span>
      </div>
      <div className="flex items-center gap-2 ml-2">
        <span className="label-caps-sm text-muted-foreground">Heat</span>
        {["Low", "Med", "High"].map((lvl) => (
          <div key={lvl} className="flex items-center gap-1" title={lvl}>
            <span className="w-2.5 h-2.5 rounded-full bg-surface-container-high" />
            <span className="text-xs text-muted-foreground">{lvl}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
