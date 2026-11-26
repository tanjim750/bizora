import type { OrderSummary } from '@/lib/api/types';
import {
  apiError,
  json,
  type MockRequest,
  type MockResponse,
  queryOne,
  SESSION_COOKIE,
} from './http';
import { getDb } from './db';
import { stripOrderInternal } from './checkout';

function parseStrictInt(str: string): number | null {
  if (!/^\d+$/.test(str)) return null;
  const n = Number(str);
  return Number.isSafeInteger(n) ? n : null;
}

export function listOrders(req: MockRequest): MockResponse {
  const db = getDb();
  const sessionToken = req.cookies[SESSION_COOKIE];
  if (!sessionToken) {
    return apiError(401, 'UNAUTHENTICATED', 'Please sign in.');
  }

  const customerId = db.sessions.get(sessionToken);
  if (!customerId) {
    return apiError(401, 'UNAUTHENTICATED', 'Please sign in.');
  }

  const fields: Record<string, string[]> = {};
  let page = 1;
  const pageStr = queryOne(req.query, 'page');
  if (pageStr !== undefined) {
    const p = parseStrictInt(pageStr);
    if (p === null || p < 1) {
      fields.page = ['Must be an integer ≥ 1.'];
    } else {
      page = p;
    }
  }

  let pageSize = 10;
  const pageSizeStr = queryOne(req.query, 'pageSize');
  if (pageSizeStr !== undefined) {
    const ps = parseStrictInt(pageSizeStr);
    if (ps === null || ps < 1 || ps > 50) {
      fields.pageSize = ['Must be between 1 and 50.'];
    } else {
      pageSize = ps;
    }
  }

  if (Object.keys(fields).length > 0) {
    return apiError(400, 'VALIDATION_FAILED', 'Validation failed.', fields);
  }

  const customerOrders = db.orders
    .filter((o) => o.customerId === customerId)
    .sort((a, b) => new Date(b.placedAt).getTime() - new Date(a.placedAt).getTime());
  const totalItems = customerOrders.length;
  const totalPages = Math.ceil(totalItems / pageSize);

  const start = (page - 1) * pageSize;
  const pagedOrders = customerOrders.slice(start, start + pageSize);

  const items: OrderSummary[] = pagedOrders.map((order) => {
    const itemCount = order.lines.reduce((sum, line) => sum + line.quantity, 0);
    const previewImages = order.lines
      .map((line) => line.image)
      .filter((img): img is NonNullable<typeof img> => img !== null)
      .slice(0, 3);

    return {
      number: order.number,
      status: order.status,
      placedAt: order.placedAt,
      itemCount,
      total: order.total,
      previewImages,
    };
  });

  return json(200, {
    items,
    page,
    pageSize,
    totalItems,
    totalPages,
  });
}

export function getOrder(req: MockRequest, orderNumber: string): MockResponse {
  const db = getDb();
  const order = db.orders.find((o) => o.number === orderNumber);
  if (!order) {
    return apiError(404, 'NOT_FOUND', 'Order not found.');
  }

  const sessionToken = req.cookies[SESSION_COOKIE];
  const customerId = sessionToken ? (db.sessions.get(sessionToken) ?? null) : null;
  const token = queryOne(req.query, 'token');

  const isOwner = customerId !== null && order.customerId === customerId;
  const hasValidToken = token !== undefined && token === order.confirmationToken;

  if (!isOwner && !hasValidToken) {
    return apiError(404, 'NOT_FOUND', 'Order not found.');
  }

  return json(200, stripOrderInternal(order));
}
