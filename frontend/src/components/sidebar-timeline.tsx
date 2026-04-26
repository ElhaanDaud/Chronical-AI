"use client";

import type { StoryCard as StoryCardType } from "@/lib/api";
import { formatRelativeTime } from "@/lib/utils";

export default function SidebarTimeline({ stories }: { stories: StoryCardType[] }) {
  const entries = (stories ?? [])
    .slice()
    .sort((a, b) => new Date(b.last_updated).getTime() - new Date(a.last_updated).getTime())
    .slice(0, 8);

  return (
    <section className="bg-card border border-border rounded-lg p-md whisper-shadow">
      <div className="mb-md">
        <span className="label-caps text-muted-foreground">Commit Timeline</span>
      </div>
      <div className="border-l-2 border-border ml-2 pl-4">
        {entries.map((story, idx) => (
          <div key={story.id} className="flex items-start gap-3 mb-4 relative">
            <span
              className={idx === 0
                ? 'w-3 h-3 shrink-0 rounded-full bg-secondary mt-1.5'
                : 'w-2 h-2 shrink-0 rounded-full bg-muted-foreground mt-2'}
            />
            <div className="flex-1">
              <div className="flex items-center gap-2 text-sm text-muted-foreground mb-1">
                <span className="body-sm">{story.topic_label}</span>
                <span className="ml-2 text-xs">{formatRelativeTime(story.last_updated)}</span>
              </div>
              <div className="text-sm text-muted-foreground line-clamp-1">{story.latest_commit_message}</div>
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}
