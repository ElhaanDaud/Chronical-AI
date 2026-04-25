"use client";

import Link from "next/link";
import { Card, CardContent, CardHeader, CardTitle, CardDescription, CardFooter } from "@/components/ui/card";
import { HeatBadge } from "./heat-badge";
import { formatRelativeTime } from "@/lib/utils";
import type { StoryCard as StoryCardType } from "@/lib/api";

type StoryCardProps = {
  story: StoryCardType
}

function StoryCard({ story }: StoryCardProps) {
  return (
    <Link href={`/story/${story.id}`} className="block">
      <Card>
        <CardHeader>
          <CardTitle>{story.topic_label}</CardTitle>
        </CardHeader>
        <CardContent>
          <CardDescription>{story.latest_commit_message}</CardDescription>
        </CardContent>
        <CardFooter className="flex items-center justify-between gap-4">
          <HeatBadge state={story.state} heat_score={story.heat_score} />
          <span className="text-xs text-muted-foreground">
            {story.article_count} articles • {formatRelativeTime(story.last_updated)}
          </span>
        </CardFooter>
      </Card>
    </Link>
  )
}

export { StoryCard }
