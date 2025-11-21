"use client";

import { useEffect, useState } from "react";
import { StatCard } from "@/components/StatCard";
import { SentimentTimeline } from "@/components/SentimentTimeline";
import { LoadingSpinner } from "@/components/LoadingSpinner";
import {
  MessageSquare,
  TrendingUp,
  AlertTriangle,
  Target,
  BarChart3,
  ThumbsUp,
  ThumbsDown,
  Minus,
} from "lucide-react";
import { DashboardStats, SentimentTimelinePoint } from "@/types";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
  Legend,
} from "recharts";

export default function Home() {
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [timeline, setTimeline] = useState<SentimentTimelinePoint[]>([]);
  const [distribution, setDistribution] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function fetchData() {
      try {
        setLoading(true);

        const [statsRes, timelineRes, distRes] = await Promise.all([
          fetch("/api/stats"),
          fetch("/api/sentiment/timeline?days=7"),
          fetch("/api/distribution"),
        ]);

        if (!statsRes.ok || !timelineRes.ok || !distRes.ok) {
          throw new Error("Failed to fetch data");
        }

        const statsData = await statsRes.json();
        const timelineData = await timelineRes.json();
        const distData = await distRes.json();

        setStats(statsData.data);
        setTimeline(timelineData.data);
        setDistribution(distData.data);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Unknown error");
      } finally {
        setLoading(false);
      }
    }

    fetchData();

    // Auto-refresh every 30 seconds
    const interval = setInterval(fetchData, 30000);
    return () => clearInterval(interval);
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

  const sentimentData = distribution?.sentiment
    ? [
        {
          name: "Positive",
          value: distribution.sentiment.positive_count,
          color: "#22c55e",
        },
        {
          name: "Neutral",
          value: distribution.sentiment.neutral_count,
          color: "#eab308",
        },
        {
          name: "Negative",
          value: distribution.sentiment.negative_count,
          color: "#ef4444",
        },
      ]
    : [];

  const subredditData = distribution?.subreddits?.slice(0, 10) || [];

  return (
    <div className="p-8 space-y-8">
      {/* Header */}
      <div>
        <h1 className="text-4xl font-bold">Dashboard</h1>
        <p className="text-muted-foreground mt-2">
          Real-time sentiment analysis of Tesla Energy discussions on Reddit
        </p>
      </div>

      {/* Stats Grid */}
      {stats && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
          <StatCard
            title="Total Posts"
            value={stats.total_posts.toLocaleString()}
            subtitle="Processed from 14 subreddits"
            icon={MessageSquare}
          />
          <StatCard
            title="Entity Extraction Rate"
            value={`${stats.extraction_rate}%`}
            subtitle="Products & issues identified"
            icon={Target}
          />
          <StatCard
            title="Critical Alerts"
            value={stats.critical_alerts}
            subtitle="Requiring immediate attention"
            icon={AlertTriangle}
            className={stats.critical_alerts > 0 ? "border-red-500" : ""}
          />
          <StatCard
            title="Average Sentiment"
            value={
              stats.avg_sentiment != null
                ? Number(stats.avg_sentiment).toFixed(3)
                : "N/A"
            }
            subtitle={
              (Number(stats.avg_sentiment) || 0) > 0.2
                ? "Positive trend"
                : (Number(stats.avg_sentiment) || 0) < 0
                ? "Negative trend"
                : "Neutral"
            }
            icon={TrendingUp}
          />
        </div>
      )}

      {/* Main Charts */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Sentiment Timeline */}
        <div className="lg:col-span-2">
          <SentimentTimeline data={timeline} />
        </div>

        {/* Sentiment Distribution Pie */}
        <Card>
          <CardHeader>
            <CardTitle>Sentiment Distribution</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="h-[300px]">
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={sentimentData}
                    cx="50%"
                    cy="50%"
                    labelLine={false}
                    label={({ name, percent }) =>
                      `${name}: ${((percent || 0) * 100).toFixed(0)}%`
                    }
                    outerRadius={80}
                    fill="#8884d8"
                    dataKey="value"
                  >
                    {sentimentData.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={entry.color} />
                    ))}
                  </Pie>
                  <Tooltip />
                  <Legend />
                </PieChart>
              </ResponsiveContainer>
            </div>
            <div className="grid grid-cols-3 gap-4 mt-4">
              <div className="text-center">
                <ThumbsUp className="w-5 h-5 mx-auto text-green-500" />
                <p className="text-2xl font-bold mt-1">
                  {distribution?.sentiment?.positive_count || 0}
                </p>
                <p className="text-xs text-muted-foreground">Positive</p>
              </div>
              <div className="text-center">
                <Minus className="w-5 h-5 mx-auto text-yellow-500" />
                <p className="text-2xl font-bold mt-1">
                  {distribution?.sentiment?.neutral_count || 0}
                </p>
                <p className="text-xs text-muted-foreground">Neutral</p>
              </div>
              <div className="text-center">
                <ThumbsDown className="w-5 h-5 mx-auto text-red-500" />
                <p className="text-2xl font-bold mt-1">
                  {distribution?.sentiment?.negative_count || 0}
                </p>
                <p className="text-xs text-muted-foreground">Negative</p>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Posts by Subreddit */}
        <Card>
          <CardHeader>
            <CardTitle>Top Subreddits</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="h-[300px]">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={subredditData} layout="vertical">
                  <XAxis type="number" />
                  <YAxis
                    dataKey="subreddit"
                    type="category"
                    width={100}
                    tick={{ fontSize: 12 }}
                  />
                  <Tooltip />
                  <Bar dataKey="count" fill="#8b5cf6" />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Footer */}
      <div className="text-center text-sm text-muted-foreground">
        Dashboard updates automatically every 30 seconds
      </div>
    </div>
  );
}
