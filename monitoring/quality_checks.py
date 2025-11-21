"""
Data Quality Checks for Reddit Pipeline
Implements various quality checks for monitoring data health
"""

import json
import psycopg2
from datetime import datetime, timedelta
from typing import Dict, List, Tuple
import logging
from utils.logger import setup_logger

logger = setup_logger(__name__)


class DataQualityChecker:
    """
    Performs data quality checks on the pipeline
    """
    
    def __init__(self, db_config: Dict):
    """
        Initialize quality checker
        
        Args:
            db_config: Database connection configuration
        """
        self.db_config = db_config
        self.conn = None
        
    def connect(self):
        """Establish database connection"""
        try:
            self.conn = psycopg2.connect(**self.db_config)
            logger.info("Connected to database for quality checks")
        except Exception as e:
            logger.error(f"Failed to connect to database: {e}")
            raise
    
    def disconnect(self):
        """Close database connection"""
        if self.conn:
            self.conn.close()
            logger.info("Disconnected from database")
    
    def log_quality_metric(self, check_name: str, status: str, 
                          metric_value: float = None, threshold: float = None,
                          details: Dict = None, error_message: str = None):
        """
        Log quality check result to database
        
        Args:
            check_name: Name of the check
            status: PASSED, FAILED, WARNING
            metric_value: Numeric metric value
            threshold: Threshold value used
            details: Additional details as JSON
            error_message: Error message if failed
        """
        try:
            cursor = self.conn.cursor()
            cursor.execute("""
                INSERT INTO data_quality_metrics 
                (check_timestamp, check_name, status, metric_value, threshold_value, 
                 details, error_message)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, (
                datetime.utcnow(), check_name, status, metric_value,
                threshold, json.dumps(details) if details else None, error_message
            ))
            self.conn.commit()
            cursor.close()
            logger.info(f"Quality check logged: {check_name} - {status}")
        except Exception as e:
            logger.error(f"Failed to log quality metric: {e}")
            self.conn.rollback()
    
    def check_data_freshness(self, threshold_minutes: int = 10) -> Tuple[bool, Dict]:
        """
        Check if data is fresh (recent posts exist)
        
        Args:
            threshold_minutes: Maximum age of most recent post
            
        Returns:
            Tuple of (passed, details_dict)
        """
        try:
            cursor = self.conn.cursor()
            cursor.execute("""
                SELECT 
                    subreddit,
                    MAX(created_utc) as last_post_time,
                    EXTRACT(EPOCH FROM (NOW() - MAX(created_utc)))/60 as minutes_ago
                FROM posts_raw
                GROUP BY subreddit
            """)
            results = cursor.fetchall()
            cursor.close()
            
            stale_subreddits = []
            for subreddit, last_post, minutes_ago in results:
                if minutes_ago > threshold_minutes:
                    stale_subreddits.append({
                        'subreddit': subreddit,
                        'minutes_ago': round(minutes_ago, 2)
                    })
            
            passed = len(stale_subreddits) == 0
            status = "PASSED" if passed else "FAILED"
            
            details = {
                'stale_subreddits': stale_subreddits,
                'threshold_minutes': threshold_minutes,
                'total_subreddits_checked': len(results)
            }
            
            self.log_quality_metric(
                'data_freshness',
                status,
                metric_value=len(stale_subreddits),
                threshold=threshold_minutes,
                details=details
            )
            
            return passed, details
            
        except Exception as e:
            logger.error(f"Data freshness check failed: {e}")
            self.log_quality_metric('data_freshness', 'FAILED', 
                                   error_message=str(e))
            return False, {'error': str(e)}
    
    def check_duplicate_detection(self) -> Tuple[bool, Dict]:
        """
        Check for duplicate posts
        
        Returns:
            Tuple of (passed, details_dict)
        """
        try:
            cursor = self.conn.cursor()
            cursor.execute("""
                SELECT id, COUNT(*) as count
                FROM posts_raw
                GROUP BY id
                HAVING COUNT(*) > 1
            """)
            duplicates = cursor.fetchall()
            cursor.close()
            
            passed = len(duplicates) == 0
            status = "PASSED" if passed else "WARNING"
            
            details = {
                'duplicate_count': len(duplicates),
                'duplicate_ids': [d[0] for d in duplicates[:10]]  # First 10
            }
            
            self.log_quality_metric(
                'duplicate_detection',
                status,
                metric_value=len(duplicates),
                threshold=0,
                details=details
            )
            
            return passed, details
            
        except Exception as e:
            logger.error(f"Duplicate detection failed: {e}")
            self.log_quality_metric('duplicate_detection', 'FAILED',
                                   error_message=str(e))
            return False, {'error': str(e)}
    
    def check_schema_compliance(self) -> Tuple[bool, Dict]:
        """
        Check schema compliance (null required fields)
        
        Returns:
            Tuple of (passed, details_dict)
        """
        try:
            cursor = self.conn.cursor()
            
            # Check for null values in required fields
            required_fields = ['id', 'title', 'author', 'subreddit', 'created_utc']
            null_counts = {}
            
            for field in required_fields:
                if field == 'created_utc':
                    cursor.execute(f"""
                        SELECT COUNT(*) 
                        FROM posts_raw 
                        WHERE {field} IS NULL
                    """)
                else:
                    cursor.execute(f"""
                        SELECT COUNT(*) 
                        FROM posts_raw 
                        WHERE {field} IS NULL OR {field} = ''
                    """)
                count = cursor.fetchone()[0]
                null_counts[field] = count
            
            cursor.close()
            
            total_nulls = sum(null_counts.values())
            passed = total_nulls == 0
            status = "PASSED" if passed else "FAILED"
            
            details = {
                'null_counts': null_counts,
                'total_null_violations': total_nulls
            }
            
            self.log_quality_metric(
                'schema_validation',
                status,
                metric_value=total_nulls,
                threshold=0,
                details=details
            )
            
            return passed, details
            
        except Exception as e:
            logger.error(f"Schema compliance check failed: {e}")
            self.log_quality_metric('schema_validation', 'FAILED',
                                   error_message=str(e))
            return False, {'error': str(e)}
    
    def check_data_completeness(self, hours: int = 24) -> Tuple[bool, Dict]:
        """
        Check completeness of data over time period
        
        Args:
            hours: Number of hours to check
            
        Returns:
            Tuple of (passed, details_dict)
        """
        try:
            cursor = self.conn.cursor()
            cursor.execute("""
                SELECT 
                    COUNT(*) as total_posts,
                    COUNT(DISTINCT subreddit) as unique_subreddits
                FROM posts_raw
                WHERE created_utc >= NOW() - INTERVAL '%s hours'
            """, (hours,))
            
            result = cursor.fetchone()
            total_posts, unique_subreddits = result
            cursor.close()
            
            # Expect at least some posts from most subreddits
            expected_subreddits = 6  # From config
            completeness_ratio = unique_subreddits / expected_subreddits
            
            passed = completeness_ratio >= 0.8  # 80% coverage
            status = "PASSED" if passed else "WARNING"
            
            details = {
                'total_posts': total_posts,
                'unique_subreddits': unique_subreddits,
                'expected_subreddits': expected_subreddits,
                'completeness_ratio': round(completeness_ratio, 2),
                'time_window_hours': hours
            }
            
            self.log_quality_metric(
                'completeness',
                status,
                metric_value=completeness_ratio,
                threshold=0.8,
                details=details
            )
            
            return passed, details
            
        except Exception as e:
            logger.error(f"Data completeness check failed: {e}")
            self.log_quality_metric('completeness', 'FAILED',
                                   error_message=str(e))
            return False, {'error': str(e)}
    
    def run_all_checks(self) -> Dict:
        """
        Run all quality checks
        
        Returns:
            Dictionary with all check results
        """
        logger.info("Running all data quality checks...")
        
        results = {}
        
        try:
            self.connect()
            
            # Run each check
            results['freshness'] = self.check_data_freshness()
            results['duplicates'] = self.check_duplicate_detection()
            results['schema'] = self.check_schema_compliance()
            results['completeness'] = self.check_data_completeness()
            
            # Overall status
            all_passed = all(check[0] for check in results.values())
            results['overall_passed'] = all_passed
            
            logger.info(f"Quality checks completed. Overall: {'PASSED' if all_passed else 'FAILED'}")
            
        except Exception as e:
            logger.error(f"Error running quality checks: {e}")
            results['error'] = str(e)
        finally:
            self.disconnect()
        
        return results


def get_db_config_from_env():
    """Get database configuration from environment"""
    import os
    return {
        'host': os.getenv('POSTGRES_HOST', 'localhost'),
        'port': int(os.getenv('POSTGRES_PORT', 5432)),
        'database': os.getenv('POSTGRES_DB', 'reddit_pipeline'),
        'user': os.getenv('POSTGRES_USER', 'reddit_user'),
        'password': os.getenv('POSTGRES_PASSWORD', 'reddit_pass')
    }


if __name__ == '__main__':
    # Test quality checks
    from dotenv import load_dotenv
    load_dotenv()
    
    checker = DataQualityChecker(get_db_config_from_env())
    results = checker.run_all_checks()
    print("\nQuality Check Results:")
    print(f"Overall Status: {'✓ PASSED' if results.get('overall_passed') else '✗ FAILED'}")