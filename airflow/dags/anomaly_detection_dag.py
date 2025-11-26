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
    'execution_timeout': timedelta(minutes=10),
}


def check_data_exists(**kwargs):
    """Verify sentiment data exists for anomaly detection"""
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
            # Check sentiment data
            cur.execute("SELECT COUNT(*) FROM sentiment_timeseries")
            sentiment_count = cur.fetchone()[0]
            
            # Check issue clusters
            cur.execute("SELECT COUNT(*) FROM issue_clusters")
            cluster_count = cur.fetchone()[0]
            
            print(f"✓ Found {sentiment_count} sentiment records")
            print(f"✓ Found {cluster_count} issue clusters")
            
            if sentiment_count == 0:
                raise Exception("No sentiment data found! Run sentiment analysis first.")
            
            return {'sentiment_count': sentiment_count, 'cluster_count': cluster_count}
    finally:
        conn.close()


def run_anomaly_detection(**kwargs):
    """Execute anomaly detection"""
    from analytics.anomaly_detector import AnomalyDetector
    
    print("=" * 60)
    print("STARTING ANOMALY DETECTION")
    print("=" * 60)
    
    try:
        detector = AnomalyDetector()
        results = detector.run()
        
        print("=" * 60)
        print("ANOMALY DETECTION COMPLETED")
        print("=" * 60)
        print(f"Total Anomalies Found: {results['total_anomalies']}")
        print(f"By Type: {dict(results['by_type'])}")
        print(f"By Severity: {dict(results['by_severity'])}")
        print("=" * 60)
        
        # Push results to XCom
        kwargs['ti'].xcom_push(key='detection_results', value=results)
        return results
        
    except Exception as e:
        print("=" * 60)
        print(f"ERROR IN ANOMALY DETECTION: {e}")
        print("=" * 60)
        raise


