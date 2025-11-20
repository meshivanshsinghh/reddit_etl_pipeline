"""
Reddit Data Producer - Ingests posts from Reddit API and publishes to Kafka
Implements rate limiting, retry logic, and schema validation
"""

import os
import time
import json
import logging
from datetime import datetime
from typing import Dict, List, Optional
from retry import retry
from kafka import KafkaProducer
from kafka.errors import KafkaError
import praw
from prawcore.exceptions import PrawcoreException
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class RedditKafkaProducer:
    """
    Produces Reddit posts to Kafka topics with fault tolerance and monitoring
    """
    
    def __init__(self):
        """Initialize Reddit API client and Kafka producer"""
        self.reddit = self._initialize_reddit_client()
        self.producer = self._initialize_kafka_producer()
        self.subreddits = self._load_subreddits()
        self.post_count = 0
        self.error_count = 0
        
    def _initialize_reddit_client(self) -> praw.Reddit:
        """Initialize PRAW Reddit client with credentials"""
        try:
            reddit = praw.Reddit(
                client_id=os.getenv('REDDIT_CLIENT_ID'),
                client_secret=os.getenv('REDDIT_CLIENT_SECRET'),
                user_agent=os.getenv('REDDIT_USER_AGENT', 'RedditEnergyPipeline/1.0')
            )
            logger.info("Reddit client initialized successfully")
            return reddit
        except Exception as e:
            logger.error(f"Failed to initialize Reddit client: {e}")
            raise
            
    def _initialize_kafka_producer(self) -> KafkaProducer:
        """Initialize Kafka producer with configuration"""
        try:
            producer = KafkaProducer(
                bootstrap_servers=os.getenv('KAFKA_BOOTSTRAP_SERVERS', 'localhost:9092'),
                value_serializer=lambda v: json.dumps(v).encode('utf-8'),
                compression_type='gzip',
                acks='all',  # Wait for all replicas
                retries=3,
                max_in_flight_requests_per_connection=1  # Ensure ordering
            )
            logger.info("Kafka producer initialized successfully")
            return producer
        except Exception as e:
            logger.error(f"Failed to initialize Kafka producer: {e}")
            raise
    
    def _load_subreddits(self) -> List[str]:
        """Load target subreddits from config"""
        return [
            'teslamotors',
            'solar',
            'TeslaEnergy',
            'Powerwall',
            'electricvehicles',
            'renewable'
        ]
    
    def validate_post_schema(self, post_data: Dict) -> bool:
        """
        Validate that post contains required fields
        
        Args:
            post_data: Dictionary containing post data
            
        Returns:
            bool: True if valid, False otherwise
        """
        required_fields = ['id', 'title', 'author', 'created_utc', 'subreddit']
        
        for field in required_fields:
            if field not in post_data or post_data[field] is None:
                logger.warning(f"Post missing required field: {field}")
                return False
        return True
    
    def extract_post_data(self, submission) -> Dict:
        """
        Extract relevant data from Reddit submission
        
        Args:
            submission: PRAW submission object
            
        Returns:
            Dict containing extracted post data
        """
        try:
            return {
                'id': submission.id,
                'title': submission.title,
                'selftext': submission.selftext,
                'author': str(submission.author) if submission.author else '[deleted]',
                'subreddit': str(submission.subreddit),
                'created_utc': datetime.fromtimestamp(submission.created_utc).isoformat(),
                'score': submission.score,
                'num_comments': submission.num_comments,
                'url': submission.url,
                'permalink': submission.permalink,
                'upvote_ratio': submission.upvote_ratio,
                'is_self': submission.is_self,
                'link_flair_text': submission.link_flair_text,
                'ingested_at': datetime.utcnow().isoformat()
            }
        except Exception as e:
            logger.error(f"Error extracting post data: {e}")
            return None
    
    @retry(exceptions=PrawcoreException, tries=3, delay=2, backoff=2)
    def fetch_posts_from_subreddit(self, subreddit_name: str, limit: int = 100) -> List[Dict]:
        """
        Fetch recent posts from a subreddit with retry logic
        
        Args:
            subreddit_name: Name of the subreddit
            limit: Maximum number of posts to fetch
            
        Returns:
            List of post dictionaries
        """
        posts = []
        try:
            subreddit = self.reddit.subreddit(subreddit_name)
            logger.info(f"Fetching posts from r/{subreddit_name}")
            
            # Fetch from multiple feeds for comprehensive coverage
            for submission in subreddit.new(limit=limit//2):
                post_data = self.extract_post_data(submission)
                if post_data and self.validate_post_schema(post_data):
                    posts.append(post_data)
            
            for submission in subreddit.hot(limit=limit//2):
                post_data = self.extract_post_data(submission)
                if post_data and self.validate_post_schema(post_data):
                    # Avoid duplicates
                    if not any(p['id'] == post_data['id'] for p in posts):
                        posts.append(post_data)
            
            logger.info(f"Fetched {len(posts)} valid posts from r/{subreddit_name}")
            return posts
            
        except PrawcoreException as e:
            logger.error(f"Reddit API error for r/{subreddit_name}: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error fetching from r/{subreddit_name}: {e}")
            return []
    
    def send_to_kafka(self, post: Dict, topic: str) -> bool:
        """
        Send post to Kafka topic with error handling
        
        Args:
            post: Post data dictionary
            topic: Kafka topic name
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            future = self.producer.send(topic, value=post, key=post['id'].encode('utf-8'))
            # Wait for acknowledgment
            record_metadata = future.get(timeout=10)
            logger.debug(f"Sent post {post['id']} to topic {topic} partition {record_metadata.partition}")
            return True
        except KafkaError as e:
            logger.error(f"Kafka error sending post {post['id']}: {e}")
            self.error_count += 1
            return False
        except Exception as e:
            logger.error(f"Unexpected error sending post {post['id']}: {e}")
            self.error_count += 1
            return False
    
    def run(self, duration_seconds: Optional[int] = None, fetch_interval: int = 300):
        """
        Main run loop - continuously fetch and produce posts
        
        Args:
            duration_seconds: How long to run (None for indefinite)
            fetch_interval: Seconds between fetch cycles
        """
        logger.info("Starting Reddit Kafka Producer")
        start_time = time.time()
        topic = os.getenv('KAFKA_TOPIC_PREFIX', 'reddit') + '_raw_posts'
        
        try:
            while True:
                cycle_start = time.time()
                logger.info(f"Starting fetch cycle at {datetime.utcnow().isoformat()}")
                
                for subreddit_name in self.subreddits:
                    try:
                        posts = self.fetch_posts_from_subreddit(subreddit_name, limit=100)
                        
                        for post in posts:
                            if self.send_to_kafka(post, topic):
                                self.post_count += 1
                        
                        # Rate limiting - respect Reddit API limits
                        time.sleep(2)
                        
                    except Exception as e:
                        logger.error(f"Error processing subreddit {subreddit_name}: {e}")
                        continue
                
                # Log metrics
                cycle_duration = time.time() - cycle_start
                logger.info(f"Cycle completed in {cycle_duration:.2f}s. "
                          f"Total posts: {self.post_count}, Errors: {self.error_count}")
                
                # Check duration limit
                if duration_seconds and (time.time() - start_time) >= duration_seconds:
                    logger.info(f"Reached duration limit of {duration_seconds}s. Shutting down.")
                    break
                
                # Wait before next cycle
                sleep_time = max(0, fetch_interval - cycle_duration)
                if sleep_time > 0:
                    logger.info(f"Sleeping for {sleep_time:.2f}s before next cycle")
                    time.sleep(sleep_time)
                    
        except KeyboardInterrupt:
            logger.info("Received interrupt signal. Shutting down gracefully...")
        finally:
            self.close()
    
    def close(self):
        """Clean up resources"""
        logger.info(f"Closing producer. Final stats - Posts: {self.post_count}, Errors: {self.error_count}")
        self.producer.flush()
        self.producer.close()


def main():
    """Entry point for the producer"""
    producer = RedditKafkaProducer()
    # Run for 1 hour by default (3600 seconds), or indefinitely if not specified
    producer.run(duration_seconds=None, fetch_interval=300)


if __name__ == '__main__':
    main()