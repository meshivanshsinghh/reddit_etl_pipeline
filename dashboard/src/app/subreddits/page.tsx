"use client";

import { useEffect, useState } from "react";
import { SubredditStats } from "@/types";
import { LoadingSpinner } from "@/components/LoadingSpinner";
import { SentimentBadge } from "@/components/SentimentBadge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Badge } from "@/components/ui/badge";
import { MessageSquare } from "lucide-react";

export default function SubredditsPage() {
  const [subreddits, setSubreddits] = useState<SubredditStats[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [sortBy, setSortBy] = useState<"posts" | "sentiment">("posts");

  useEffect(() => {
    async function fetchSubreddits() {
      try {
        setLoading(true);
        const response = await fetch("/api/subreddits");

        if (!response.ok) throw new Error("Failed to fetch subreddit stats");

        const data = await response.json();
        setSubreddits(data.data);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Unknown error");
      } finally {
        setLoading(false);
      }
    }

    fetchSubreddits();
    // Auto-refresh disabled for better UX
  }, []);

  if (loading) {
    return (
      <div className="p-8">
        <LoadingSpinner size="lg" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-8">
        <div className="bg-destructive/10 border border-destructive text-destructive px-4 py-3 rounded">
          Error: {error}
        </div>
      </div>
    );
  }

  // Sort subreddits
  const sortedSubreddits = [...subreddits].sort((a, b) => {
    if (sortBy === "posts") {
      return b.post_count - a.post_count;
    } else {
      return (b.avg_sentiment || 0) - (a.avg_sentiment || 0);
    }
  });

  const totalPosts = subreddits.reduce((sum, s) => sum + s.post_count, 0);

  return (
    <div className="p-8 space-y-8">
      {/* Header */}
      <div>
        <h1 className="text-4xl font-bold">Subreddits</h1>
        <p className="text-muted-foreground mt-2">
          Analysis across {subreddits.length} Tesla-related communities
        </p>
      </div>

      {/* Stats Overview */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <Card>
          <CardHeader>
            <CardTitle className="text-sm font-medium text-muted-foreground">
              Total Subreddits
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold">{subreddits.length}</div>
            <p className="text-xs text-muted-foreground mt-1">
              Communities monitored
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-sm font-medium text-muted-foreground">
              Total Posts
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold">
              {totalPosts.toLocaleString()}
            </div>
            <p className="text-xs text-muted-foreground mt-1">
              Across all subreddits
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-sm font-medium text-muted-foreground">
              Most Active
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              r/{sortedSubreddits[0]?.subreddit || "N/A"}
            </div>
            <p className="text-xs text-muted-foreground mt-1">
              {sortedSubreddits[0]?.post_count || 0} posts
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Sort Controls */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle>Subreddit Comparison</CardTitle>
            <div className="flex gap-2">
              <button
                onClick={() => setSortBy("posts")}
                className={`px-4 py-2 rounded-md text-sm font-medium transition-colors ${
                  sortBy === "posts"
                    ? "bg-primary text-primary-foreground"
                    : "bg-secondary text-secondary-foreground hover:bg-secondary/80"
                }`}
              >
                Sort by Posts
              </button>
              <button
                onClick={() => setSortBy("sentiment")}
                className={`px-4 py-2 rounded-md text-sm font-medium transition-colors ${
                  sortBy === "sentiment"
                    ? "bg-primary text-primary-foreground"
                    : "bg-secondary text-secondary-foreground hover:bg-secondary/80"
                }`}
              >
                Sort by Sentiment
              </button>
            </div>
          </div>
        </CardHeader>
        <CardContent>
          {sortedSubreddits.length === 0 ? (
            <div className="text-center py-8 text-muted-foreground">
              <MessageSquare className="w-16 h-16 mx-auto mb-4" />
              <p>No subreddit data available</p>
            </div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Subreddit</TableHead>
                  <TableHead className="text-right">Posts</TableHead>
                  <TableHead className="text-right">Avg Sentiment</TableHead>
                  <TableHead className="text-right">Positive %</TableHead>
                  <TableHead className="text-right">Negative %</TableHead>
                  <TableHead className="text-right">Neutral %</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {sortedSubreddits.map((subreddit) => (
                  <TableRow
                    key={subreddit.subreddit}
                    className="hover:bg-muted/50"
                  >
                    <TableCell>
                      <div className="flex items-center gap-2">
                        <MessageSquare className="w-4 h-4 text-muted-foreground" />
                        <span className="font-medium">
                          r/{subreddit.subreddit}
                        </span>
                      </div>
                    </TableCell>
                    <TableCell className="text-right font-semibold">
                      {subreddit.post_count.toLocaleString()}
                    </TableCell>
                    <TableCell className="text-right">
                      <SentimentBadge sentiment={subreddit.avg_sentiment} />
                    </TableCell>
                    <TableCell className="text-right">
                      <span className="text-green-500 font-medium">
                        {subreddit.positive_percent
                          ? Number(subreddit.positive_percent).toFixed(1)
                          : "0.0"}
                        %{" "}
                      </span>
                    </TableCell>
                    <TableCell className="text-right">
                      <span className="text-red-500 font-medium">
                        {subreddit.negative_percent
                          ? Number(subreddit.negative_percent).toFixed(1)
                          : "0.0"}
                        %{" "}
                      </span>
                    </TableCell>
                    <TableCell className="text-right">
                      <span className="text-yellow-500 font-medium">
                        {subreddit.neutral_percent
                          ? Number(subreddit.neutral_percent).toFixed(1)
                          : "0.0"}
                        %{" "}
                      </span>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