def log_alert_summary(**kwargs):
    """Query and display detected alerts"""
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
            # Count alerts by severity
            cur.execute("""
                SELECT 
                    severity,
                    COUNT(*) as count,
                    COUNT(*) FILTER (WHERE resolved = FALSE) as active
                FROM alerts
                WHERE detected_at > NOW() - INTERVAL '24 hours'
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
            
            # Count alerts by type
            cur.execute("""
                SELECT 
                    alert_type,
                    COUNT(*) as count
                FROM alerts
                WHERE detected_at > NOW() - INTERVAL '24 hours'
                GROUP BY alert_type
                ORDER BY count DESC
            """)
            type_stats = cur.fetchall()
            
            # Get most recent critical/high alerts
            cur.execute("""
                SELECT 
                    alert_type,
                    severity,
                    subreddit,
                    message,
                    detected_at
                FROM alerts
                WHERE severity IN ('CRITICAL', 'HIGH')
                    AND resolved = FALSE
                ORDER BY detected_at DESC
                LIMIT 5
            """)
            critical_alerts = cur.fetchall()
        
        print("\n" + "=" * 60)
        print("ALERT SUMMARY (Last 24 Hours)")
        print("=" * 60)
        
        print("\n📊 Alerts by Severity:")
        if severity_stats:
            for severity, count, active in severity_stats:
                print(f"  • {severity}: {count} total ({active} active)")
        else:
            print("  No alerts in last 24 hours")
        
        print("\n📈 Alerts by Type:")
        if type_stats:
            for alert_type, count in type_stats:
                print(f"  • {alert_type}: {count}")
        else:
            print("  No alerts in last 24 hours")
        
        print("\n🚨 Critical/High Severity Alerts (Unresolved):")
        if critical_alerts:
            for i, (alert_type, severity, subreddit, message, detected_at) in enumerate(critical_alerts, 1):
                sub_str = f"r/{subreddit}" if subreddit else "Global"
                print(f"  {i}. [{severity}] {sub_str}: {message[:80]}...")
        else:
            print("  ✅ No critical or high severity alerts!")
        
        print("=" * 60 + "\n")
        
        # Push stats to XCom
        kwargs['ti'].xcom_push(key='alert_count', value=sum(s[1] for s in severity_stats) if severity_stats else 0)
        
    finally:
        conn.close()


def check_critical_alerts(**kwargs):
    """Check if there are any critical alerts that need attention"""
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
            cur.execute("""
                SELECT COUNT(*)
                FROM alerts
                WHERE severity = 'CRITICAL'
                    AND resolved = FALSE
                    AND detected_at > NOW() - INTERVAL '24 hours'
            """)
            critical_count = cur.fetchone()[0]
            
            if critical_count > 0:
                print(f"\n⚠️  WARNING: {critical_count} CRITICAL alerts require attention!")
                # In production, send to Slack/PagerDuty
                return 'has_critical_alerts'
            else:
                print("\n✅ No critical alerts detected")
                return 'no_critical_alerts'
    finally:
        conn.close()


def send_critical_alert(**kwargs):
    """Send notification for critical alerts (placeholder)"""
    ti = kwargs['ti']
    
    print("\n" + "=" * 60)
    print("🚨 CRITICAL ALERT NOTIFICATION")
    print("=" * 60)
    print("In production, this would send alerts to:")
    print("  • Slack webhook")
    print("  • PagerDuty incident")
    print("  • Email to on-call team")
    print("=" * 60 + "\n")
    
    # In production:
    # slack_webhook = os.getenv('SLACK_WEBHOOK_URL')
    # if slack_webhook:
    #     send_slack_alert(slack_webhook, critical_alerts)

def send_email_notifications(**kwargs):
    """Send email alerts for critical/high severity anomalies"""
    import psycopg2
    import psycopg2.extras
    from monitoring.email_alerter import EmailAlerter
    
    conn = psycopg2.connect(
        host=os.getenv('POSTGRES_HOST', 'postgres'),
        port=os.getenv('POSTGRES_PORT', '5432'),
        database=os.getenv('POSTGRES_DB', 'reddit_pipeline'),
        user=os.getenv('POSTGRES_USER', 'reddit_user'),
        password=os.getenv('POSTGRES_PASSWORD', 'reddit_pass')
    )
    
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            # Get recent critical/high alerts that haven't been resolved
            cur.execute("""
                SELECT 
                    alert_type,
                    severity,
                    subreddit,
                    message,
                    metric_value,
                    threshold,
                    metadata,
                    detected_at
                FROM alerts
                WHERE detected_at > NOW() - INTERVAL '1 hour'
                    AND severity IN ('CRITICAL', 'HIGH')
                    AND resolved = FALSE
                ORDER BY 
                    CASE severity
                        WHEN 'CRITICAL' THEN 1
                        WHEN 'HIGH' THEN 2
                    END,
                    detected_at DESC
            """)
            alerts = cur.fetchall()
        
        if not alerts:
            print("📧 No critical/high alerts to send via email")
            return
        
        # Convert to list of dicts
        alert_list = [dict(alert) for alert in alerts]
        
        print(f"📧 Sending email for {len(alert_list)} critical/high alerts...")
        
        # Send email
        alerter = EmailAlerter()
        alerter.send_alert(alert_list)
        
    except Exception as e:
        print(f"❌ Error sending email notifications: {e}")
        # Don't fail the pipeline if email fails
        
    finally:
        conn.close()

with DAG(
    'anomaly_detection_pipeline',
    default_args=default_args,
    description='Detect sentiment, volume, and content anomalies',
    start_date=days_ago(1),
    catchup=False,
    schedule_interval = '0 * * * *',
    max_active_runs=1,
    tags=['reddit', 'analytics', 'ml', 'anomaly-detection', 'monitoring'],
) as dag:
    
    # Task 1: Check prerequisites
    check_data = PythonOperator(
        task_id='check_data_exists',
        python_callable=check_data_exists,
        provide_context=True,
    )
    
    # Task 2: Run anomaly detection
    detect_anomalies = PythonOperator(
        task_id='run_anomaly_detection',
        python_callable=run_anomaly_detection,
        provide_context=True,
    )
    
    # Task 3: Log alert summary
    log_alerts = PythonOperator(
        task_id='log_alert_summary',
        python_callable=log_alert_summary,
        provide_context=True,
    )
    
    # Task 4: Check for critical alerts
    check_critical = PythonOperator(
        task_id='check_critical_alerts',
        python_callable=check_critical_alerts,
        provide_context=True,
    )
    
    # Task 5: Send email notifications (NEW!)
    email_alerts = PythonOperator(
        task_id='send_email_notifications',
        python_callable=send_email_notifications,
        provide_context=True,
        trigger_rule='none_failed',
    )
    
    # Task 6: Send critical alert (legacy notification)
    send_alert = PythonOperator(
        task_id='send_critical_alert',
        python_callable=send_critical_alert,
        provide_context=True,
        trigger_rule='none_failed',
    )
    
    # Task 7: Success notification
    success_notification = BashOperator(
        task_id='pipeline_complete',
        bash_command='echo "✅ Anomaly detection pipeline completed successfully!"',
    )
    
    # Dependencies
    check_data >> detect_anomalies >> log_alerts >> check_critical >> [email_alerts, send_alert] >> success_notification