"use client";

import { Skeleton } from "@/components/ui/skeleton";

export default function StoryDetailSkeleton() {
  return (
    <div className="flex flex-col gap-6 p-6 w-full">
      <Skeleton className="h-48 md:h-72 w-full rounded" />
      <Skeleton className="h-6 w-3/4 rounded" />
      <Skeleton className="h-4 w-5/6 rounded" />
      <Skeleton className="h-4 w-4/6 rounded" />
      <Skeleton className="h-3 w-3/5 rounded" />
    </div>
  );
}
