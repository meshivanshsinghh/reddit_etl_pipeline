"use client";

import { useEffect, useState } from "react";
import { Topic, Cluster } from "@/types";
import { LoadingSpinner } from "@/components/LoadingSpinner";
import { SentimentBadge } from "@/components/SentimentBadge";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  CardDescription,
} from "@/components/ui/card";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Badge } from "@/components/ui/badge";
import { TrendingUp, Layers } from "lucide-react";

export default function InsightsPage() {
  const [topics, setTopics] = useState<Topic[]>([]);
  const [clusters, setClusters] = useState<Cluster[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function fetchData() {
      try {
        setLoading(true);

        const [topicsRes, clustersRes] = await Promise.all([
          fetch("/api/topics?limit=20"),
          fetch("/api/clusters"),
        ]);

        if (!topicsRes.ok || !clustersRes.ok) {
          throw new Error("Failed to fetch insights data");
        }

        const topicsData = await topicsRes.json();
        const clustersData = await clustersRes.json();

        setTopics(topicsData.data);
        setClusters(clustersData.data);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Unknown error");
      } finally {
        setLoading(false);
      }
    }

    fetchData();

    // Auto-refresh every 2 minutes
    const interval = setInterval(fetchData, 120000);
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

  return (
    <div className="p-8 space-y-8">
      {/* Header */}
      <div>
        <h1 className="text-4xl font-bold">Insights</h1>
        <p className="text-muted-foreground mt-2">
          Topic extraction and issue clustering analysis
        </p>
      </div>

      {/* Stats Overview */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <Card>
          <CardHeader>
            <CardTitle className="text-sm font-medium text-muted-foreground flex items-center gap-2">
              <TrendingUp className="w-4 h-4" />
              Keywords Extracted
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold">{topics.length}</div>
            <p className="text-xs text-muted-foreground mt-1">
              Using TF-IDF analysis
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-sm font-medium text-muted-foreground flex items-center gap-2">
              <Layers className="w-4 h-4" />
              Issue Clusters
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold">{clusters.length}</div>
            <p className="text-xs text-muted-foreground mt-1">
              K-Means clustering
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Topic Extraction Section */}
      <Card>
        <CardHeader>
          <CardTitle>Top Keywords</CardTitle>
          <CardDescription>
            Most significant keywords extracted from posts using TF-IDF
          </CardDescription>
        </CardHeader>
        <CardContent>
          {topics.length === 0 ? (
            <div className="text-center py-8 text-muted-foreground">
              No topics extracted yet. Run the topic extraction DAG in Airflow.
            </div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Keyword</TableHead>
                  <TableHead>Subreddit</TableHead>
                  <TableHead className="text-right">TF-IDF Score</TableHead>
                  <TableHead className="text-right">Post Count</TableHead>
                  <TableHead className="text-right">Avg Sentiment</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {topics.map((topic) => (
                  <TableRow key={topic.id}>
                    <TableCell className="font-medium">
                      {topic.keyword}
                    </TableCell>
                    <TableCell>
                      <Badge variant="outline">r/{topic.subreddit}</Badge>
                    </TableCell>
                    <TableCell className="text-right font-mono text-sm">
                      {Number(topic.score).toFixed(4)}
                    </TableCell>
                    <TableCell className="text-right">
                      {topic.post_count}
                    </TableCell>
                    <TableCell className="text-right">
                      <SentimentBadge sentiment={topic.avg_sentiment} />
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>

      {/* Issue Clusters Section */}
      <Card>
        <CardHeader>
          <CardTitle>Issue Clusters</CardTitle>
          <CardDescription>
            Related posts grouped by similarity using K-Means clustering
          </CardDescription>
        </CardHeader>
        <CardContent>
          {clusters.length === 0 ? (
            <div className="text-center py-8 text-muted-foreground">
              No clusters identified yet. Run the topic extraction DAG in
              Airflow.
            </div>
          ) : (
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
              {clusters.map((cluster) => (
                <Card key={cluster.id} className="border-2">
                  <CardHeader>
                    <div className="flex items-start justify-between">
                      <div className="flex-1">
                        <div className="flex items-center gap-2 mb-2">
                          <Badge>Cluster {cluster.cluster_id}</Badge>
                          <Badge variant="outline">{cluster.severity}</Badge>
                        </div>
                        <CardTitle className="text-lg">
                          {cluster.cluster_name}
                        </CardTitle>
                      </div>
                      <SentimentBadge sentiment={cluster.avg_sentiment} />
                    </div>
                  </CardHeader>
                  <CardContent className="space-y-3">
                    <div className="flex justify-between items-center">
                      <span className="text-sm text-muted-foreground">
                        Posts in cluster
                      </span>
                      <span className="text-lg font-semibold">
                        {cluster.post_count}
                      </span>
                    </div>

                    <div className="flex justify-between items-center">
                      <span className="text-sm text-muted-foreground">
                        Avg Sentiment
                      </span>
                      <span className="text-lg font-semibold">
                        {Number(cluster.avg_sentiment).toFixed(3)}
                      </span>
                    </div>

                    {cluster.keywords && cluster.keywords.length > 0 && (
                      <div>
                        <p className="text-xs font-medium text-muted-foreground mb-2">
                          Top Keywords:
                        </p>
                        <div className="flex flex-wrap gap-1">
                          {cluster.keywords.slice(0, 5).map((keyword, idx) => (
                            <Badge
                              key={idx}
                              variant="secondary"
                              className="text-xs"
                            >
                              {keyword}
                            </Badge>
                          ))}
                        </div>
                      </div>
                    )}

                    <div className="text-xs text-muted-foreground border-t pt-2">
                      {cluster.post_ids?.length || 0} unique posts
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Footer Note */}
      <Card className="bg-muted/50">
        <CardContent className="py-4">
          <p className="text-sm text-muted-foreground">
            <strong>Note:</strong> Topics and clusters are generated by the
            Airflow pipeline. If you don't see data here, trigger the{" "}
            <code>topic_extraction_dag</code> in the Airflow UI.
          </p>
        </CardContent>
      </Card>
    </div>
  );
}
