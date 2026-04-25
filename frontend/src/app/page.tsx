import { fetchStories } from "../lib/api";
import { StoryCard } from "@/components/story-card";

export const dynamic = "force-dynamic";
export const revalidate = 300;

export default async function Page() {
  const stories = await fetchStories();
  return (
    <>
      <h1 className="text-2xl font-bold mb-6">Chronicle — News that evolves</h1>
      {stories.length === 0 ? (
        <p className="text-muted-foreground">No stories found.</p>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {stories.map((s) => (
            <StoryCard key={s.id} story={s} />
          ))}
        </div>
      )}
    </>
  );
}
