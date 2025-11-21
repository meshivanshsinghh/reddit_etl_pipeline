"use client";

import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from "recharts";
import { format } from "date-fns";
import { SentimentTimelinePoint } from "@/types";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  CardDescription,
} from "@/components/ui/card";

interface SentimentTimelineProps {
  data: SentimentTimelinePoint[];
  title?: string;
  description?: string;
}

export function SentimentTimeline({
  data,
  title = "Sentiment Over Time",
  description = "Hourly sentiment analysis from Reddit posts",
}: SentimentTimelineProps) {
  // Transform data for chart
  const chartData = data.map((point) => ({
    time: format(new Date(point.time), "MMM dd HH:mm"),
    sentiment: Number(point.sentiment) || 0,
    posts: point.posts || 0,
  }));

  return (
    <Card>
      <CardHeader>
        <CardTitle>{title}</CardTitle>
        {description && <CardDescription>{description}</CardDescription>}
      </CardHeader>
      <CardContent>
        <div className="h-[400px]">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart
              data={chartData}
              margin={{ top: 5, right: 30, left: 20, bottom: 5 }}
            >
              <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
              <XAxis
                dataKey="time"
                className="text-xs"
                tick={{ fill: "currentColor" }}
              />
              <YAxis
                yAxisId="left"
                domain={[-1, 1]}
                label={{
                  value: "Sentiment",
                  angle: -90,
                  position: "insideLeft",
                }}
                tick={{ fill: "currentColor" }}
              />
              <YAxis
                yAxisId="right"
                orientation="right"
                label={{ value: "Posts", angle: 90, position: "insideRight" }}
                tick={{ fill: "currentColor" }}
              />
              <Tooltip
                contentStyle={{
                  backgroundColor: "hsl(var(--card))",
                  border: "1px solid hsl(var(--border))",
                  borderRadius: "8px",
                }}
                formatter={(value: number, name: string) => {
                  if (name === "sentiment")
                    return [value.toFixed(3), "Sentiment"];
                  return [value, "Posts"];
                }}
              />
              <Legend />
              <Line
                yAxisId="left"
                type="monotone"
                dataKey="sentiment"
                stroke="#3b82f6"
                strokeWidth={2}
                dot={false}
                name="Sentiment"
              />
              <Line
                yAxisId="right"
                type="monotone"
                dataKey="posts"
                stroke="#8b5cf6"
                strokeWidth={2}
                dot={false}
                name="Posts"
              />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </CardContent>
    </Card>
  );
}
