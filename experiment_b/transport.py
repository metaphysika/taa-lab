"""Explicitly approved HTTPS route only. No retries, redirects, SDKs or key files."""
import http.client
import json
import os
import time
from urllib.parse import urlsplit

from experiment_b.host import Stop


class HTTPS:
    def __init__(self, provider, deadline=None, retain=None):
        self.provider = provider
        self.deadline = deadline
        self.retain = retain or (lambda *args: None)

    def __call__(self, body):
        provider = self.provider
        remaining = self.deadline - time.monotonic() if self.deadline is not None else provider['timeout_seconds']
        if remaining <= 0:
            raise Stop('approved_runtime_bound')
        key = os.environ.get(provider['key_env'])
        if not key:
            raise Stop('approved_key_unavailable')
        url = urlsplit(provider['endpoint'])
        connection = http.client.HTTPSConnection(url.hostname, url.port,
                                                 timeout=min(provider['timeout_seconds'], remaining))
        headers = dict(provider.get('headers', {}))
        headers.update({'Content-Type': 'application/json',
                        provider['auth_header']: provider.get('auth_prefix', '') + key})
        try:
            connection.request('POST', url.path, body=json.dumps(body).encode(), headers=headers)
            response = connection.getresponse()
            raw = response.read(16 * 1024 * 1024 + 1)
            self.retain('http_receipt', dict(status=response.status,
                                            request_id=response.getheader('x-request-id') or response.getheader('request-id')))
            if len(raw) > 16 * 1024 * 1024:
                raise Stop('response_size_guard')
            if response.status != 200:
                self.retain('http_error', dict(status=response.status, body=raw.decode('utf-8', errors='replace')))
                raise Stop('http_status_' + str(response.status))
            return json.loads(raw)
        finally:
            connection.close()
