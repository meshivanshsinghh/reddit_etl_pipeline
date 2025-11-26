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
  ReferenceLine,
  Area,
  AreaChart,
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
  title = "Sentiment Trends",
  description = "7-day sentiment analysis with moving average",
}: SentimentTimelineProps) {
  // Calculate 24-hour moving average for smoother trends
  const calculateMovingAverage = (data: any[], windowSize: number = 24) => {
    return data.map((point, index) => {
      const start = Math.max(0, index - windowSize + 1);
      const window = data.slice(start, index + 1);
      const avg = window.reduce((sum, p) => sum + (Number(p.sentiment) || 0), 0) / window.length;
      return { ...point, movingAvg: Number(avg.toFixed(3)) };
    });
  };

  // Transform and aggregate data
  const rawData = data.map((point) => ({
    time: new Date(point.time),
    timeStr: format(new Date(point.time), "MMM dd HH:mm"),
    sentiment: Number(point.sentiment) || 0,
    posts: point.posts || 0,
  }));

  // Add moving average
  const chartData = calculateMovingAverage(rawData).map(point => ({
    ...point,
    timeStr: format(point.time, "MMM dd HH:mm"),
  }));

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base font-medium">{title}</CardTitle>
        {description && <CardDescription>{description}</CardDescription>}
      </CardHeader>
      <CardContent>
        <div className="h-[350px]">
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart
              data={chartData}
              margin={{ top: 10, right: 30, left: 0, bottom: 0 }}
            >
              <defs>
                <linearGradient id="sentimentGradient" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.3}/>
                  <stop offset="95%" stopColor="#3b82f6" stopOpacity={0}/>
                </linearGradient>
                <linearGradient id="trendGradient" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#10b981" stopOpacity={0.4}/>
                  <stop offset="95%" stopColor="#10b981" stopOpacity={0}/>
                </linearGradient>
              </defs>
              
              <CartesianGrid strokeDasharray="3 3" className="stroke-muted" opacity={0.3} />
              
              <XAxis
                dataKey="timeStr"
                className="text-xs"
                tick={{ fill: "currentColor", fontSize: 11 }}
                interval="preserveStartEnd"
                minTickGap={50}
              />
              
              <YAxis
                domain={[-1, 1]}
                ticks={[-1, -0.5, 0, 0.5, 1]}
                tick={{ fill: "currentColor", fontSize: 12 }}
              />

              {/* Sentiment zones */}
              <ReferenceLine 
                y={0.2} 
                stroke="#22c55e" 
                strokeDasharray="3 3" 
                strokeOpacity={0.5}
                label={{ value: "Positive", fill: "#22c55e", fontSize: 11, position: "right" }}
              />
              <ReferenceLine 
                y={0} 
                stroke="#94a3b8" 
                strokeDasharray="3 3" 
                strokeOpacity={0.5}
              />
              <ReferenceLine 
                y={-0.2} 
                stroke="#ef4444" 
                strokeDasharray="3 3" 
                strokeOpacity={0.5}
                label={{ value: "Negative", fill: "#ef4444", fontSize: 11, position: "right" }}
              />
              
              <Tooltip
                contentStyle={{
                  backgroundColor: "hsl(var(--card))",
                  border: "1px solid hsl(var(--border))",
                  borderRadius: "8px",
                  padding: "8px 12px",
                }}
                formatter={(value: number, name: string) => {
                  if (name === "Raw Sentiment" || name === "Trend") {
                    const sentiment = Number(value);
                    const label = sentiment > 0.2 ? "Positive" : sentiment < -0.2 ? "Negative" : "Neutral";
                    return [
                      <span key={name}>
                        {value.toFixed(3)} <span className="text-muted-foreground">({label})</span>
                      </span>,
                      name
                    ];
                  }
                  return [value, name];
                }}
                labelStyle={{ fontWeight: 600, marginBottom: 4 }}
              />
              
              <Legend 
                wrapperStyle={{ paddingTop: "10px" }}
                iconType="line"
              />

              {/* Raw sentiment with subtle area fill */}
              <Area
                type="monotone"
                dataKey="sentiment"
                stroke="#3b82f6"
                strokeWidth={1.5}
                fill="url(#sentimentGradient)"
                name="Raw Sentiment"
                strokeOpacity={0.6}
              />

              {/* Moving average trend line (thicker, more prominent) */}
              <Line
                type="monotone"
                dataKey="movingAvg"
                stroke="#10b981"
                strokeWidth={3}
                dot={false}
                name="Trend (24h avg)"
              />
            </AreaChart>
          </ResponsiveContainer>
        </div>

        {/* Legend explanation */}
        <div className="flex items-center justify-center gap-6 mt-4 text-xs text-muted-foreground">
          <div className="flex items-center gap-2">
            <div className="w-3 h-3 rounded-full bg-blue-500"></div>
            <span>Hourly sentiment</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-3 h-3 rounded-full bg-green-500"></div>
            <span>24-hour trend</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="text-green-500">━━</span>
            <span>Positive zone (+0.2)</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="text-red-500">━━</span>
            <span>Negative zone (-0.2)</span>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
