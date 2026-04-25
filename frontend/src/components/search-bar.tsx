"use client";

import React, { useState } from "react";
import { Button } from "@/components/ui/button";
import { useRouter } from "next/navigation";
import { Search } from "lucide-react";

function SearchBar() {
  const [q, setQ] = useState("");
  const router = useRouter();

  const onSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (q.trim()) {
      router.push(`/search?q=${encodeURIComponent(q.trim())}`);
    }
  };

  return (
    <form onSubmit={onSubmit} className="flex items-center gap-2">
      <input
        value={q}
        onChange={(e) => setQ(e.target.value)}
        placeholder="Search articles..."
        className="h-9 rounded-md border border-border bg-background text-foreground px-3 w-48 sm:w-64"
      />
      <Button type="submit" variant="default" className="h-9 px-3">
        <Search className="size-4" />
      </Button>
    </form>
  );
}

export { SearchBar }
