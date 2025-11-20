"""
Spark Streaming Job for Real-time Reddit Sentiment Analysis
Consumes from Kafka, performs sentiment analysis, detects anomalies
"""

import os
import json
from datetime import datetime
from typing import Dict, List

from pyspark.sql import SparkSession
from pyspark.sql.functions import (
    col, from_json, window, avg, count, sum as spark_sum,
    udf, current_timestamp, expr, collect_list, desc, stddev
)
from pyspark.sql.types import (
    StructType, StructField, StringType, IntegerType, 
    FloatType, BooleanType, TimestampType
)
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
from dotenv import load_dotenv

load_dotenv()

# Initialize sentiment analyzer
sentiment_analyzer = SentimentIntensityAnalyzer()


def analyze_sentiment(text: str) -> float:
    """
    Analyze sentiment of text using VADER
    
    Args:
        text: Input text to analyze
        
    Returns:
        Compound sentiment score between -1 (negative) and 1 (positive)
    """
    if not text or text.strip() == "":
        return 0.0
    
    scores = sentiment_analyzer.polarity_scores(text)
    return scores['compound']


def categorize_sentiment(score: float) -> str:
    """
    Categorize sentiment score into positive/negative/neutral
    
    Args:
        score: Sentiment score
        
    Returns:
        Category string
    """
    if score >= 0.05:
        return "positive"
    elif score <= -0.05:
        return "negative"
    else:
        return "neutral"


