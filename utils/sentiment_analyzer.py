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
    """Add sentiment scores to posts that don't have sentiment yet"""
    conn = psycopg2.connect(
        host=os.getenv('POSTGRES_HOST', 'postgres'),
        port=os.getenv('POSTGRES_PORT', '5432'),
        database=os.getenv('POSTGRES_DB', 'reddit_pipeline'),
        user=os.getenv('POSTGRES_USER', 'reddit_user'),
        password=os.getenv('POSTGRES_PASSWORD', 'reddit_pass')
    )
    cursor = conn.cursor()
    cursor.execute("""
        SELECT p.id, p.title, p.selftext, p.subreddit, p.created_utc
        FROM posts_raw p
        LEFT JOIN sentiment_timeseries s 
            ON p.subreddit = s.subreddit
            AND DATE_TRUNC('minute', p.created_utc) = s.timestamp
        WHERE s.id IS NULL
        ORDER BY p.created_utc DESC
    """)
    
    posts = cursor.fetchall()
    
    if len(posts) == 0:
        print("No new posts to analyze")
        cursor.close()
        conn.close()
        return {
            'total': 0,
            'positive': 0,
            'negative': 0,
            'neutral': 0
        }
    
    print(f"Processing sentiment for {len(posts)} NEW posts...")
    
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
            ON CONFLICT (timestamp, subreddit) 
            DO UPDATE SET
                posts_count = sentiment_timeseries.posts_count + 1,
                avg_sentiment = (
                    (sentiment_timeseries.avg_sentiment * sentiment_timeseries.posts_count + EXCLUDED.avg_sentiment) 
                    / (sentiment_timeseries.posts_count + 1)
                ),
                positive_count = sentiment_timeseries.positive_count + EXCLUDED.positive_count,
                negative_count = sentiment_timeseries.negative_count + EXCLUDED.negative_count,
                neutral_count = sentiment_timeseries.neutral_count + EXCLUDED.neutral_count
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