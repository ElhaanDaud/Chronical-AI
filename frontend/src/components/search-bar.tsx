"use client";

import { Button } from "@/components/ui/button";
import MaterialIcon from "@/components/material-icon";
import { cn } from "@/lib/utils";

type Props = {
  initialQuery?: string;
};

function SearchBar({ initialQuery = "" }: Props) {
  return (
    <form action="/search" method="GET" className={cn("w-full max-w-[800px] mx-auto flex gap-sm items-center px-2")}>
      <div className="flex-1">
        <input
          name="q"
          defaultValue={initialQuery}
          placeholder="Search across all intelligence threads..."
          className="w-full h-14 border border-border rounded-lg bg-card px-4 body-lg outline-none focus:ring-2 focus:ring-ring focus:border-primary"
        />
      </div>
      <Button type="submit" variant="default" size="lg" className={cn("label-caps px-lg h-14 ml-2")}>
        <MaterialIcon name="search" className="mr-2" /> Analyze
      </Button>
    </form>
  );
}

export { SearchBar };
export default SearchBar;
