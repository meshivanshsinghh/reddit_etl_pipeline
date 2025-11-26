import { NextResponse } from 'next/server';
import { getAlerts, getAlertCounts } from '@/lib/queries';

export const dynamic = 'force-dynamic';

export async function GET(request: Request) {
  try {
    const { searchParams } = new URL(request.url);
    const severity = searchParams.get('severity') || undefined;
    const resolved = searchParams.get('resolved') === 'true';
    const limit = parseInt(searchParams.get('limit') || '50');
    
    const [alerts, counts] = await Promise.all([
      getAlerts(severity, resolved, limit),
      getAlertCounts(),
    ]);
    
    return NextResponse.json({
      data: {
        alerts,
        counts,
      },
      timestamp: new Date().toISOString(),
    });
  } catch (error) {
    console.error('Error fetching alerts:', error);
    return NextResponse.json(
      {
        error: 'Failed to fetch alerts',
        message: error instanceof Error ? error.message : 'Unknown error',
      },
      { status: 500 }
    );
  }
}

