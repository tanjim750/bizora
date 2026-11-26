import 'server-only';
import { createApi } from './create-api';
import { createHttpTransport } from './transport-http';
import { mockTransport } from './transport-mock';

export const serverApi = createApi(
  process.env.API_BASE_URL
    ? createHttpTransport(process.env.API_BASE_URL, { revalidate: 60 })
    : mockTransport,
);

export const isMockMode = !process.env.API_BASE_URL;