class RedditSentimentStreaming:
    """
    Spark Streaming application for real-time sentiment analysis
    """
    
    def __init__(self):
        """Initialize Spark session and configurations"""
        self.spark = self._create_spark_session()
        self.kafka_servers = os.getenv('KAFKA_BOOTSTRAP_SERVERS', 'kafka:29092')
        self.checkpoint_dir = os.getenv('SPARK_CHECKPOINT_DIR', '/tmp/spark-checkpoints')
        self.postgres_url = os.getenv('POSTGRES_CONNECTION_STRING', 
                                     'jdbc:postgresql://postgres:5432/reddit_pipeline')
        self.postgres_properties = {
            "user": os.getenv('POSTGRES_USER', 'reddit_user'),
            "password": os.getenv('POSTGRES_PASSWORD', 'reddit_pass'),
            "driver": "org.postgresql.Driver"
        }
        
    def _create_spark_session(self) -> SparkSession:
        """Create Spark session with required configurations"""
        return SparkSession.builder \
            .appName("RedditSentimentStreaming") \
            .config("spark.jars.packages", 
                   "org.apache.spark:spark-sql-kafka-0-10_2.12:3.5.0,"
                   "org.postgresql:postgresql:42.6.0") \
            .config("spark.sql.streaming.checkpointLocation", self.checkpoint_dir) \
            .config("spark.sql.shuffle.partitions", "3") \
            .getOrCreate()
    
    def define_schema(self) -> StructType:
        """Define schema for incoming Reddit posts"""
        return StructType([
            StructField("id", StringType(), False),
            StructField("title", StringType(), False),
            StructField("selftext", StringType(), True),
            StructField("author", StringType(), True),
            StructField("subreddit", StringType(), False),
            StructField("created_utc", StringType(), False),
            StructField("score", IntegerType(), True),
            StructField("num_comments", IntegerType(), True),
            StructField("url", StringType(), True),
            StructField("permalink", StringType(), True),
            StructField("upvote_ratio", FloatType(), True),
            StructField("is_self", BooleanType(), True),
            StructField("link_flair_text", StringType(), True),
            StructField("ingested_at", StringType(), True)
        ])
    
    def read_from_kafka(self):
        """Read streaming data from Kafka"""
        schema = self.define_schema()
        
        # Register UDFs
        sentiment_udf = udf(analyze_sentiment, FloatType())
        category_udf = udf(categorize_sentiment, StringType())
        
        # Read from Kafka
        df = self.spark \
            .readStream \
            .format("kafka") \
            .option("kafka.bootstrap.servers", self.kafka_servers) \
            .option("subscribe", "reddit_raw_posts") \
            .option("startingOffsets", "latest") \
            .option("maxOffsetsPerTrigger", "1000") \
            .load()
        
        # Parse JSON and extract fields
        parsed_df = df.select(
            from_json(col("value").cast("string"), schema).alias("data"),
            col("timestamp").alias("kafka_timestamp")
        ).select("data.*", "kafka_timestamp")
        
        # Combine title and selftext for sentiment analysis
        combined_text = expr("CONCAT(title, ' ', COALESCE(selftext, ''))")
        
        # Add sentiment analysis
        enriched_df = parsed_df \
            .withColumn("combined_text", combined_text) \
            .withColumn("sentiment_score", sentiment_udf(col("combined_text"))) \
            .withColumn("sentiment_category", category_udf(col("sentiment_score"))) \
            .withColumn("processed_at", current_timestamp()) \
            .withColumn("created_timestamp", col("created_utc").cast(TimestampType()))
        
        return enriched_df
    
    def write_to_postgres_raw(self, df, epoch_id):
        """
        Write raw posts to PostgreSQL
        
        Args:
            df: DataFrame to write
            epoch_id: Micro-batch ID
        """
        try:
            # Select and rename columns to match database schema
            posts_df = df.select(
                col("id"),
                col("title"),
                col("selftext"),
                col("author"),
                col("subreddit"),
                col("created_timestamp").alias("created_utc"),
                col("score"),
                col("num_comments"),
                col("url"),
                col("permalink"),
                col("upvote_ratio"),
                col("is_self"),
                col("link_flair_text"),
                col("ingested_at").cast(TimestampType())
            )
            
            # Write to PostgreSQL (append mode with duplicate handling)
            posts_df.write \
                .jdbc(
                    url=self.postgres_url,
                    table="posts_raw",
                    mode="append",
                    properties=self.postgres_properties
                )
            
            print(f"Batch {epoch_id}: Wrote {posts_df.count()} posts to posts_raw")
            
        except Exception as e:
            print(f"Error writing to posts_raw: {e}")
    
    def compute_aggregations(self, enriched_df):
        """
        Compute time-series aggregations
        
        Args:
            enriched_df: Enriched DataFrame with sentiment
            
        Returns:
            Aggregated DataFrame
        """
        # Aggregate by 1-minute windows and subreddit
        aggregated_df = enriched_df \
            .withWatermark("created_timestamp", "10 minutes") \
            .groupBy(
                window(col("created_timestamp"), "1 minute"),
                col("subreddit")
            ) \
            .agg(
                count("*").alias("posts_count"),
                avg("sentiment_score").alias("avg_sentiment"),
                spark_sum(expr("CASE WHEN sentiment_category = 'positive' THEN 1 ELSE 0 END")).alias("positive_count"),
                spark_sum(expr("CASE WHEN sentiment_category = 'negative' THEN 1 ELSE 0 END")).alias("negative_count"),
                spark_sum(expr("CASE WHEN sentiment_category = 'neutral' THEN 1 ELSE 0 END")).alias("neutral_count"),
                avg("score").alias("avg_score"),
                spark_sum("num_comments").alias("total_comments"),
                stddev("sentiment_score").alias("sentiment_std_dev")
            ) \
            .select(
                col("window.start").alias("timestamp"),
                col("subreddit"),
                col("posts_count"),
                col("avg_sentiment"),
                col("positive_count"),
                col("negative_count"),
                col("neutral_count"),
                col("avg_score"),
                col("total_comments"),
                col("sentiment_std_dev")
            )
        
        return aggregated_df
    
    def detect_anomalies(self, aggregated_df):
        """
        Detect anomalies in sentiment (simple threshold-based)
        
        Args:
            aggregated_df: Aggregated DataFrame
            
        Returns:
            DataFrame with anomaly flags
        """
        # Simple anomaly detection: negative sentiment > threshold
        threshold = float(os.getenv('NEGATIVE_SENTIMENT_THRESHOLD', '0.3'))
        
        anomaly_df = aggregated_df \
            .withColumn(
                "anomaly_detected",
                (col("avg_sentiment") < -threshold) | 
                (col("sentiment_std_dev") > 0.5)
            ) \
            .withColumn(
                "anomaly_score",
                expr("ABS(avg_sentiment) * sentiment_std_dev")
            )
        
        return anomaly_df
    
    def write_aggregations_to_postgres(self, df, epoch_id):
        """
        Write aggregated data to PostgreSQL
        
        Args:
            df: DataFrame to write
            epoch_id: Micro-batch ID
        """
        try:
            df.write \
                .jdbc(
                    url=self.postgres_url,
                    table="sentiment_timeseries",
                    mode="append",
                    properties=self.postgres_properties
                )
            
            print(f"Batch {epoch_id}: Wrote {df.count()} aggregations to sentiment_timeseries")
            
        except Exception as e:
            print(f"Error writing aggregations: {e}")
    
    def run(self):
        """Main execution method"""
        print("Starting Reddit Sentiment Streaming Job...")
        
        # Read from Kafka
        enriched_df = self.read_from_kafka()
        
        # Write raw posts to PostgreSQL
        raw_query = enriched_df.writeStream \
            .foreachBatch(self.write_to_postgres_raw) \
            .outputMode("append") \
            .option("checkpointLocation", f"{self.checkpoint_dir}/raw_posts") \
            .start()
        
        # Compute aggregations
        aggregated_df = self.compute_aggregations(enriched_df)
        
        # Detect anomalies
        anomaly_df = self.detect_anomalies(aggregated_df)
        
        # Write aggregations to PostgreSQL
        agg_query = anomaly_df.writeStream \
            .foreachBatch(self.write_aggregations_to_postgres) \
            .outputMode("append") \
            .option("checkpointLocation", f"{self.checkpoint_dir}/aggregations") \
            .start()
        
        # Console output for monitoring
        console_query = enriched_df \
            .select("id", "subreddit", "sentiment_score", "sentiment_category") \
            .writeStream \
            .outputMode("append") \
            .format("console") \
            .option("truncate", "false") \
            .option("numRows", "5") \
            .start()
        
        # Wait for termination
        print("Streaming job running. Press Ctrl+C to stop.")
        self.spark.streams.awaitAnyTermination()


def main():
    """Entry point"""
    streaming_job = RedditSentimentStreaming()
    streaming_job.run()


if __name__ == "__main__":
    main()