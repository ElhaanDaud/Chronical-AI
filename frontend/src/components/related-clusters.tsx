import Link from "next/link"
import type { StoryCard } from "@/lib/api"
import { HeatBadge } from "@/components/heat-badge"
import { formatRelativeTime } from "@/lib/utils"

type RelatedClustersProps = {
  stories: StoryCard[]
  currentId: string
}

export function RelatedClusters({ stories, currentId }: RelatedClustersProps) {
  const related = stories.filter((s) => s.id !== currentId).slice(0, 4)
  if (related.length === 0) return null

  return (
    <div>
      <h3 className="headline-md mb-md">Related Clusters</h3>
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-md">
        {related.map((story) => (
          <Link
            key={story.id}
            href={`/story/${story.id}`}
            className="block bg-card border border-border rounded-lg p-md hover:hover-shadow hover:-translate-y-0.5 transition-all duration-200"
          >
            <h4 className="headline-md line-clamp-2 mb-2">{story.topic_label}</h4>
            <p className="body-sm text-muted-foreground line-clamp-2 mb-3">{story.latest_commit_message}</p>
            <div className="flex items-center justify-between">
              <HeatBadge heat_score={story.heat_score} />
              <span className="metadata text-muted-foreground">{formatRelativeTime(story.last_updated)}</span>
            </div>
          </Link>
        ))}
      </div>
    </div>
  )
}
