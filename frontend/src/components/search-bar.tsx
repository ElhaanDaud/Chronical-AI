"use client";

import MaterialIcon from "@/components/material-icon";
import { cn } from "@/lib/utils";

type Props = {
  initialQuery?: string;
};

function SearchBar({ initialQuery = "" }: Props) {
  return (
    <form action="/search" method="GET" className={cn("w-full max-w-[800px] mx-auto px-2")}>
      <div className="relative">
        <input
          name="q"
          defaultValue={initialQuery}
          placeholder="Search across all intelligence threads..."
          className="w-full h-14 border border-border rounded-lg bg-card pl-4 pr-12 body-lg outline-none focus:ring-2 focus:ring-ring focus:border-primary"
        />
        <button type="submit" className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground transition-colors">
          <MaterialIcon name="search" size={22} />
        </button>
      </div>
    </form>
  );
}

export { SearchBar };
export default SearchBar;
