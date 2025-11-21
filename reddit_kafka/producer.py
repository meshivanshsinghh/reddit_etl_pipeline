"""
Reddit JSON Scraper Producer - Uses Reddit's public JSON API
No authentication required - works immediately!
"""

import os
import time
import json
import logging
import requests
from datetime import datetime
from typing import Dict, List, Optional
from kafka import KafkaProducer
from kafka.errors import KafkaError
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class RedditJSONProducer:
    """
    Fetches Reddit posts using public JSON API (no authentication needed)
    """
    
    def __init__(self):
        """Initialize Kafka producer"""
        self.producer = self._initialize_kafka_producer()
        self.subreddits = self._load_subreddits()
        self.post_count = 0
        self.error_count = 0
        self.user_agent = os.getenv('REDDIT_USER_AGENT', 'RedditEnergyPipeline/1.0')
        
    def _initialize_kafka_producer(self) -> KafkaProducer:
        """Initialize Kafka producer with configuration"""
        try:
            producer = KafkaProducer(
                bootstrap_servers=os.getenv('KAFKA_BOOTSTRAP_SERVERS', 'localhost:9092'),
                value_serializer=lambda v: json.dumps(v).encode('utf-8'),
                compression_type='gzip',
                acks='all',
                retries=3,
                max_in_flight_requests_per_connection=1
            )
            logger.info("Kafka producer initialized successfully")
            return producer
        except Exception as e:
            logger.error(f"Failed to initialize Kafka producer: {e}")
            raise
    
    def _load_subreddits(self) -> List[str]:
        """Load target subreddits from config"""
        return [
            'TeslaMotors',
            'solar',
            'TeslaEnergy',
            'Powerwall',
            'electricvehicles',
            'renewable',
            'TeslaLounge',
            'TeslaModel3',
            'TeslaModelS',
            'TeslaModelX',
            'TeslaModelY',
            'Superchargers',
            'TeslaSupport',
            'electriccars'
        ]
    
    def fetch_reddit_json(self, subreddit: str, limit: int = 50) -> List[Dict]:
        """
        Fetch posts using Reddit's public JSON API
        
        Args:
            subreddit: Name of the subreddit
            limit: Maximum number of posts to fetch (max 100)
            
        Returns:
            List of post dictionaries
        """
        posts = []
        
        try:
            # Reddit's public JSON endpoint
            url = f"https://www.reddit.com/r/{subreddit}/new.json"
            headers = {'User-Agent': self.user_agent}
            params = {'limit': min(limit, 100)}
            
            logger.info(f"Fetching posts from r/{subreddit}")
            response = requests.get(url, headers=headers, params=params, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                
                for child in data['data']['children']:
                    post_data = child['data']
                    
                    # Extract and normalize post data
                    post = {
                        'id': post_data.get('id'),
                        'title': post_data.get('title', ''),
                        'selftext': post_data.get('selftext', ''),
                        'author': post_data.get('author', '[deleted]'),
                        'subreddit': post_data.get('subreddit'),
                        'created_utc': datetime.fromtimestamp(
                            post_data.get('created_utc', 0)
                        ).isoformat(),
                        'score': post_data.get('score', 0),
                        'num_comments': post_data.get('num_comments', 0),
                        'url': post_data.get('url', ''),
                        'permalink': f"https://reddit.com{post_data.get('permalink', '')}",
                        'upvote_ratio': post_data.get('upvote_ratio', 0.0),
                        'is_self': post_data.get('is_self', False),
                        'link_flair_text': post_data.get('link_flair_text'),
                        'ingested_at': datetime.utcnow().isoformat()
                    }
                    
                    # Validate required fields
                    if self.validate_post_schema(post):
                        posts.append(post)
                
                logger.info(f"Fetched {len(posts)} valid posts from r/{subreddit}")
            else:
                logger.error(f"HTTP {response.status_code} for r/{subreddit}: {response.text}")
                self.error_count += 1
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Network error fetching r/{subreddit}: {e}")
            self.error_count += 1
        except Exception as e:
            logger.error(f"Unexpected error fetching r/{subreddit}: {e}")
            self.error_count += 1
        
        return posts
    
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
            future = self.producer.send(
                topic, 
                value=post, 
                key=post['id'].encode('utf-8')
            )
            # Wait for acknowledgment
            record_metadata = future.get(timeout=10)
            logger.debug(
                f"Sent post {post['id']} to {topic} "
                f"partition {record_metadata.partition}"
            )
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
            fetch_interval: Seconds between fetch cycles (default 300 = 5 min)
        """
        logger.info("🚀 Starting Reddit JSON Scraper Producer")
        logger.info("✅ No authentication required - using public JSON API")
        start_time = time.time()
        topic = os.getenv('KAFKA_TOPIC_PREFIX', 'reddit') + '_raw_posts'
        
        try:
            while True:
                cycle_start = time.time()
                logger.info(f"📥 Starting fetch cycle at {datetime.utcnow().isoformat()}")
                
                for subreddit_name in self.subreddits:
                    try:
                        # Fetch posts from Reddit
                        posts = self.fetch_reddit_json(subreddit_name, limit=50)
                        
                        # Send to Kafka
                        for post in posts:
                            if self.send_to_kafka(post, topic):
                                self.post_count += 1
                        
                        # Rate limiting - be nice to Reddit
                        # Reddit allows ~60 requests/min, so 2s between requests is safe
                        time.sleep(2)
                        
                    except Exception as e:
                        logger.error(f"Error processing subreddit {subreddit_name}: {e}")
                        continue
                
                # Log metrics
                cycle_duration = time.time() - cycle_start
                logger.info(
                    f"✅ Cycle completed in {cycle_duration:.2f}s. "
                    f"Total posts: {self.post_count}, Errors: {self.error_count}"
                )
                
                # Check duration limit
                if duration_seconds and (time.time() - start_time) >= duration_seconds:
                    logger.info(f"⏰ Reached duration limit of {duration_seconds}s. Shutting down.")
                    break
                
                # Wait before next cycle
                sleep_time = max(0, fetch_interval - cycle_duration)
                if sleep_time > 0:
                    logger.info(f"💤 Sleeping for {sleep_time:.2f}s before next cycle")
                    time.sleep(sleep_time)
                    
        except KeyboardInterrupt:
            logger.info("⚠️ Received interrupt signal. Shutting down gracefully...")
        finally:
            self.close()
    
    def close(self):
        """Clean up resources"""
        logger.info(
            f"🛑 Closing producer. Final stats - "
            f"Posts: {self.post_count}, Errors: {self.error_count}"
        )
        self.producer.flush()
        self.producer.close()


def main():
    """Entry point for the producer"""
    producer = RedditJSONProducer()
    # Run for 5 minutes for testing (300 seconds), or indefinitely
    producer.run(duration_seconds=300, fetch_interval=60)


if __name__ == '__main__':
    main()