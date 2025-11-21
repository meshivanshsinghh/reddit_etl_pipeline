import os
import sys
import psycopg2
from typing import List, Dict, Tuple
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.cluster import KMeans
from collections import Counter

# Add project root to path for imports
sys.path.insert(0, os.getenv('AIRFLOW_HOME', '/opt/airflow'))
from utils.logger import setup_logger

logger = setup_logger(__name__)


class TopicExtractor:
    """Extract topics and cluster issues from Reddit posts"""
    
    def __init__(self):
        """Initialize database connection"""
        self.conn = psycopg2.connect(
            host=os.getenv('POSTGRES_HOST', 'localhost'),
            port=os.getenv('POSTGRES_PORT', '5432'),
            database=os.getenv('POSTGRES_DB', 'reddit_pipeline'),
            user=os.getenv('POSTGRES_USER', 'reddit_user'),
            password=os.getenv('POSTGRES_PASSWORD', 'reddit_pass')
        )
        logger.info("Connected to PostgreSQL for topic extraction")
    
    def fetch_posts(self) -> List[Dict]:
        """Fetch all posts with sentiment data from database
        
        Returns:
            List of post dictionaries with id, text, subreddit, sentiment
        """
        
        query = """
            WITH post_sentiment AS (
                SELECT 
                    p.id,
                    p.title,
                    p.selftext,
                    p.subreddit,
                    p.created_utc,
                    AVG(s.avg_sentiment) as avg_sentiment
                FROM posts_raw p
                LEFT JOIN sentiment_timeseries s 
                    ON p.subreddit = s.subreddit
                    AND DATE_TRUNC('minute', p.created_utc) = s.timestamp
                WHERE p.title IS NOT NULL
                GROUP BY p.id, p.title, p.selftext, p.subreddit, p.created_utc
            )
            SELECT 
                id,
                title,
                selftext,
                subreddit,
                COALESCE(avg_sentiment, 0) as sentiment
            FROM post_sentiment
            ORDER BY created_utc DESC
        """
        
        with self.conn.cursor() as cur:
            cur.execute(query)
            rows = cur.fetchall()
            
            posts = []
            for row in rows:
                # Combine title and selftext for full context
                text = row[1]
                if row[2]:  # Add selftext if exists
                    text = f"{text} {row[2]}"
                
                posts.append({
                    'id': row[0],
                    'text': text,
                    'subreddit': row[3],
                    'sentiment': float(row[4]) if row[4] else 0.0
                })
            
            logger.info(f"Fetched {len(posts)} posts for topic extraction")
            return posts
    
    def extract_keywords_by_subreddit(self, posts: List[Dict], top_n: int = 10) -> Dict[str, List[Tuple[str, float]]]:
        """Extract top keywords per subreddit using TF-IDF
        
        Args:
            posts: List of post dictionaries
            top_n: Number of top keywords to extract per subreddit
            
        Returns:
            Dictionary mapping subreddit to list of (keyword, score) tuples
        """
        subreddit_keywords = {}
        
        # Group posts by subreddit
        subreddit_posts = {}
        for post in posts:
            subreddit = post['subreddit']
            if subreddit not in subreddit_posts:
                subreddit_posts[subreddit] = []
            subreddit_posts[subreddit].append(post)
        
        # Extract keywords for each subreddit
        for subreddit, sub_posts in subreddit_posts.items():
            texts = [p['text'] for p in sub_posts]
            
            try:
                # TF-IDF vectorization with English stop words
                vectorizer = TfidfVectorizer(
                    max_features=100,
                    stop_words='english',
                    ngram_range=(1, 2),  # Unigrams and bigrams
                    min_df=2,  # Ignore terms that appear in less than 2 documents
                    max_df=0.8  # Ignore terms that appear in more than 80% of documents
                )
                
                tfidf_matrix = vectorizer.fit_transform(texts)
                feature_names = vectorizer.get_feature_names_out()
                
                # Calculate average TF-IDF score for each term
                avg_scores = np.asarray(tfidf_matrix.mean(axis=0)).flatten()
                
                # Get top N keywords
                top_indices = avg_scores.argsort()[-top_n:][::-1]
                keywords = [(feature_names[i], float(avg_scores[i])) for i in top_indices]
                
                subreddit_keywords[subreddit] = keywords
                logger.info(f"Extracted {len(keywords)} keywords for r/{subreddit}")
                
            except Exception as e:
                logger.error(f"Error extracting keywords for r/{subreddit}: {e}")
                subreddit_keywords[subreddit] = []
        
        return subreddit_keywords
    
    def cluster_posts(self, posts: List[Dict], n_clusters: int = 7) -> List[Dict]:
        """Cluster posts using K-Means on TF-IDF vectors
        
        Args:
            posts: List of post dictionaries
            n_clusters: Number of clusters to create
            
        Returns:
            List of cluster dictionaries with metadata
        """
        if len(posts) < n_clusters:
            logger.warning(f"Not enough posts ({len(posts)}) for {n_clusters} clusters")
            n_clusters = max(2, len(posts) // 10)
        
        texts = [p['text'] for p in posts]
        
        # TF-IDF vectorization
        vectorizer = TfidfVectorizer(
            max_features=200,
            stop_words='english',
            ngram_range=(1, 2),
            min_df=2
        )
        
        tfidf_matrix = vectorizer.fit_transform(texts)
        feature_names = vectorizer.get_feature_names_out()
        
        # K-Means clustering
        kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
        cluster_labels = kmeans.fit_predict(tfidf_matrix)
        
        # Analyze each cluster
        clusters = []
        for cluster_id in range(n_clusters):
            # Get posts in this cluster
            cluster_indices = [i for i, label in enumerate(cluster_labels) if label == cluster_id]
            cluster_posts = [posts[i] for i in cluster_indices]
            
            if not cluster_posts:
                continue
            
            # Calculate cluster statistics
            post_ids = [p['id'] for p in cluster_posts]
            sentiments = [p['sentiment'] for p in cluster_posts]
            avg_sentiment = np.mean(sentiments)
            
            # Extract top keywords for this cluster
            cluster_center = kmeans.cluster_centers_[cluster_id]
            top_indices = cluster_center.argsort()[-5:][::-1]
            keywords = [feature_names[i] for i in top_indices]
            
            # Generate cluster name from top keywords
            cluster_name = ' | '.join(keywords[:3])
            
            # Assign severity based on negative sentiment and volume
            severity = self._calculate_severity(avg_sentiment, len(cluster_posts))
            
            clusters.append({
                'cluster_id': int(cluster_id),
                'cluster_name': cluster_name,
                'post_ids': post_ids,
                'keywords': keywords,
                'avg_sentiment': float(avg_sentiment),
                'post_count': len(cluster_posts),
                'severity': severity
            })
            
            logger.info(f"Cluster {cluster_id}: {len(cluster_posts)} posts, sentiment={avg_sentiment:.3f}, severity={severity}")
        
        return clusters
    
    def _calculate_severity(self, avg_sentiment: float, post_count: int) -> str:
        """Calculate issue severity based on sentiment and volume
        
        Args:
            avg_sentiment: Average sentiment score (-1 to 1)
            post_count: Number of posts in cluster
            
        Returns:
            Severity level: CRITICAL, HIGH, MEDIUM, or LOW
        """
        # Normalize post count (assume 10+ posts is high volume)
        volume_score = min(post_count / 10.0, 1.0)
        
        # Calculate severity score (0-1)
        # Negative sentiment + high volume = high severity
        negativity = max(0, -avg_sentiment)  # 0 to 1
        severity_score = (negativity * 0.7) + (volume_score * 0.3)
        
        if severity_score > 0.7:
            return 'CRITICAL'
        elif severity_score > 0.5:
            return 'HIGH'
        elif severity_score > 0.3:
            return 'MEDIUM'
        else:
            return 'LOW'
    
    def save_keywords(self, subreddit_keywords: Dict[str, List[Tuple[str, float]]], posts: List[Dict]):
        """Save extracted keywords to database with actual post counts and sentiment
        
        Args:
            subreddit_keywords: Dictionary mapping subreddit to (keyword, score) tuples
            posts: List of post dictionaries (to calculate counts and sentiment)
        """
        with self.conn.cursor() as cur:
            # Clear existing keywords
            cur.execute("DELETE FROM topics")
            
            # Insert new keywords with calculated counts and sentiment
            for subreddit, keywords in subreddit_keywords.items():
                # Get posts for this subreddit
                subreddit_posts = [p for p in posts if p['subreddit'] == subreddit]
                
                for keyword, score in keywords:
                    # Find posts containing this keyword (case-insensitive)
                    keyword_posts = [
                        p for p in subreddit_posts 
                        if keyword.lower() in p['text'].lower()
                    ]
                    
                    # Calculate post count and average sentiment
                    post_count = len(keyword_posts)
                    if post_count > 0:
                        avg_sentiment = np.mean([p['sentiment'] for p in keyword_posts])
                    else:
                        avg_sentiment = 0.0
                    
                    cur.execute("""
                        INSERT INTO topics (subreddit, keyword, score, post_count, avg_sentiment)
                        VALUES (%s, %s, %s, %s, %s)
                    """, (subreddit, keyword, score, post_count, float(avg_sentiment)))
            
            self.conn.commit()
            total_keywords = sum(len(kw) for kw in subreddit_keywords.values())
            logger.info(f"Saved {total_keywords} keywords to database with counts and sentiment")
    
    def save_clusters(self, clusters: List[Dict]):
        """Save issue clusters to database
        
        Args:
            clusters: List of cluster dictionaries
        """
        with self.conn.cursor() as cur:
            # Clear existing clusters
            cur.execute("DELETE FROM issue_clusters")
            
            # Insert new clusters
            for cluster in clusters:
                cur.execute("""
                    INSERT INTO issue_clusters 
                    (cluster_id, cluster_name, post_ids, keywords, avg_sentiment, post_count, severity)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                """, (
                    cluster['cluster_id'],
                    cluster['cluster_name'],
                    cluster['post_ids'],
                    cluster['keywords'],
                    cluster['avg_sentiment'],
                    cluster['post_count'],
                    cluster['severity']
                ))
            
            self.conn.commit()
            logger.info(f"Saved {len(clusters)} clusters to database")
    
    def run(self):
        """Execute full topic extraction pipeline"""
        try:
            logger.info("Starting topic extraction pipeline")
            
            # Step 1: Fetch posts
            posts = self.fetch_posts()
            if not posts:
                logger.warning("No posts found for topic extraction")
                return
            
            # Step 2: Extract keywords by subreddit
            logger.info("Extracting keywords by subreddit")
            subreddit_keywords = self.extract_keywords_by_subreddit(posts, top_n=10)
            self.save_keywords(subreddit_keywords, posts)
            
            # Step 3: Cluster all posts
            logger.info("Clustering posts to identify issues")
            clusters = self.cluster_posts(posts, n_clusters=7)
            self.save_clusters(clusters)
            
            logger.info("Topic extraction completed successfully")
            
        except Exception as e:
            logger.error(f"Error in topic extraction pipeline: {e}")
            raise
        finally:
            self.conn.close()


def main():
    """Main entry point"""
    extractor = TopicExtractor()
    extractor.run()


if __name__ == '__main__':
    main()