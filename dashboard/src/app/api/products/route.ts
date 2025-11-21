import { NextResponse } from 'next/server';
import { getProducts } from '@/lib/queries';

export const dynamic = 'force-dynamic';

export async function GET() {
  try {
    const products = await getProducts();
    
    return NextResponse.json({
      data: products,
      timestamp: new Date().toISOString(),
    });
  } catch (error) {
    console.error('Error fetching products:', error);
    return NextResponse.json(
      {
        error: 'Failed to fetch products',
        message: error instanceof Error ? error.message : 'Unknown error',
      },
      { status: 500 }
    );
  }
}

