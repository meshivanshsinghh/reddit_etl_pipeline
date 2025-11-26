import { NextResponse } from 'next/server';
import { getClusters } from '@/lib/queries';

export const dynamic = 'force-dynamic';

export async function GET() {
  try {
    const clusters = await getClusters();
    
    return NextResponse.json({
      data: clusters,
      timestamp: new Date().toISOString(),
    });
  } catch (error) {
    console.error('Error fetching clusters:', error);
    return NextResponse.json(
      {
        error: 'Failed to fetch clusters',
        message: error instanceof Error ? error.message : 'Unknown error',
      },
      { status: 500 }
    );
  }
}

