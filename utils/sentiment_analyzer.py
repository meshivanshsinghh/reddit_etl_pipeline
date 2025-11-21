"""
Simple sentiment analysis using VADER
Adds sentiment scores to existing posts
"""

import os
import psycopg2
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

def analyze_post_sentiment(text: str) -> dict:
    """Analyze sentiment of text"""
    analyzer = SentimentIntensityAnalyzer()
    if not text or text.strip() == "":
        return {'compound': 0.0, 'category': 'neutral'}
    
    scores = analyzer.polarity_scores(text)
    compound = scores['compound']
    
    # Categorize
    if compound >= 0.05:
        category = 'positive'
    elif compound <= -0.05:
        category = 'negative'
    else:
        category = 'neutral'
    
    return {'compound': compound, 'category': category}


def add_sentiment_to_posts():
    """Add sentiment scores to all posts without sentiment"""
    conn = psycopg2.connect(
        host=os.getenv('POSTGRES_HOST', 'postgres'),
        port=os.getenv('POSTGRES_PORT', '5432'),
        database=os.getenv('POSTGRES_DB', 'reddit_pipeline'),
        user=os.getenv('POSTGRES_USER', 'reddit_user'),
        password=os.getenv('POSTGRES_PASSWORD', 'reddit_pass')
    )
    cursor = conn.cursor()
    
    # Get posts
    cursor.execute("""
        SELECT id, title, selftext, subreddit, created_utc
        FROM posts_raw
        ORDER BY created_utc DESC
    """)
    
    posts = cursor.fetchall()
    print(f"Processing sentiment for {len(posts)} posts...")
    
    processed = 0
    positive = 0
    negative = 0
    neutral = 0
    
    for post_id, title, selftext, subreddit, created_utc in posts:
        # Combine title and selftext
        combined_text = f"{title} {selftext or ''}"
        
        # Analyze sentiment
        sentiment = analyze_post_sentiment(combined_text)
        
        # Insert into sentiment_timeseries (minute-level aggregation)
        created_minute = created_utc.replace(second=0, microsecond=0)
        
        cursor.execute("""
            INSERT INTO sentiment_timeseries 
            (timestamp, subreddit, posts_count, avg_sentiment, 
             positive_count, negative_count, neutral_count)
            VALUES (%s, %s, 1, %s, %s, %s, %s)
        """, (
            created_minute,
            subreddit,
            sentiment['compound'],
            1 if sentiment['category'] == 'positive' else 0,
            1 if sentiment['category'] == 'negative' else 0,
            1 if sentiment['category'] == 'neutral' else 0
        ))
        
        processed += 1
        if sentiment['category'] == 'positive':
            positive += 1
        elif sentiment['category'] == 'negative':
            negative += 1
        else:
            neutral += 1
        
        if processed % 50 == 0:
            conn.commit()
            print(f"Processed {processed}/{len(posts)} posts...")
    
    conn.commit()
    cursor.close()
    conn.close()
    
    print(f"\n✅ Sentiment Analysis Complete!")
    print(f"   Positive: {positive} ({positive/len(posts)*100:.1f}%)")
    print(f"   Negative: {negative} ({negative/len(posts)*100:.1f}%)")
    print(f"   Neutral: {neutral} ({neutral/len(posts)*100:.1f}%)")
    
    return {
        'total': len(posts),
        'positive': positive,
        'negative': negative,
        'neutral': neutral
    }


if __name__ == '__main__':
    add_sentiment_to_posts()