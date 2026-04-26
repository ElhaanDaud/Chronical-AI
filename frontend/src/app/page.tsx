import type { StoryCard as StoryCardType } from "@/lib/api";
import { fetchStories } from "../lib/api";
import FeaturedCard from "@/components/featured-card";
import StoryCard from "@/components/story-card";
import MorningDigest from "@/components/morning-digest";
import SidebarTimeline from "@/components/sidebar-timeline";
import LiveBadge from "@/components/live-badge";
import MaterialIcon from "@/components/material-icon";

export const dynamic = "force-dynamic";
export const revalidate = 300;

export default async function Page() {
  let stories: StoryCardType[] = [];
  try {
    stories = await fetchStories();
  } catch {
    stories = [];
  }

  const hasLive = stories.some((s) => s.heat_score >= 5.0);

  const digestStories = stories
    .slice()
    .sort((a, b) => b.heat_score - a.heat_score)
    .slice(0, 5);
  const timelineStories = stories
    .slice()
    .sort((a, b) => new Date(b.last_updated).getTime() - new Date(a.last_updated).getTime())
    .slice(0, 8);

  return (
    <section className="p-6">
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-4">
          <h1 className="headline-lg font-serif">Intelligence Feed</h1>
          {hasLive && <LiveBadge />}
        </div>
        <div className="flex items-center gap-2">
          <span className="label-caps-sm text-muted-foreground bg-card border border-border px-3 py-1 rounded-full">{stories.length} ACTIVE THREADS</span>
        </div>
      </div>

      <div className="grid grid-cols-12 gap-gutter">
        <div className="col-span-12 lg:col-span-8">
          {stories.length > 0 ? (
            <>
              <FeaturedCard story={stories[0]} />
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-md mt-6">
                {stories.slice(1).map((s) => (
                  <StoryCard key={s.id} story={s} />
                ))}
              </div>
            </>
          ) : (
            <div className="bg-card border border-border rounded-lg p-md whisper-shadow h-56 flex flex-col items-center justify-center">
              <MaterialIcon name="search_off" className="text-4xl text-muted-foreground" />
              <div className="mt-2 text-muted-foreground">No active stories</div>
              <span className="mt-3 body-sm text-muted-foreground">Use the Ingest Refresh button to load feeds</span>
            </div>
          )}
        </div>

        <aside className="col-span-12 lg:col-span-4 space-y-4">
          <MorningDigest stories={digestStories} />
          <SidebarTimeline stories={timelineStories} />
        </aside>
      </div>
    </section>
  );
}
