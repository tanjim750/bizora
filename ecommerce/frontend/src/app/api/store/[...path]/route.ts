import { type NextRequest } from 'next/server';
import { handleMockRequest } from '@/mocks/server/router';
import { apiError, type MockRequest } from '@/mocks/server/http';

export const dynamic = 'force-dynamic';

async function handle(
  request: NextRequest,
  { params }: { params: Promise<{ path: string[] }> },
): Promise<Response> {
  if (process.env.API_BASE_URL) {
    const errRes = apiError(404, 'NOT_FOUND', 'Route not found.');
    return new Response(JSON.stringify(errRes.body), {
      status: 404,
      headers: errRes.headers,
    });
  }

  const { path: pathSegments } = await params;
  const path = '/' + pathSegments.join('/');

  const query: Record<string, string | string[]> = {};
  for (const key of request.nextUrl.searchParams.keys()) {
    const all = request.nextUrl.searchParams.getAll(key);
    query[key] = all.length > 1 ? all : (all[0] ?? '');
  }

  const headers: Record<string, string> = {};
  request.headers.forEach((val, key) => {
    headers[key.toLowerCase()] = val;
  });

  const cookies: Record<string, string> = {};
  for (const c of request.cookies.getAll()) {
    cookies[c.name] = c.value;
  }

  let body: unknown;
  const text = await request.text();
  if (!text || text.length === 0) {
    body = undefined;
  } else {
    try {
      body = JSON.parse(text);
    } catch {
      const errRes = apiError(400, 'VALIDATION_FAILED', 'Body is not valid JSON.');
      return new Response(JSON.stringify(errRes.body), {
        status: 400,
        headers: errRes.headers,
      });
    }
  }

  const latency = Number(process.env.MOCK_LATENCY_MS ?? 250);
  if (latency > 0) {
    await new Promise((resolve) => setTimeout(resolve, latency));
  }

  const mockReq: MockRequest = {
    method: request.method as 'GET' | 'POST' | 'PATCH' | 'DELETE',
    path,
    query,
    body,
    headers,
    cookies,
  };

  const mockRes = await handleMockRequest(mockReq);

  const resHeaders = new Headers(mockRes.headers);
  if (mockRes.setCookies) {
    for (const sc of mockRes.setCookies) {
      resHeaders.append('set-cookie', sc);
    }
  }

  return new Response(mockRes.status === 204 ? null : JSON.stringify(mockRes.body), {
    status: mockRes.status,
    headers: resHeaders,
  });
}

export const GET = handle;
export const POST = handle;
export const PATCH = handle;
export const DELETE = handle;
