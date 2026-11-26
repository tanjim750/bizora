import { createApi } from './create-api';
import { createHttpTransport } from './transport-http';

export const browserApi = createApi(createHttpTransport('/api/store'));
