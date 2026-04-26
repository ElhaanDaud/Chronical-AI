import Link from "next/link"
import { notFound } from "next/navigation"
import { fetchStory, fetchStories, type StoryCard, type StoryDetail } from "@/lib/api"
import { HeatBadge } from "@/components/heat-badge"
import { CommitLog } from "@/components/commit-log"
import { ExecutiveSynthesis } from "@/components/executive-synthesis"
import { EntityChips } from "@/components/entity-chips"
import { Sparkline } from "@/components/sparkline"
import { RelatedClusters } from "@/components/related-clusters"
import MaterialIcon from "@/components/material-icon"
import { formatRelativeTime } from "@/lib/utils"

type PageProps = { params: { id: string } }

export default async function StoryDetailPage({ params }: PageProps) {
  let story: StoryDetail
  try {
    story = await fetchStory(params.id)
  } catch {
    notFound()
  }

  let allStories: StoryCard[] = []
  try {
    allStories = await fetchStories()
  } catch {
    allStories = []
  }

  const entities: string[] = story.entity_fingerprint && story.entity_fingerprint.length > 0 ? story.entity_fingerprint : story.topic_tokens

  return (
    <div className="space-y-xl">
      <Link
        href="/"
        className="inline-flex items-center gap-1 metadata text-muted-foreground hover:text-secondary transition-colors"
      >
        <MaterialIcon name="arrow_back" size={16} />
        Back to Intelligence Feed
      </Link>

      <div className="space-y-lg">
        <div className="flex items-center gap-3 flex-wrap">
          <HeatBadge heat_score={story.heat_score} />
          <span className="metadata text-muted-foreground">
            Synthesized: {formatRelativeTime(story.updated_at)} · {story.article_count} sources
          </span>
        </div>

        <div className="flex items-start justify-between gap-lg">
          <h1 className="display-xl max-w-3xl">{story.topic_label}</h1>
          <Sparkline commits={story.commits} className="hidden md:flex shrink-0 pt-2" />
        </div>

        {story.commits[0] && (
          <p className="body-lg text-muted-foreground max-w-2xl">
            {story.commits[0].detail}
          </p>
        )}
      </div>

      <div className="grid grid-cols-1 md:grid-cols-12 gap-lg">
        <div className="md:col-span-8 space-y-xl">
          <ExecutiveSynthesis storyId={story.id} />
          <CommitLog commits={story.commits} />
        </div>

        <aside className="md:col-span-4 space-y-lg">
          <EntityChips entities={entities} />

          <div className="bg-card border border-border rounded-lg p-lg">
            <h3 className="label-caps text-muted-foreground mb-md flex items-center gap-2">
              <MaterialIcon name="query_stats" size={18} />
              CLUSTER DATA
            </h3>
            <div className="space-y-3">
              <div className="flex justify-between items-center">
                <span className="body-sm text-muted-foreground">Articles</span>
                <span className="body-sm font-medium">{story.article_count}</span>
              </div>
              <div className="flex justify-between items-center">
                <span className="body-sm text-muted-foreground">Revisions</span>
                <span className="body-sm font-medium">{story.commits.length}</span>
              </div>
              <div className="flex justify-between items-center">
                <span className="body-sm text-muted-foreground">Status</span>
                <span className="label-caps-sm">{story.state.toUpperCase()}</span>
              </div>
              <div className="flex justify-between items-center">
                <span className="body-sm text-muted-foreground">Created</span>
                <span className="metadata">{new Date(story.created_at).toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" })}</span>
              </div>
            </div>
          </div>

          <div className="md:hidden">
            <Sparkline commits={story.commits} />
          </div>
        </aside>
      </div>

      <RelatedClusters stories={allStories} currentId={story.id} />
    </div>
  )
}
