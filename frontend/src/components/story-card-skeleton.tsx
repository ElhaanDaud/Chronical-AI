"use client";

import { Skeleton } from "@/components/ui/skeleton";

export default function StoryCardSkeleton() {
  return (
    <div className="bg-card border border-border rounded-lg p-md whisper-shadow relative min-h-[140px]">
      <div className="flex items-center justify-between mb-2">
        <Skeleton className="h-4 w-28 rounded" />
        <Skeleton className="h-4 w-12 rounded" />
      </div>
      <Skeleton className="h-4 w-3/4 rounded mb-2" />
      <Skeleton className="h-3 w-5/6 rounded mb-2" />
      <Skeleton className="h-3 w-2/5 rounded" />
    </div>
  );
}
