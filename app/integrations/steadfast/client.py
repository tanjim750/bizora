"""Small, injectable HTTP client matching the Steadfast PHP package endpoints."""
import json
import math
import time
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener


class SteadfastError(Exception):
    def __init__(self, message, *, status=None, errors=None, response=None):
        super().__init__(message)
        self.status = status
        self.errors = errors
        self.response = response


class SteadfastNetworkError(SteadfastError):
    pass


class _NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, request, fp, code, msg, headers, newurl):
        return None


class SteadfastClient:
    DEFAULT_BASE_URL = 'https://portal.packzy.com/api/v1'

    def __init__(self, api_key, secret_key, *, base_url=DEFAULT_BASE_URL, timeout=10.0,
                 retry_count=2, transport=None, sleep=time.sleep):
        if not isinstance(api_key, str) or not api_key.strip() or not isinstance(secret_key, str) or not secret_key.strip():
            raise ValueError('Steadfast API key and secret key are required.')
        parsed = urlsplit(base_url)
        if parsed.scheme not in {'http', 'https'} or not parsed.netloc or parsed.username or parsed.password or parsed.query or parsed.fragment:
            raise ValueError('Steadfast base URL must be an HTTP(S) URL without credentials or query.')
        if not isinstance(timeout, (int, float)) or not math.isfinite(timeout) or timeout <= 0:
            raise ValueError('Steadfast timeout must be positive.')
        if isinstance(retry_count, bool) or not isinstance(retry_count, int) or retry_count < 0:
            raise ValueError('Steadfast retry count must be a nonnegative integer.')
        self.api_key, self.secret_key = api_key, secret_key
        self.base_url, self.timeout, self.retry_count = base_url.rstrip('/'), timeout, retry_count
        self.transport = transport or build_opener(_NoRedirect()).open
        self.sleep = sleep

    def request(self, method, endpoint, *, payload=None, query=None, authenticated=True, retry=None):
        if not isinstance(endpoint, str) or not endpoint.strip() or endpoint.startswith('//') or '://' in endpoint:
            raise ValueError('Steadfast endpoint must be relative to the configured base URL.')
        endpoint = endpoint.lstrip('/')
        if endpoint.startswith('/') or '?' in endpoint or '#' in endpoint or '\\' in endpoint or '..' in endpoint.split('/'):
            raise ValueError('Invalid Steadfast endpoint.')
        url = f'{self.base_url}/{endpoint}'
        if query:
            url += '?' + urlencode(query)
        headers = {'Accept': 'application/json'}
        if authenticated:
            headers.update({'Api-Key': self.api_key, 'Secret-Key': self.secret_key})
        data = None
        if payload is not None:
            data = json.dumps(payload, separators=(',', ':')).encode('utf-8')
            headers['Content-Type'] = 'application/json'
        request = Request(url, data=data, headers=headers, method=method)
        attempts = self.retry_count + 1 if (method == 'GET' if retry is None else retry) else 1
        for attempt in range(attempts):
            try:
                response = self.transport(request, timeout=self.timeout)
                with response:
                    status, body, response_headers = response.status, response.read(), response.headers
            except HTTPError as exc:
                status, body, response_headers = exc.code, exc.read(), exc.headers
            except (URLError, TimeoutError, OSError) as exc:
                if attempt + 1 < attempts:
                    self.sleep(min(2 ** attempt, 5))
                    continue
                raise SteadfastNetworkError('Steadfast network request failed.') from exc
            if (status == 429 or status >= 500) and attempt + 1 < attempts:
                self.sleep(self._retry_delay(response_headers, attempt))
                continue
            try:
                result = json.loads(body) if body.strip() else {}
            except (ValueError, UnicodeDecodeError) as exc:
                raise SteadfastError('Steadfast returned malformed JSON.', status=status) from exc
            if not isinstance(result, (dict, list)):
                raise SteadfastError('Steadfast returned an unusable JSON response.', status=status)
            if not 200 <= status < 300:
                message = next((result[k] for k in ('message', 'error', 'detail') if isinstance(result, dict) and isinstance(result.get(k), str)), None)
                raise SteadfastError(message or f'Steadfast request failed with HTTP {status}.', status=status,
                                     errors=result.get('errors', result.get('validation_errors')) if isinstance(result, dict) else None,
                                     response=result)
            return result
        raise SteadfastNetworkError('Steadfast request failed after retries.')

    @staticmethod
    def _retry_delay(headers, attempt):
        value = headers.get('Retry-After') if headers else None
        if value:
            try:
                return min(5.0, max(0.0, float(value)))
            except ValueError:
                try:
                    return min(5.0, max(0.0, (parsedate_to_datetime(value) - datetime.now(timezone.utc)).total_seconds()))
                except (TypeError, ValueError, OverflowError):
                    pass
        return min(2 ** attempt, 5)

    def get(self, endpoint, *, query=None, authenticated=True):
        return self.request('GET', endpoint, query=query, authenticated=authenticated)

    def post(self, endpoint, payload, *, retry=False):
        return self.request('POST', endpoint, payload=payload, retry=retry)

    def ping(self):
        return self.get('/ping', authenticated=False)
