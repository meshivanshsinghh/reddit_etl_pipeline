"""
Daily Analytics DAG
Aggregates daily metrics and generates reports
"""

from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.providers.postgres.operators.postgres import PostgresOperator
from airflow.utils.dates import days_ago
import json

default_args = {
    'owner': 'data-engineering',
    'depends_on_past': False,
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 2,
    'retry_delay': timedelta(minutes=10),
}


def compute_daily_metrics(**kwargs):
    """Compute daily aggregated metrics"""
    import os
    import psycopg2
    
    execution_date = kwargs['execution_date']
    target_date = execution_date.date()
    
    # Direct connection using environment variables
    conn = psycopg2.connect(
        host=os.getenv('POSTGRES_HOST', 'postgres'),
        port=os.getenv('POSTGRES_PORT', '5432'),
        database=os.getenv('POSTGRES_DB', 'reddit_pipeline'),
        user=os.getenv('POSTGRES_USER', 'reddit_user'),
        password=os.getenv('POSTGRES_PASSWORD', 'reddit_pass')
    )
    cursor = conn.cursor()
    
    # Get all subreddits
    cursor.execute("SELECT DISTINCT subreddit FROM posts_raw")
    subreddits = [row[0] for row in cursor.fetchall()]
    
    metrics_inserted = 0
    
    for subreddit in subreddits:
        # Compute metrics for each subreddit
        cursor.execute("""
            WITH daily_posts AS (
                SELECT 
                    p.id,
                    p.title,
                    p.score,
                    p.num_comments,
                    p.created_utc,
                    s.avg_sentiment
                FROM posts_raw p
                LEFT JOIN sentiment_timeseries s 
                    ON DATE_TRUNC('minute', p.created_utc) = s.timestamp
                    AND p.subreddit = s.subreddit
                WHERE DATE(p.created_utc) = %s
                    AND p.subreddit = %s
            )
            SELECT 
                COUNT(*) as total_posts,
                AVG(avg_sentiment) as avg_sentiment,
                STDDEV(avg_sentiment) as sentiment_std_dev,
                AVG(num_comments) as avg_comments,
                AVG(score) as avg_score,
                EXTRACT(HOUR FROM created_utc) as peak_hour
            FROM daily_posts
            GROUP BY peak_hour
            ORDER BY COUNT(*) DESC
            LIMIT 1
        """, (target_date, subreddit))
        
        result = cursor.fetchone()
        
        if result and result[0] > 0:
            total_posts, avg_sentiment, sentiment_std, avg_comments, avg_score, peak_hour = result
            
            # Get top posts
            cursor.execute("""
                SELECT json_agg(row_to_json(t))
                FROM (
                    SELECT id, title, score, num_comments
                    FROM posts_raw
                    WHERE DATE(created_utc) = %s AND subreddit = %s
                    ORDER BY score DESC
                    LIMIT 5
                ) t
            """, (target_date, subreddit))
            
            top_posts = cursor.fetchone()[0]
            
            # Insert daily metrics
            cursor.execute("""
                INSERT INTO daily_metrics 
                (date, subreddit, total_posts, avg_sentiment, sentiment_std_dev,
                 top_posts, avg_comments_per_post, avg_score, peak_hour, quality_score)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (date, subreddit) DO UPDATE SET
                    total_posts = EXCLUDED.total_posts,
                    avg_sentiment = EXCLUDED.avg_sentiment,
                    sentiment_std_dev = EXCLUDED.sentiment_std_dev,
                    top_posts = EXCLUDED.top_posts,
                    avg_comments_per_post = EXCLUDED.avg_comments_per_post,
                    avg_score = EXCLUDED.avg_score,
                    peak_hour = EXCLUDED.peak_hour,
                    quality_score = EXCLUDED.quality_score
            """, (
                target_date, subreddit, total_posts, avg_sentiment, sentiment_std,
                json.dumps(top_posts) if top_posts else None,
                avg_comments, avg_score, int(peak_hour) if peak_hour else 0, 0.95
            ))
            
            metrics_inserted += 1
    
    conn.commit()
    cursor.close()
    conn.close()
    
    print(f"Computed daily metrics for {metrics_inserted} subreddits on {target_date}")
    return {'subreddits_processed': metrics_inserted, 'date': str(target_date)}


with DAG(
    'daily_analytics_pipeline',
    default_args=default_args,
    description='Daily aggregation and analytics',
    schedule_interval='0 1 * * *',  # Daily at 1 AM
    start_date=days_ago(1),
    catchup=False,
    tags=['reddit', 'analytics', 'daily'],
) as dag:
    
    compute_metrics = PythonOperator(
        task_id='compute_daily_metrics',
        python_callable=compute_daily_metrics,
        provide_context=True,
    )
    
    compute_metrics