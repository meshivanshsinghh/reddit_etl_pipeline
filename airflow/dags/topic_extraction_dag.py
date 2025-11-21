from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.operators.bash import BashOperator
from airflow.utils.dates import days_ago
import sys
import os

sys.path.insert(0, os.getenv('AIRFLOW_HOME', '/opt/airflow'))

default_args = {
    'owner': 'data-engineering',
    'depends_on_past': False,
    'email_on_failure': True,
    'email_on_retry': False,
    'retries': 2,
    'retry_delay': timedelta(minutes=5),
    'execution_timeout': timedelta(minutes=15),
}


def check_data_exists(**kwargs):
    """Check if posts exist in database"""
    import psycopg2
    
    conn = psycopg2.connect(
        host=os.getenv('POSTGRES_HOST', 'postgres'),
        port=os.getenv('POSTGRES_PORT', '5432'),
        database=os.getenv('POSTGRES_DB', 'reddit_pipeline'),
        user=os.getenv('POSTGRES_USER', 'reddit_user'),
        password=os.getenv('POSTGRES_PASSWORD', 'reddit_pass')
    )
    
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM posts_raw")
            count = cur.fetchone()[0]
            
            print(f"✓ Found {count} posts in database")
            
            if count == 0:
                raise Exception("No posts found in database! Run reddit_ingestion_pipeline first.")
            
            return count
    finally:
        conn.close()


def extract_topics(**kwargs):
    """Run topic extraction and clustering"""
    from analytics.topic_extractor import TopicExtractor
    
    print("=" * 60)
    print("STARTING TOPIC EXTRACTION")
    print("=" * 60)
    
    try:
        extractor = TopicExtractor()
        extractor.run()
        
        print("=" * 60)
        print("TOPIC EXTRACTION COMPLETED SUCCESSFULLY")
        print("=" * 60)
        
        # Push success flag to XCom
        kwargs['ti'].xcom_push(key='extraction_status', value='SUCCESS')
        return True
        
    except Exception as e:
        print("=" * 60)
        print(f"ERROR IN TOPIC EXTRACTION: {e}")
        print("=" * 60)
        kwargs['ti'].xcom_push(key='extraction_status', value='FAILED')
        raise


def log_extraction_results(**kwargs):
    """Query and log extraction results"""
    import psycopg2
    
    conn = psycopg2.connect(
        host=os.getenv('POSTGRES_HOST', 'postgres'),
        port=os.getenv('POSTGRES_PORT', '5432'),
        database=os.getenv('POSTGRES_DB', 'reddit_pipeline'),
        user=os.getenv('POSTGRES_USER', 'reddit_user'),
        password=os.getenv('POSTGRES_PASSWORD', 'reddit_pass')
    )
    
    try:
        with conn.cursor() as cur:
            # Count keywords per subreddit
            cur.execute("""
                SELECT subreddit, COUNT(*) as keyword_count
                FROM topics
                GROUP BY subreddit
                ORDER BY keyword_count DESC
            """)
            subreddit_counts = cur.fetchall()
            
            # Count clusters by severity
            cur.execute("""
                SELECT severity, COUNT(*) as cluster_count, 
                       AVG(post_count) as avg_posts,
                       AVG(avg_sentiment) as avg_sentiment
                FROM issue_clusters
                GROUP BY severity
                ORDER BY 
                    CASE severity
                        WHEN 'CRITICAL' THEN 1
                        WHEN 'HIGH' THEN 2
                        WHEN 'MEDIUM' THEN 3
                        WHEN 'LOW' THEN 4
                    END
            """)
            severity_stats = cur.fetchall()
            
            # Get top 5 keywords overall
            cur.execute("""
                SELECT keyword, subreddit, score
                FROM topics
                ORDER BY score DESC
                LIMIT 5
            """)
            top_keywords = cur.fetchall()
        
        print("\n" + "=" * 60)
        print("TOPIC EXTRACTION RESULTS")
        print("=" * 60)
        
        print("\n📊 Keywords Extracted by Subreddit:")
        for subreddit, count in subreddit_counts:
            print(f"  • r/{subreddit}: {count} keywords")
        
        print("\n🔍 Issue Clusters by Severity:")
        for severity, count, avg_posts, avg_sentiment in severity_stats:
            print(f"  • {severity}: {count} clusters (avg {avg_posts:.1f} posts, sentiment {avg_sentiment:.3f})")
        
        print("\n🔥 Top 5 Keywords Overall:")
        for i, (keyword, subreddit, score) in enumerate(top_keywords, 1):
            print(f"  {i}. '{keyword}' (r/{subreddit}, score: {score:.4f})")
        
        print("=" * 60 + "\n")
        
        # Push stats to XCom
        kwargs['ti'].xcom_push(key='subreddit_counts', value=len(subreddit_counts))
        kwargs['ti'].xcom_push(key='cluster_count', value=sum(s[1] for s in severity_stats))
        
    except Exception as e:
        print(f"Error logging results: {e}")
    finally:
        conn.close()


