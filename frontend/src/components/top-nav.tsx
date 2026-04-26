"use client";

import { useState } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { SearchBar } from "@/components/search-bar";
import MaterialIcon from "@/components/material-icon";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import ThemeToggle from "@/components/theme-toggle";

const NAV_LINKS = [
  { label: "Home Feed", href: "/", italic: true },
  { label: "Search", href: "/search" },
];

type TopNavProps = {
  onMenuToggle?: () => void;
};

export default function TopNav({ onMenuToggle }: TopNavProps) {
  const pathname = usePathname();
  const router = useRouter();
  const [ingesting, setIngesting] = useState(false);

  const handleIngest = async () => {
    setIngesting(true);
    try {
      const base = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
      await fetch(`${base}/api/ingest?full_pipeline=true`, { method: "POST" });
      router.refresh();
    } catch {
    } finally {
      setIngesting(false);
    }
  };

  return (
    <header className="fixed top-0 w-full z-50 h-16 flex items-center justify-between px-6 bg-card/80 backdrop-blur-md border-b border-border">
      <div className="flex items-center gap-4">
        <button
          aria-label="Open menu"
          className="md:hidden p-2 rounded hover:bg-accent/50 transition-colors"
          onClick={onMenuToggle}
        >
          <MaterialIcon name="menu" />
        </button>
        <Link href="/" className="font-serif text-2xl font-semibold tracking-tight text-foreground">
          Chronicle AI
        </Link>
      </div>

      <nav className="hidden md:flex items-center gap-6 h-full">
        {NAV_LINKS.map((link) => {
          const isActive = link.href === "/" ? pathname === "/" : pathname === link.href;
          return (
            <Link
              key={link.label}
              href={link.href}
              className={cn(
                "flex items-center h-full transition-colors duration-200",
                isActive
                  ? "text-foreground border-b-2 border-secondary font-serif italic tracking-tight"
                  : "label-caps-sm text-muted-foreground hover:text-secondary border-b-2 border-transparent"
              )}
            >
              {link.label}
            </Link>
          );
        })}
      </nav>

      <div className="flex items-center gap-3">
        <div className="hidden sm:block">
          <SearchBar />
        </div>
        <Button
          className="hidden sm:inline-flex label-caps-sm px-4 py-2"
          onClick={handleIngest}
          disabled={ingesting}
        >
          <MaterialIcon name={ingesting ? "hourglass_empty" : "refresh"} size={16} />
          <span className="ml-1">{ingesting ? "Ingesting…" : "Ingest Refresh"}</span>
        </Button>
        <ThemeToggle />
      </div>
    </header>
  );
}
