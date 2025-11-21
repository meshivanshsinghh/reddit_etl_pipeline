// Dashboard Statistics
export interface DashboardStats {
  total_posts: number;
  avg_sentiment: number;
  critical_alerts: number;
  extraction_rate: number;
}

// Alert Types
export type AlertSeverity = 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW';

export type AlertType =
  | 'SENTIMENT_ANOMALY'
  | 'VOLUME_SPIKE'
  | 'EXTREME_POST'
  | 'KEYWORD_SPIKE'
  | 'SENTIMENT_DROP';

export interface Alert {
  id: number;
  alert_type: AlertType;
  severity: AlertSeverity;
  subreddit: string;
  message: string;
  metric_value: number;
  metadata: {
    post_ids?: string[];
    permalinks?: string[];
    keywords?: string[];
    [key: string]: any;
  };
  detected_at: string;
  resolved: boolean;
}

// Product Types
export interface Product {
  primary_product: string;
  post_count: number;
  avg_sentiment: number;
}

export interface ProductDetail extends Product {
  sentiment_timeline: SentimentTimelinePoint[];
  top_posts: RedditPost[];
  common_issues: string[];
  related_subreddits: string[];
}

// Sentiment Types
export interface SentimentTimelinePoint {
  time: string;
  sentiment: number;
  posts: number;
}

export interface SentimentDistribution {
  positive_count: number;
  negative_count: number;
  neutral_count: number;
  total: number;
}

// Topic & Cluster Types
export interface Topic {
  id: number;
  subreddit: string;
  keyword: string;
  score: number;
  post_count: number;
  avg_sentiment: number;
}

export interface Cluster {
  id: number;
  cluster_id: number;
  cluster_name: string;
  post_ids: string[];
  keywords: string[];
  avg_sentiment: number;
  post_count: number;
  severity: string;
  created_at: string;
}

// Reddit Post Types
export interface RedditPost {
  id: string;
  title: string;
  subreddit: string;
  created_utc: string;
  score: number;
  num_comments: number;
  permalink: string;
  entities?: {
    vehicles?: string[];
    energy_products?: string[];
    issues?: string[];
  };
  primary_product?: string;
  sentiment?: number;
}

// Subreddit Types
export interface SubredditStats {
  subreddit: string;
  post_count: number;
  avg_sentiment: number;
  positive_percent: number;
  negative_percent: number;
  neutral_percent: number;
}

export interface SubredditDetail extends SubredditStats {
  sentiment_timeline: SentimentTimelinePoint[];
  top_posts: RedditPost[];
  entity_distribution: {
    vehicles: number;
    energy_products: number;
    issues: number;
  };
  active_alerts: Alert[];
}

// API Response Types
export interface ApiResponse<T> {
  data: T;
  error?: string;
  timestamp: string;
}

export interface ApiError {
  error: string;
  message: string;
  statusCode: number;
}

