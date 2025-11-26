import { NextResponse } from 'next/server';
import { getSubredditStats } from '@/lib/queries';

export const dynamic = 'force-dynamic';

export async function GET() {
  try {
    const subreddits = await getSubredditStats();
    
    return NextResponse.json({
      data: subreddits,
      timestamp: new Date().toISOString(),
    });
  } catch (error) {
    console.error('Error fetching subreddit stats:', error);
    return NextResponse.json(
      {
        error: 'Failed to fetch subreddit statistics',
        message: error instanceof Error ? error.message : 'Unknown error',
      },
      { status: 500 }
    );
  }
}

