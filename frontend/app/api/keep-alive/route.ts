import { NextResponse } from 'next/server';

export async function GET() {
  try {
    // Replace this with your explicit Hugging Face Space URL string
    const hfBackendUrl = 'https://chandann-23-astra-backend.hf.space/docs';
    
    const response = await fetch(hfBackendUrl, {
      method: 'GET',
      headers: {
        'Cache-Control': 'no-cache'
      }
    });
    
    return NextResponse.json({ 
      status: 'success', 
      message: 'Astra engine pinged successfully',
      backendStatus: response.status 
    });
  } catch (error: any) {
    return NextResponse.json({ 
      status: 'error', 
      message: error.message || 'Failed to awake space' 
    }, { status: 500 });
  }
}
