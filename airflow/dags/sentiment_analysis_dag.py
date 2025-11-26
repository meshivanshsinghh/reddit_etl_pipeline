from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.utils.dates import days_ago
import sys
import os

sys.path.insert(0, os.getenv('AIRFLOW_HOME', '/opt/airflow'))

default_args = {
    'owner': 'data-engineering',
    'depends_on_past': False,
    'email_on_failure': False,
    'retries': 2,
    'retry_delay': timedelta(minutes=2),
    'execution_timeout': timedelta(minutes=10),
}


def analyze_sentiment(**kwargs):
    """Run sentiment analysis on posts without sentiment"""
    from utils.sentiment_analyzer import add_sentiment_to_posts
    
    print("=" * 60)
    print("STARTING SENTIMENT ANALYSIS")
    print("=" * 60)
    
    results = add_sentiment_to_posts()
    
    print("=" * 60)
    print(f"SENTIMENT ANALYSIS COMPLETE")
    print(f"Processed: {results['total']} posts")
    print(f"Positive: {results['positive']} ({results['positive']/max(results['total'],1)*100:.1f}%)")
    print(f"Negative: {results['negative']} ({results['negative']/max(results['total'],1)*100:.1f}%)")
    print(f"Neutral: {results['neutral']} ({results['neutral']/max(results['total'],1)*100:.1f}%)")
    print("=" * 60)
    
    return results


with DAG(
    'sentiment_analysis_pipeline',
    default_args=default_args,
    description='Analyze sentiment of Reddit posts',
    schedule_interval = '*/15 * * * *',
    start_date=days_ago(1),
    catchup=False,
    max_active_runs=1,
    tags=['reddit', 'sentiment', 'analysis'],
) as dag:
    
    analyze_sentiment_task = PythonOperator(
        task_id='analyze_sentiment',
        python_callable=analyze_sentiment,
        provide_context=True,
    )