"use client";

import Link from "next/link";
import type { StoryCard as StoryCardType } from "@/lib/api";
import { formatRelativeTime, cn } from "@/lib/utils";

export default function FeaturedCard({ story }: { story: StoryCardType }) {
  const category = story.topic_tokens?.[0] ?? story.topic_label;
  const isLive = story.heat_score >= 5.0;
  return (
    <Link href={`/story/${story.id}`} className="block mb-6">
      <div
        className={cn(
          "bg-card border border-border rounded-lg p-lg whisper-shadow hover:hover-shadow hover:-translate-y-0.5 transition-all duration-200 relative"
        )}
      >
        <div className="hidden dark:block absolute -top-6 -left-6 w-60 h-60 rounded-full bg-secondary/10 blur-3xl" aria-hidden="true" />

        <div className="flex items-center justify-between mb-2">
          <div className="flex items-center gap-2">
            <span className="label-caps-sm bg-secondary-container text-secondary-foreground px-3 py-1 rounded-full">{category}</span>
            <span className="metadata text-muted-foreground">{formatRelativeTime(story.last_updated)}</span>
          </div>
          {isLive && <span className="label-caps-sm bg-secondary/15 text-secondary px-3 py-1 rounded-full">LIVE</span>}
        </div>
        <h2 className="headline-md line-clamp-2 mb-2">{story.topic_label}</h2>
        <p className="body-md text-muted-foreground line-clamp-2 mb-2">{story.latest_commit_message}</p>
        <div className="flex items-center justify-between mt-2 text-sm text-muted-foreground">
          <span className="metadata">{story.article_count} sources</span>
          <span className="label-caps-sm text-secondary">DEEP DIVE →</span>
        </div>
      </div>
    </Link>
  );
}
