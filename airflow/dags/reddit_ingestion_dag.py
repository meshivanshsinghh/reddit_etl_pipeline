"""
Reddit Ingestion DAG
Orchestrates data ingestion from Reddit API to Kafka
"""

from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.operators.bash import BashOperator
from airflow.utils.dates import days_ago
import os
import sys

# Add project paths to Python path
sys.path.insert(0, os.path.join(os.getenv('AIRFLOW_HOME', '/opt/airflow'), 'reddit_kafka'))

default_args = {
    'owner': 'data-engineering',
    'depends_on_past': False,
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 3,
    'retry_delay': timedelta(minutes=5),
    'execution_timeout': timedelta(minutes=30),
}


def run_reddit_producer(**kwargs):
    """Run Reddit Kafka producer for a limited time"""
    from producer import RedditJSONProducer
    
    producer = RedditJSONProducer()
    # Run for 5 minutes (300 seconds)
    producer.run(duration_seconds=300, fetch_interval=60)
    
    # Return metrics for XCom
    return {
        'posts_produced': producer.post_count,
        'errors': producer.error_count,
        'timestamp': datetime.utcnow().isoformat()
    }


def check_kafka_health(**kwargs):
    """Check if Kafka is healthy"""
    from kafka import KafkaConsumer
    from kafka.errors import KafkaError
    
    try:
        consumer = KafkaConsumer(
            bootstrap_servers=os.getenv('KAFKA_BOOTSTRAP_SERVERS', 'kafka:29092'),
            consumer_timeout_ms=5000
        )
        topics = consumer.topics()
        consumer.close()
        
        print(f"Kafka is healthy. Available topics: {topics}")
        return True
    except KafkaError as e:
        print(f"Kafka health check failed: {e}")
        raise

def consume_kafka_to_postgres(**kwargs):
    """
    Consume messages from Kafka and write to PostgreSQL
    Processes ALL existing messages in Kafka
    """
    from kafka import KafkaConsumer
    from kafka.errors import KafkaError
    import psycopg2
    import json
    from datetime import datetime
    
    # Kafka configuration
    consumer = KafkaConsumer(
        'reddit_raw_posts',
        bootstrap_servers=os.getenv('KAFKA_BOOTSTRAP_SERVERS', 'kafka:29092'),
        auto_offset_reset='earliest',  # Read from beginning
        enable_auto_commit=False,  # Manual commit for reliability
        group_id='airflow_postgres_consumer',
        value_deserializer=lambda v: json.loads(v.decode('utf-8')),
        consumer_timeout_ms=30000  # Stop after 30s of no messages
    )
    
    # PostgreSQL connection
    conn = psycopg2.connect(
        host=os.getenv('POSTGRES_HOST', 'postgres'),
        port=os.getenv('POSTGRES_PORT', '5432'),
        database=os.getenv('POSTGRES_DB', 'reddit_pipeline'),
        user=os.getenv('POSTGRES_USER', 'reddit_user'),
        password=os.getenv('POSTGRES_PASSWORD', 'reddit_pass')
    )
    cursor = conn.cursor()
    
    inserted_count = 0
    duplicate_count = 0
    error_count = 0
    
    try:
        print("📥 Starting Kafka consumer...")
        
        for message in consumer:
            try:
                post = message.value
                
                # Convert ISO timestamp to PostgreSQL timestamp
                created_utc = datetime.fromisoformat(post['created_utc'])
                ingested_at = datetime.fromisoformat(post['ingested_at'])
                
                # Insert with ON CONFLICT to handle duplicates
                insert_query = """
                    INSERT INTO posts_raw (
                        id, title, selftext, author, subreddit, created_utc,
                        score, num_comments, url, permalink, upvote_ratio,
                        is_self, link_flair_text, ingested_at
                    ) VALUES (
                        %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                    )
                    ON CONFLICT (id) DO NOTHING
                    RETURNING id;
                """
                
                cursor.execute(insert_query, (
                    post['id'],
                    post['title'],
                    post['selftext'],
                    post['author'],
                    post['subreddit'],
                    created_utc,
                    post['score'],
                    post['num_comments'],
                    post['url'],
                    post['permalink'],
                    post['upvote_ratio'],
                    post['is_self'],
                    post.get('link_flair_text'),
                    ingested_at
                ))
                
                # Check if row was inserted (not a duplicate)
                if cursor.fetchone():
                    inserted_count += 1
                else:
                    duplicate_count += 1
                
                # Commit every 100 records for performance
                if (inserted_count + duplicate_count) % 100 == 0:
                    conn.commit()
                    print(f"✅ Processed {inserted_count + duplicate_count} messages "
                          f"(Inserted: {inserted_count}, Duplicates: {duplicate_count})")
                
            except Exception as e:
                print(f"❌ Error processing message: {e}")
                error_count += 1
                conn.rollback()
                continue
        
        # Final commit
        conn.commit()
        
        # Manually commit Kafka offsets after successful DB writes
        consumer.commit()
        
        print(f"\n🎉 Consumer finished!")
        print(f"   Inserted: {inserted_count}")
        print(f"   Duplicates: {duplicate_count}")
        print(f"   Errors: {error_count}")
        
        return {
            'inserted': inserted_count,
            'duplicates': duplicate_count,
            'errors': error_count
        }
        
    finally:
        cursor.close()
        conn.close()
        consumer.close()


with DAG(
    'reddit_ingestion_pipeline',
    default_args=default_args,
    description='Ingest Reddit posts and publish to Kafka',
    # running every 10 minutes
    schedule_interval='*/10 * * * *',
    start_date=days_ago(1),
    catchup=False,
    max_active_runs=1,
    tags=['reddit', 'ingestion', 'kafka'],
) as dag:
    
    # Task 1: Check Kafka health
    kafka_health_check = PythonOperator(
        task_id='check_kafka_health',
        python_callable=check_kafka_health,
    )
    
    # Task 2: Run Reddit producer
    run_producer = PythonOperator(
        task_id='run_reddit_producer',
        python_callable=run_reddit_producer,
        provide_context=True,
    )

    # Task 3: Consume from Kafka to PostgreSQL
    consume_to_db = PythonOperator(
        task_id='consume_kafka_to_postgres',
        python_callable=consume_kafka_to_postgres,
        provide_context=True,
    )
    
    # Task 4: Log metrics
    log_metrics = BashOperator(
        task_id='log_ingestion_metrics',
        bash_command='echo "Ingestion completed at $(date)"',
    )
    
    # Define task dependencies
    kafka_health_check >> run_producer >> consume_to_db >> log_metrics