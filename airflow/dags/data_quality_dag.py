"""
Data Quality DAG
Runs quality checks and alerts on failures
"""

from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator, BranchPythonOperator
from airflow.operators.bash import BashOperator
from airflow.utils.dates import days_ago
import sys
import os

sys.path.insert(0, os.path.join(os.getenv('AIRFLOW_HOME', '/opt/airflow'), 'monitoring'))

default_args = {
    'owner': 'data-engineering',
    'depends_on_past': False,
    'email_on_failure': True,
    'email_on_retry': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
}


def run_quality_checks(**kwargs):
    """Run all data quality checks"""
    from monitoring.quality_checks import DataQualityChecker, get_db_config_from_env
    
    checker = DataQualityChecker(get_db_config_from_env())
    results = checker.run_all_checks()
    
    # Push results to XCom
    kwargs['ti'].xcom_push(key='quality_results', value=results)
    
    return results


def check_quality_status(**kwargs):
    """Determine next action based on quality check results"""
    ti = kwargs['ti']
    results = ti.xcom_pull(key='quality_results', task_ids='run_quality_checks')
    
    if results.get('overall_passed', False):
        return 'quality_passed'
    else:
        return 'quality_failed'


def send_alert(**kwargs):
    """Send alert on quality failure"""
    ti = kwargs['ti']
    results = ti.xcom_pull(key='quality_results', task_ids='run_quality_checks')
    
    print("=" * 50)
    print("DATA QUALITY ALERT")
    print("=" * 50)
    
    for check_name, (passed, details) in results.items():
        if check_name == 'overall_passed':
            continue
        status = "✓ PASSED" if passed else "✗ FAILED"
        print(f"{check_name}: {status}")
        print(f"  Details: {details}")
    
    print("=" * 50)
    
    # In production, send to Slack/Email/PagerDuty
    # slack_webhook = os.getenv('SLACK_WEBHOOK_URL')
    # if slack_webhook:
    #     send_slack_message(slack_webhook, results)


with DAG(
    'data_quality_pipeline',
    default_args=default_args,
    description='Data quality monitoring and alerts',
    schedule_interval='0 */6 * * *',  # Every 6 hours
    start_date=days_ago(1),
    catchup=False,
    tags=['reddit', 'quality', 'monitoring'],
) as dag:
    
    # Run quality checks
    run_checks = PythonOperator(
        task_id='run_quality_checks',
        python_callable=run_quality_checks,
        provide_context=True,
    )
    
    # Branch based on results
    check_status = BranchPythonOperator(
        task_id='check_quality_status',
        python_callable=check_quality_status,
        provide_context=True,
    )
    
    # Quality passed path
    quality_passed = BashOperator(
        task_id='quality_passed',
        bash_command='echo "All quality checks passed ✓"',
    )
    
    # Quality failed path
    quality_failed = PythonOperator(
        task_id='quality_failed',
        python_callable=send_alert,
        provide_context=True,
    )
    
    # Dependencies
    run_checks >> check_status >> [quality_passed, quality_failed]