import { NextResponse } from 'next/server';
import { getTopics } from '@/lib/queries';

export const dynamic = 'force-dynamic';

export async function GET(request: Request) {
  try {
    const { searchParams } = new URL(request.url);
    const limit = parseInt(searchParams.get('limit') || '20');
    
    const topics = await getTopics(limit);
    
    return NextResponse.json({
      data: topics,
      timestamp: new Date().toISOString(),
    });
  } catch (error) {
    console.error('Error fetching topics:', error);
    return NextResponse.json(
      {
        error: 'Failed to fetch topics',
        message: error instanceof Error ? error.message : 'Unknown error',
      },
      { status: 500 }
    );
  }
}

