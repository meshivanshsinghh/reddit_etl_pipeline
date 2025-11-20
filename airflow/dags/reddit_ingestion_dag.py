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
sys.path.insert(0, os.path.join(os.getenv('AIRFLOW_HOME', '/opt/airflow'), 'kafka'))

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
    from kafka.producer import RedditKafkaProducer
    
    producer = RedditKafkaProducer()
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


with DAG(
    'reddit_ingestion_pipeline',
    default_args=default_args,
    description='Ingest Reddit posts and publish to Kafka',
    schedule_interval='*/5 * * * *',  # Every 5 minutes
    start_date=days_ago(1),
    catchup=False,
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
    
    # Task 3: Log metrics
    log_metrics = BashOperator(
        task_id='log_ingestion_metrics',
        bash_command='echo "Ingestion completed at $(date)"',
    )
    
    # Define task dependencies
    kafka_health_check >> run_producer >> log_metrics