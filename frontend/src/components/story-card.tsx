"use client";

import Link from "next/link";
import { Card, CardContent, CardHeader, CardDescription, CardFooter } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
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
          <div className="flex flex-wrap gap-1.5">
            {story.topic_tokens.map((token) => (
              <Badge key={token} variant="secondary" className="text-xs font-medium">
                {token}
              </Badge>
            ))}
          </div>
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
