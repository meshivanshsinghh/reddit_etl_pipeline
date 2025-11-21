import os
import sys
import psycopg2
from typing import List, Dict, Tuple
import numpy as np
from datetime import datetime, timedelta
from collections import Counter

# Add project root to path for imports
sys.path.insert(0, os.getenv('AIRFLOW_HOME', '/opt/airflow'))
from utils.logger import setup_logger

logger = setup_logger(__name__)


class AnomalyDetector:
    """Detect anomalies in sentiment, volume, and content"""
    
    def __init__(self):
        """Initialize database connection"""
        self.conn = psycopg2.connect(
            host=os.getenv('POSTGRES_HOST', 'localhost'),
            port=os.getenv('POSTGRES_PORT', '5432'),
            database=os.getenv('POSTGRES_DB', 'reddit_pipeline'),
            user=os.getenv('POSTGRES_USER', 'reddit_user'),
            password=os.getenv('POSTGRES_PASSWORD', 'reddit_pass')
        )
        logger.info("Connected to PostgreSQL for anomaly detection")
    
    def detect_sentiment_anomalies(self, std_dev_threshold: float = 2.0) -> List[Dict]:
        """Detect sentiment outliers using statistical deviation
        
        Args:
            std_dev_threshold: Number of standard deviations for anomaly threshold
            
        Returns:
            List of anomaly dictionaries
        """
        anomalies = []
        
        query = """
        WITH sentiment_stats AS (
            SELECT 
                subreddit,
                AVG(avg_sentiment) as mean_sentiment,
                STDDEV(avg_sentiment) as std_sentiment,
                COUNT(*) as sample_size
            FROM sentiment_timeseries
            GROUP BY subreddit
        )
        SELECT 
            s.subreddit,
            s.timestamp,
            s.avg_sentiment,
            ss.mean_sentiment,
            ss.std_sentiment,
            ABS(s.avg_sentiment - ss.mean_sentiment) / NULLIF(ss.std_sentiment, 0) as z_score,
            s.posts_count
        FROM sentiment_timeseries s
        JOIN sentiment_stats ss ON s.subreddit = ss.subreddit
        WHERE ss.std_sentiment > 0
            AND ABS(s.avg_sentiment - ss.mean_sentiment) / ss.std_sentiment > %s
        ORDER BY ABS(s.avg_sentiment - ss.mean_sentiment) / ss.std_sentiment DESC
        LIMIT 10
        """
        
        with self.conn.cursor() as cur:
            cur.execute(query, (std_dev_threshold,))
            rows = cur.fetchall()
            
            for row in rows:
                subreddit, timestamp, sentiment, mean, std, z_score, post_count = row
                
                # Determine severity based on z-score
                if abs(z_score) > 3:
                    severity = 'CRITICAL'
                elif abs(z_score) > 2.5:
                    severity = 'HIGH'
                else:
                    severity = 'MEDIUM'
                
                direction = "negative" if sentiment < mean else "positive"
                
                anomalies.append({
                    'alert_type': 'SENTIMENT_ANOMALY',
                    'severity': severity,
                    'subreddit': subreddit,
                    'message': f"r/{subreddit} sentiment ({sentiment:.3f}) is {abs(z_score):.2f} std devs from mean ({mean:.3f}), trending {direction}",
                    'metric_value': float(sentiment),
                    'threshold': float(mean),
                    'metadata': {
                        'z_score': float(z_score),
                        'std_dev': float(std),
                        'post_count': post_count,
                        'timestamp': str(timestamp)
                    }
                })
        
        logger.info(f"Found {len(anomalies)} sentiment anomalies")
        return anomalies
    
    def detect_volume_anomalies(self, multiplier_threshold: float = 2.0) -> List[Dict]:
        """Detect unusual post volume patterns
        
        Args:
            multiplier_threshold: Multiplier above/below average to flag
            
        Returns:
            List of anomaly dictionaries
        """
        anomalies = []
        
        query = """
        WITH volume_stats AS (
            SELECT 
                subreddit,
                AVG(posts_count) as avg_volume,
                STDDEV(posts_count) as std_volume,
                MAX(posts_count) as max_volume,
                MIN(posts_count) as min_volume
            FROM sentiment_timeseries
            GROUP BY subreddit
        )
        SELECT 
            s.subreddit,
            s.timestamp,
            s.posts_count,
            vs.avg_volume,
            s.posts_count / NULLIF(vs.avg_volume, 0) as volume_ratio
        FROM sentiment_timeseries s
        JOIN volume_stats vs ON s.subreddit = vs.subreddit
        WHERE vs.avg_volume > 0
            AND (
                s.posts_count > vs.avg_volume * %s
                OR s.posts_count < vs.avg_volume / %s
            )
        ORDER BY ABS(s.posts_count - vs.avg_volume) DESC
        LIMIT 5
        """
        
        with self.conn.cursor() as cur:
            cur.execute(query, (multiplier_threshold, multiplier_threshold))
            rows = cur.fetchall()
            
            for row in rows:
                subreddit, timestamp, volume, avg_volume, ratio = row
                
                if volume > avg_volume:
                    severity = 'HIGH' if ratio > 3 else 'MEDIUM'
                    direction = "spike"
                else:
                    severity = 'MEDIUM' if ratio < 0.5 else 'LOW'
                    direction = "drop"
                
                anomalies.append({
                    'alert_type': 'VOLUME_ANOMALY',
                    'severity': severity,
                    'subreddit': subreddit,
                    'message': f"r/{subreddit} volume {direction}: {volume} posts vs {avg_volume:.1f} average ({ratio:.2f}x)",
                    'metric_value': float(volume),
                    'threshold': float(avg_volume),
                    'metadata': {
                        'ratio': float(ratio),
                        'timestamp': str(timestamp)
                    }
                })
        
        logger.info(f"Found {len(anomalies)} volume anomalies")
        return anomalies
    
    def detect_keyword_anomalies(self, top_n: int = 5) -> List[Dict]:
        """Detect unusual keyword patterns from clusters
        
        Args:
            top_n: Number of top keywords to analyze
            
        Returns:
            List of anomaly dictionaries
        """
        anomalies = []
        
        # Check for clusters with negative sentiment (potential issues)
        query = """
        SELECT 
            cluster_id,
            cluster_name,
            avg_sentiment,
            post_count,
            severity,
            keywords[1:3] as top_keywords
        FROM issue_clusters
        WHERE avg_sentiment < -0.1
            OR severity IN ('HIGH', 'CRITICAL')
        ORDER BY avg_sentiment ASC
        LIMIT %s
        """
        
        with self.conn.cursor() as cur:
            cur.execute(query, (top_n,))
            rows = cur.fetchall()
            
            for row in rows:
                cluster_id, cluster_name, sentiment, post_count, severity, keywords = row
                
                # Map cluster severity to alert severity
                alert_severity = severity if severity in ['HIGH', 'CRITICAL'] else 'MEDIUM'
                
                anomalies.append({
                    'alert_type': 'KEYWORD_ANOMALY',
                    'severity': alert_severity,
                    'subreddit': None,  # Cluster spans multiple subreddits
                    'message': f"Issue cluster '{cluster_name}' has negative sentiment ({sentiment:.3f}) across {post_count} posts",
                    'metric_value': float(sentiment),
                    'threshold': 0.0,
                    'metadata': {
                        'cluster_id': cluster_id,
                        'keywords': keywords,
                        'post_count': post_count
                    }
                })
        
        logger.info(f"Found {len(anomalies)} keyword anomalies")
        return anomalies
    
    def detect_extreme_posts(self, sentiment_threshold: float = -0.5) -> List[Dict]:
        """Detect individual posts with extremely negative sentiment
        
        Args:
            sentiment_threshold: Sentiment score below which to flag
            
        Returns:
            List of anomaly dictionaries
        """
        anomalies = []
        
        query = """
        SELECT 
            p.subreddit,
            p.title,
            s.avg_sentiment,
            p.score,
            p.num_comments,
            p.id
        FROM posts_raw p
        JOIN sentiment_timeseries s 
            ON p.subreddit = s.subreddit
            AND DATE_TRUNC('minute', p.created_utc) = s.timestamp
        WHERE s.avg_sentiment < %s
        ORDER BY s.avg_sentiment ASC
        LIMIT 5
        """
        
        with self.conn.cursor() as cur:
            cur.execute(query, (sentiment_threshold,))
            rows = cur.fetchall()
            
            for row in rows:
                subreddit, title, sentiment, score, comments, post_id = row
                
                # Determine severity based on engagement
                if comments > 50 or score > 100:
                    severity = 'HIGH'  # High engagement on negative post = bigger issue
                elif sentiment < -0.7:
                    severity = 'CRITICAL'  # Extremely negative
                else:
                    severity = 'MEDIUM'
                
                anomalies.append({
                    'alert_type': 'EXTREME_POST',
                    'severity': severity,
                    'subreddit': subreddit,
                    'message': f"r/{subreddit}: Very negative post ({sentiment:.3f}) - '{title[:100]}...'",
                    'metric_value': float(sentiment),
                    'threshold': float(sentiment_threshold),
                    'metadata': {
                        'post_id': post_id,
                        'score': score,
                        'comments': comments,
                        'title': title[:200]
                    }
                })
        
        logger.info(f"Found {len(anomalies)} extreme posts")
        return anomalies
    
    def save_alerts(self, anomalies: List[Dict]):
        """Save detected anomalies to alerts table
        
        Args:
            anomalies: List of anomaly dictionaries
        """
        if not anomalies:
            logger.info("No anomalies to save")
            return
        
        with self.conn.cursor() as cur:
            for anomaly in anomalies:
                # Check if similar alert already exists (avoid duplicates)
                cur.execute("""
                    SELECT id FROM alerts
                    WHERE alert_type = %s
                        AND subreddit IS NOT DISTINCT FROM %s
                        AND resolved = FALSE
                        AND detected_at > NOW() - INTERVAL '24 hours'
                    LIMIT 1
                """, (anomaly['alert_type'], anomaly.get('subreddit')))
                
                existing = cur.fetchone()
                
                if not existing:
                    # Insert new alert
                    cur.execute("""
                        INSERT INTO alerts 
                        (alert_type, severity, subreddit, message, metric_value, threshold, metadata)
                        VALUES (%s, %s, %s, %s, %s, %s, %s)
                    """, (
                        anomaly['alert_type'],
                        anomaly['severity'],
                        anomaly.get('subreddit'),
                        anomaly['message'],
                        anomaly.get('metric_value'),
                        anomaly.get('threshold'),
                        psycopg2.extras.Json(anomaly.get('metadata', {}))
                    ))
            
            self.conn.commit()
            logger.info(f"Saved {len(anomalies)} alerts to database")
    
    def resolve_old_alerts(self, hours: int = 24):
        """Mark old unresolved alerts as resolved
        
        Args:
            hours: Age in hours after which to auto-resolve
        """
        with self.conn.cursor() as cur:
            cur.execute("""
                UPDATE alerts
                SET resolved = TRUE,
                    resolved_at = NOW()
                WHERE resolved = FALSE
                    AND detected_at < NOW() - INTERVAL '%s hours'
            """, (hours,))
            
            count = cur.rowcount
            self.conn.commit()
            logger.info(f"Auto-resolved {count} old alerts")
    
    def run(self):
        """Execute full anomaly detection pipeline"""
        try:
            logger.info("Starting anomaly detection pipeline")
            
            all_anomalies = []
            
            # Run all detection methods
            all_anomalies.extend(self.detect_sentiment_anomalies(std_dev_threshold=2.0))
            all_anomalies.extend(self.detect_volume_anomalies(multiplier_threshold=2.0))
            all_anomalies.extend(self.detect_keyword_anomalies(top_n=5))
            all_anomalies.extend(self.detect_extreme_posts(sentiment_threshold=-0.5))
            
            # Save to database
            self.save_alerts(all_anomalies)
            
            # Auto-resolve old alerts
            self.resolve_old_alerts(hours=24)
            
            logger.info(f"Anomaly detection completed. Found {len(all_anomalies)} total anomalies")
            
            return {
                'total_anomalies': len(all_anomalies),
                'by_type': Counter(a['alert_type'] for a in all_anomalies),
                'by_severity': Counter(a['severity'] for a in all_anomalies)
            }
            
        except Exception as e:
            logger.error(f"Error in anomaly detection pipeline: {e}")
            raise
        finally:
            self.conn.close()


def main():
    """Main entry point"""
    detector = AnomalyDetector()
    results = detector.run()
    print(f"\nAnomaly Detection Summary:")
    print(f"  Total Anomalies: {results['total_anomalies']}")
    print(f"  By Type: {dict(results['by_type'])}")
    print(f"  By Severity: {dict(results['by_severity'])}")


if __name__ == '__main__':
    main()