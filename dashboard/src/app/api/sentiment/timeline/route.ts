import { NextResponse } from 'next/server';
import { getSentimentTimeline } from '@/lib/queries';

export const dynamic = 'force-dynamic';

export async function GET(request: Request) {
  try {
    const { searchParams } = new URL(request.url);
    const days = parseInt(searchParams.get('days') || '7');
    const subreddit = searchParams.get('subreddit') || undefined;
    
    const timeline = await getSentimentTimeline(days, subreddit);
    
    return NextResponse.json({
      data: timeline,
      timestamp: new Date().toISOString(),
    });
  } catch (error) {
    console.error('Error fetching sentiment timeline:', error);
    return NextResponse.json(
      {
        error: 'Failed to fetch sentiment timeline',
        message: error instanceof Error ? error.message : 'Unknown error',
      },
      { status: 500 }
    );
  }
}

