"use client";

import Link from "next/link";
import type { StoryCard as StoryCardType } from "@/lib/api";

export default function MorningDigest({ stories }: { stories: StoryCardType[] }) {
  const top5 = (stories ?? []).slice(0, 5);
  return (
    <section className="bg-card border border-border rounded-lg p-md whisper-shadow">
      <div className="mb-md">
        <span className="label-caps text-muted-foreground">Morning Catch-up</span>
      </div>
      <ul className="list-disc pl-5 space-y-2">
        {top5.map((s) => (
          <li key={s.id}>
            <Link href={`/story/${s.id}`} className="body-sm text-muted-foreground hover:underline">
              {s.latest_commit_message}
            </Link>
          </li>
        ))}
      </ul>
    </section>
  );
}
