import Link from "next/link";
import { notFound } from "next/navigation";
import { fetchStory } from "../../../lib/api";
import { HeatBadge } from "@/components/heat-badge";
import { CommitLog } from "@/components/commit-log";
import { CatchUpPanel } from "@/components/catch-up-panel";
import { Card, CardHeader, CardContent, CardTitle, CardDescription } from "@/components/ui/card";

type PageProps = { params: { id: string } };

export default async function StoryDetail({ params }: PageProps) {
  let story;
  try {
    story = await fetchStory(params.id);
  } catch {
    notFound();
  }

  return (
    <div className="space-y-6">
      <Link href="/" className="text-sm text-primary hover:underline">&larr; Back</Link>
      <Card>
        <CardHeader>
          <CardTitle>{story.topic_label}</CardTitle>
        </CardHeader>
        <CardContent>
          <CardDescription className="flex items-center gap-2">
            <HeatBadge state={story.state} heat_score={story.heat_score} />
            <span>{story.article_count} articles &middot; Created {new Date(story.created_at).toLocaleDateString()}</span>
          </CardDescription>
        </CardContent>
      </Card>

      <CatchUpPanel storyId={story.id} />
      <CommitLog commits={story.commits} />
    </div>
  );
}
