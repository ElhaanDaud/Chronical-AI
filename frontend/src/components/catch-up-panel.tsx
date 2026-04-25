"use client";

import React, { useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { Button } from "@/components/ui/button";
import { fetchCatchUp } from "../lib/api";

type CatchUpPanelProps = {
  storyId: string;
};

function CatchUpPanel({ storyId }: CatchUpPanelProps) {
  const [loading, setLoading] = useState(false);
  const [data, setData] = useState<{ narrative: string; commit_count: number; time_span_days: number } | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetchCatchUp(storyId);
      setData({ narrative: res.narrative, commit_count: res.commit_count, time_span_days: res.time_span_days });
    } catch {
      setError("Failed to load catch-up.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle>Catch Up</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="space-y-3">
          <Button onClick={load} variant="default">Catch Me Up</Button>
          {loading && <Skeleton className="h-28" />}
          {!loading && data && (
            <div className="text-sm space-y-2">
              <p>{data.narrative}</p>
              <p className="text-muted-foreground">
                {data.commit_count} commit{data.commit_count === 1 ? "" : "s"} • {data.time_span_days} day{data.time_span_days === 1 ? "" : "s"}
              </p>
            </div>
          )}
          {!loading && error && <p className="text-destructive text-sm">{error}</p>}
        </div>
      </CardContent>
    </Card>
  );
}

export { CatchUpPanel }
