"use client";

import Link from "next/link";
import { SearchBar } from "./search-bar";
import React from "react";

export default function Navbar() {
  return (
    <header className="fixed top-0 left-0 right-0 z-50 bg-card border-b border-border">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-14 flex items-center justify-between">
        <Link href="/" className="text-xl font-semibold tracking-tight text-foreground hover:underline">
          Chronicle
        </Link>
        <div className="flex-1 flex items-center justify-end space-x-4">
          <SearchBar />
        </div>
      </div>
    </header>
  );
}