def verify_data_quality(**kwargs):
    """Verify extraction quality"""
    import psycopg2
    
    conn = psycopg2.connect(
        host=os.getenv('POSTGRES_HOST', 'postgres'),
        port=os.getenv('POSTGRES_PORT', '5432'),
        database=os.getenv('POSTGRES_DB', 'reddit_pipeline'),
        user=os.getenv('POSTGRES_USER', 'reddit_user'),
        password=os.getenv('POSTGRES_PASSWORD', 'reddit_pass')
    )
    
    issues = []
    
    try:
        with conn.cursor() as cur:
            # Check 1: At least some keywords extracted
            cur.execute("SELECT COUNT(*) FROM topics")
            keyword_count = cur.fetchone()[0]
            if keyword_count == 0:
                issues.append("No keywords extracted")
            
            # Check 2: At least some clusters created
            cur.execute("SELECT COUNT(*) FROM issue_clusters")
            cluster_count = cur.fetchone()[0]
            if cluster_count == 0:
                issues.append("No clusters created")
            
            # Check 3: Clusters have reasonable post counts
            cur.execute("SELECT MIN(post_count), MAX(post_count) FROM issue_clusters")
            result = cur.fetchone()
            if result[0]:
                min_posts, max_posts = result
                if min_posts < 1:
                    issues.append(f"Cluster with too few posts: {min_posts}")
            
            # Check 4: Severity distribution is reasonable
            cur.execute("""
                SELECT severity, COUNT(*) 
                FROM issue_clusters 
                GROUP BY severity
            """)
            severity_dist = cur.fetchall()
            
        print("\n" + "=" * 60)
        print("DATA QUALITY VERIFICATION")
        print("=" * 60)
        
        if issues:
            print("\n⚠️  WARNINGS FOUND:")
            for issue in issues:
                print(f"  • {issue}")
        else:
            print("\n✅ All quality checks passed!")
            print(f"  • {keyword_count} keywords extracted")
            print(f"  • {cluster_count} clusters created")
            if result[0]:
                print(f"  • Post count range: {min_posts} - {max_posts}")
            print(f"  • Severity distribution:")
            for severity, count in severity_dist:
                print(f"    - {severity}: {count}")
        
        print("=" * 60 + "\n")
        
        kwargs['ti'].xcom_push(key='quality_issues', value=issues)
        
    finally:
        conn.close()


with DAG(
    'topic_extraction_pipeline',
    default_args=default_args,
    description='Extract topics and cluster issues from Reddit posts',
    start_date=days_ago(1),
    catchup=False,
    schedule_interval=None,  # Manual trigger (can change to '@daily' for automated)
    max_active_runs=1,
    tags=['reddit', 'analytics', 'ml', 'topic-extraction'],
) as dag:
    
    # Task 1: Check prerequisites
    check_data = PythonOperator(
        task_id='check_data_exists',
        python_callable=check_data_exists,
        provide_context=True,
    )
    
    # Task 2: Run topic extraction
    extract = PythonOperator(
        task_id='extract_topics_and_clusters',
        python_callable=extract_topics,
        provide_context=True,
    )
    
    # Task 3: Log results
    log_results = PythonOperator(
        task_id='log_extraction_results',
        python_callable=log_extraction_results,
        provide_context=True,
    )
    
    # Task 4: Verify quality
    verify_quality = PythonOperator(
        task_id='verify_data_quality',
        python_callable=verify_data_quality,
        provide_context=True,
    )
    
    # Task 5: Success notification
    success_notification = BashOperator(
        task_id='pipeline_complete',
        bash_command='echo "🎉 Topic extraction pipeline completed successfully!"',
    )
    
    # Dependencies
    check_data >> extract >> log_results >> verify_quality >> success_notification