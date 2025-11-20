-- Reddit Energy Sentiment Pipeline Database Schema

-- Enable TimescaleDB extension for time-series optimization (if available)
-- CREATE EXTENSION IF NOT EXISTS timescaledb;

-- Drop existing tables (for development)
DROP TABLE IF EXISTS data_quality_metrics CASCADE;
DROP TABLE IF EXISTS daily_metrics CASCADE;
DROP TABLE IF EXISTS sentiment_timeseries CASCADE;
DROP TABLE IF EXISTS posts_raw CASCADE;

-- Raw posts table - stores all ingested Reddit data
CREATE TABLE posts_raw (
    id VARCHAR(50) PRIMARY KEY,
    title TEXT NOT NULL,
    selftext TEXT,
    author VARCHAR(100),
    subreddit VARCHAR(100) NOT NULL,
    created_utc TIMESTAMP NOT NULL,
    score INTEGER,
    num_comments INTEGER,
    url TEXT,
    permalink TEXT,
    upvote_ratio FLOAT,
    is_self BOOLEAN,
    link_flair_text VARCHAR(200),
    raw_json JSONB,  -- Store complete raw data
    ingested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    processed BOOLEAN DEFAULT FALSE
);

-- Create indexes for time-series queries
CREATE INDEX idx_posts_created_utc ON posts_raw(created_utc DESC);
CREATE INDEX idx_posts_subreddit ON posts_raw(subreddit);
CREATE INDEX idx_posts_ingested_at ON posts_raw(ingested_at DESC);
CREATE INDEX idx_posts_processed ON posts_raw(processed) WHERE processed = FALSE;

-- Sentiment time-series table - stores minute-level aggregations
CREATE TABLE sentiment_timeseries (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMP NOT NULL,
    subreddit VARCHAR(100) NOT NULL,
    posts_count INTEGER DEFAULT 0,
    avg_sentiment FLOAT,
    positive_count INTEGER DEFAULT 0,
    negative_count INTEGER DEFAULT 0,
    neutral_count INTEGER DEFAULT 0,
    avg_score FLOAT,
    total_comments INTEGER DEFAULT 0,
    top_keywords TEXT[],
    anomaly_detected BOOLEAN DEFAULT FALSE,
    anomaly_score FLOAT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for time-series queries
CREATE INDEX idx_sentiment_timestamp ON sentiment_timeseries(timestamp DESC);
CREATE INDEX idx_sentiment_subreddit ON sentiment_timeseries(subreddit);
CREATE INDEX idx_sentiment_anomaly ON sentiment_timeseries(anomaly_detected) WHERE anomaly_detected = TRUE;

-- Convert to TimescaleDB hypertable (if extension available)
-- SELECT create_hypertable('sentiment_timeseries', 'timestamp', if_not_exists => TRUE);

-- Daily metrics table - aggregated daily analytics
CREATE TABLE daily_metrics (
    id SERIAL PRIMARY KEY,
    date DATE NOT NULL,
    subreddit VARCHAR(100) NOT NULL,
    total_posts INTEGER DEFAULT 0,
    avg_sentiment FLOAT,
    sentiment_std_dev FLOAT,
    top_posts JSONB,  -- Top 5 posts by score
    trending_topics JSONB,  -- Top 10 keywords/phrases
    avg_comments_per_post FLOAT,
    avg_score FLOAT,
    engagement_rate FLOAT,
    peak_hour INTEGER,  -- Hour with most activity
    quality_score FLOAT,  -- Data quality metric
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(date, subreddit)
);

-- Create indexes for daily queries
CREATE INDEX idx_daily_date ON daily_metrics(date DESC);
CREATE INDEX idx_daily_subreddit ON daily_metrics(subreddit);

-- Data quality metrics table - monitoring table
CREATE TABLE data_quality_metrics (
    id SERIAL PRIMARY KEY,
    check_timestamp TIMESTAMP NOT NULL,
    check_name VARCHAR(100) NOT NULL,
    status VARCHAR(50) NOT NULL,  -- PASSED, FAILED, WARNING
    metric_value FLOAT,
    threshold_value FLOAT,
    details JSONB,
    error_message TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for monitoring queries
CREATE INDEX idx_quality_timestamp ON data_quality_metrics(check_timestamp DESC);
CREATE INDEX idx_quality_status ON data_quality_metrics(status);
CREATE INDEX idx_quality_check_name ON data_quality_metrics(check_name);

-- View for real-time dashboard - last 24 hours sentiment
CREATE OR REPLACE VIEW v_realtime_sentiment_24h AS
SELECT 
    timestamp,
    subreddit,
    posts_count,
    avg_sentiment,
    positive_count,
    negative_count,
    neutral_count,
    anomaly_detected
FROM sentiment_timeseries
WHERE timestamp >= NOW() - INTERVAL '24 hours'
ORDER BY timestamp DESC;

-- View for data quality dashboard
CREATE OR REPLACE VIEW v_data_quality_summary AS
SELECT 
    check_name,
    status,
    COUNT(*) as check_count,
    AVG(metric_value) as avg_metric,
    MAX(check_timestamp) as last_check
FROM data_quality_metrics
WHERE check_timestamp >= NOW() - INTERVAL '7 days'
GROUP BY check_name, status
ORDER BY check_name, status;

-- View for top posts by subreddit (last 7 days)
CREATE OR REPLACE VIEW v_top_posts_weekly AS
SELECT 
    subreddit,
    title,
    author,
    score,
    num_comments,
    created_utc,
    url
FROM posts_raw
WHERE created_utc >= NOW() - INTERVAL '7 days'
ORDER BY score DESC
LIMIT 100;

-- Function to calculate sentiment distribution
CREATE OR REPLACE FUNCTION get_sentiment_distribution(
    p_start_date TIMESTAMP,
    p_end_date TIMESTAMP,
    p_subreddit VARCHAR DEFAULT NULL
)
RETURNS TABLE (
    sentiment_category VARCHAR,
    count BIGINT,
    percentage FLOAT
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        CASE 
            WHEN avg_sentiment > 0.1 THEN 'positive'
            WHEN avg_sentiment < -0.1 THEN 'negative'
            ELSE 'neutral'
        END as sentiment_category,
        COUNT(*) as count,
        ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER (), 2) as percentage
    FROM sentiment_timeseries
    WHERE timestamp BETWEEN p_start_date AND p_end_date
        AND (p_subreddit IS NULL OR subreddit = p_subreddit)
    GROUP BY sentiment_category;
END;
$$ LANGUAGE plpgsql;

-- Function to detect data freshness issues
CREATE OR REPLACE FUNCTION check_data_freshness(
    threshold_minutes INTEGER DEFAULT 10
)
RETURNS TABLE (
    subreddit VARCHAR,
    last_post_time TIMESTAMP,
    minutes_ago INTEGER,
    is_stale BOOLEAN
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        p.subreddit,
        MAX(p.created_utc) as last_post_time,
        EXTRACT(EPOCH FROM (NOW() - MAX(p.created_utc)))/60 as minutes_ago,
        EXTRACT(EPOCH FROM (NOW() - MAX(p.created_utc)))/60 > threshold_minutes as is_stale
    FROM posts_raw p
    GROUP BY p.subreddit
    ORDER BY minutes_ago DESC;
END;
$$ LANGUAGE plpgsql;

-- Insert initial data quality check
INSERT INTO data_quality_metrics (check_timestamp, check_name, status, details)
VALUES (NOW(), 'schema_initialization', 'PASSED', '{"message": "Database schema created successfully"}');