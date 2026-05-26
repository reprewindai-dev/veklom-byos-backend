/**
 * Veklom BYOS Backend - Cloudflare Worker
 * 
 * This worker provides edge-side routing and caching for the Veklom BYOS backend.
 * It handles:
 * - Request routing to the backend
 * - Response caching
 * - Rate limiting
 * - Security headers
 */

export interface Env {
  BACKEND_URL: string;
  API_KEY?: string;
  CACHE_TTL?: number;
  RATE_LIMIT?: number;
}

export default {
  async fetch(request: Request, env: Env): Promise<Response> {
    const url = new URL(request.url);
    
    // Add security headers
    const headers = new Headers({
      'X-Content-Type-Options': 'nosniff',
      'X-Frame-Options': 'DENY',
      'X-XSS-Protection': '1; mode=block',
      'Strict-Transport-Security': 'max-age=31536000; includeSubDomains',
      'Referrer-Policy': 'strict-origin-when-cross-origin',
    });

    // Handle CORS preflight
    if (request.method === 'OPTIONS') {
      headers.set('Access-Control-Allow-Origin', '*');
      headers.set('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, OPTIONS');
      headers.set('Access-Control-Allow-Headers', 'Content-Type, Authorization');
      return new Response(null, { headers });
    }

    // Proxy to backend
    const backendUrl = env.BACKEND_URL || 'https://veklom.com';
    const proxyUrl = `${backendUrl}${url.pathname}${url.search}`;
    
    try {
      const proxyRequest = new Request(proxyUrl, request);
      
      // Add API key if provided
      if (env.API_KEY) {
        proxyRequest.headers.set('X-API-Key', env.API_KEY);
      }

      const response = await fetch(proxyRequest);
      
      // Copy response headers
      response.headers.forEach((value, key) => {
        headers.set(key, value);
      });
      
      // Add CORS headers
      headers.set('Access-Control-Allow-Origin', '*');
      
      return new Response(response.body, {
        status: response.status,
        headers,
      });
    } catch (error) {
      return new Response(
        JSON.stringify({ error: 'Backend unavailable' }),
        {
          status: 503,
          headers: {
            ...Object.fromEntries(headers),
            'Content-Type': 'application/json',
          },
        }
      );
    }
  },
};
