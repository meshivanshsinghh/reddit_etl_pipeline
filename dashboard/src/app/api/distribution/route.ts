import { NextResponse } from 'next/server';
import { getSentimentDistribution, getPostsBySubreddit } from '@/lib/queries';

export const dynamic = 'force-dynamic';

export async function GET() {
  try {
    const [sentimentDist, subredditDist] = await Promise.all([
      getSentimentDistribution(),
      getPostsBySubreddit(),
    ]);
    
    return NextResponse.json({
      data: {
        sentiment: sentimentDist,
        subreddits: subredditDist,
      },
      timestamp: new Date().toISOString(),
    });
  } catch (error) {
    console.error('Error fetching distribution data:', error);
    return NextResponse.json(
      {
        error: 'Failed to fetch distribution data',
        message: error instanceof Error ? error.message : 'Unknown error',
      },
      { status: 500 }
    );
  }
}

