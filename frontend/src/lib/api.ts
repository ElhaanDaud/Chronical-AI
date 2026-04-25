export interface StoryCard {
  id: string;
  topic_label: string;
  topic_tokens: string[];
  latest_commit_message: string;
  heat_score: number;
  state: "active" | "cooling" | "hibernated";
  article_count: number;
  last_updated: string;
}

export interface CommitResponse {
  id: string;
  message: string;
  detail: string;
  commit_date: string;
  source_count: number;
  source_urls: string[];
}

export interface StoryDetail {
  id: string;
  topic_label: string;
  topic_tokens: string[];
  state: "active" | "cooling" | "hibernated";
  heat_score: number;
  article_count: number;
  commits: CommitResponse[];
  created_at: string;
  updated_at: string;
}

export interface CatchUpResponse {
  story_id: string;
  narrative: string;
  commit_count: number;
  time_span_days: number;
}

export interface SearchResult {
  id: string;
  title: string;
  summary: string | null;
  source: string;
  published_at: string;
  cluster_id: string | null;
}

const API_BASE = (process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000");
const SERVER_API_BASE = (process.env.API_URL || API_BASE);

export async function fetchStories(): Promise<StoryCard[]> {
  const res = await fetch(`${SERVER_API_BASE}/api/stories`, {
    next: { revalidate: 300 },
  });
  if (!res.ok) throw new Error(`API error: ${res.status}`);
  return res.json();
}

export async function fetchStory(id: string): Promise<StoryDetail> {
  const res = await fetch(`${SERVER_API_BASE}/api/stories/${id}`, {
    next: { revalidate: 60 },
  });
  if (!res.ok) throw new Error(`API error: ${res.status}`);
  return res.json();
}

export async function fetchCatchUp(id: string): Promise<CatchUpResponse> {
  const res = await fetch(`${API_BASE}/api/stories/${id}/catchup`);
  if (!res.ok) throw new Error(`API error: ${res.status}`);
  return res.json();
}

export async function searchArticles(q: string): Promise<SearchResult[]> {
  const res = await fetch(`${SERVER_API_BASE}/api/search?q=${encodeURIComponent(q)}`);
  if (!res.ok) throw new Error(`API error: ${res.status}`);
  return res.json();
}
