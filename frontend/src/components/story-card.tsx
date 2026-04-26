"use client";

import Link from "next/link";
import { formatRelativeTime } from "@/lib/utils";
import type { StoryCard as StoryCardType } from "@/lib/api";
import { cn } from "@/lib/utils";
import { HeatBadge } from "./heat-badge";

type StoryCardProps = {
  story: StoryCardType
}

export default function StoryCard({ story }: StoryCardProps) {
  return (
    <Link href={`/story/${story.id}`} className="block">
      <div className={cn("bg-card border border-border rounded-lg p-md whisper-shadow hover:hover-shadow hover:-translate-y-0.5 transition-all duration-200")}>
        <div className="flex items-center justify-between mb-2">
          <span className="metadata text-muted-foreground">{formatRelativeTime(story.last_updated)}</span>
          <HeatBadge heat_score={story.heat_score} />
        </div>
        <h3 className="headline-md line-clamp-2 mb-2">{story.topic_label}</h3>
        <p className="body-sm text-muted-foreground line-clamp-2">{story.latest_commit_message}</p>
        <div className="mt-2 text-xs text-muted-foreground">{story.article_count} sources</div>
      </div>
    </Link>
  )
}
