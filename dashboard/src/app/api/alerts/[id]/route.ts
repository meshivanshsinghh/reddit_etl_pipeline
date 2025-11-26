import { NextResponse } from 'next/server';
import { resolveAlert } from '@/lib/queries';

export const dynamic = 'force-dynamic';

export async function PATCH(
  request: Request,
  { params }: { params: Promise<{ id: string }> }
) {
  try {
    const { id } = await params;
    const alertId = parseInt(id);
    
    if (isNaN(alertId)) {
      return NextResponse.json(
        { error: 'Invalid alert ID' },
        { status: 400 }
      );
    }
    
    const body = await request.json();
    
    if (body.resolved === true) {
      const success = await resolveAlert(alertId);
      
      if (success) {
        return NextResponse.json({
          data: { id: alertId, resolved: true },
          timestamp: new Date().toISOString(),
        });
      } else {
        return NextResponse.json(
          { error: 'Alert not found' },
          { status: 404 }
        );
      }
    }
    
    return NextResponse.json(
      { error: 'Invalid request body' },
      { status: 400 }
    );
  } catch (error) {
    console.error('Error updating alert:', error);
    return NextResponse.json(
      {
        error: 'Failed to update alert',
        message: error instanceof Error ? error.message : 'Unknown error',
      },
      { status: 500 }
    );
  }
}

