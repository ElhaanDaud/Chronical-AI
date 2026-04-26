import { cn } from "@/lib/utils";

export default function LiveBadge() {
  return (
    <span className={cn("label-caps-sm bg-secondary-container text-secondary-foreground px-3 py-1 rounded-full inline-flex items-center gap-2")}>
      <span
        aria-hidden="true"
        className="w-1.5 h-1.5 bg-secondary rounded-full animate-pulse-live inline-block"
      />
      LIVE
    </span>
  );
}
