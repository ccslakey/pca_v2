"""Sentry setup and PII scrubbing.

The app has no accounts, so the only personal data that can leak into error
reports is request metadata: client IP (incl. X-Forwarded-For from Railway's
proxy), cookies, headers, bodies, and query params someone else appended to a
URL (email trackers, ad click IDs). Strip all of it before events leave the box.
"""

import os
from urllib.parse import parse_qsl, urlencode

# Query params we put in URLs ourselves, minus free-text ones (`search`, `q`).
# Everything else is dropped. Keep in sync with frontend/src/observability.ts.
ALLOWED_QUERY_PARAMS = {
    'compare', 'utm_source', 'utm_medium', 'utm_campaign',
    'pos', 'min_war', 'era_start', 'era_end', 'sort', 'order', 'page', 'page_size', 'role', 'outcome',
}


def scrub_query_string(qs: str) -> str:
    return urlencode([(k, v) for k, v in parse_qsl(qs, keep_blank_values=True) if k in ALLOWED_QUERY_PARAMS])


def scrub_event(event, hint=None):
    request = event.get('request')
    if request:
        for key in ('headers', 'cookies', 'data', 'env'):
            request.pop(key, None)
        qs = request.get('query_string')
        if isinstance(qs, str):
            request['query_string'] = scrub_query_string(qs)
        elif qs:
            request.pop('query_string')
    event.pop('user', None)
    return event


def init_sentry() -> None:
    dsn = os.environ.get('SENTRY_DSN', '')
    if not dsn:
        return
    import sentry_sdk

    sentry_sdk.init(
        dsn=dsn,
        environment=os.environ.get('SENTRY_ENVIRONMENT', 'production'),
        release=os.environ.get('RAILWAY_GIT_COMMIT_SHA') or None,
        send_default_pii=False,
        max_request_body_size='never',
        traces_sample_rate=float(os.environ.get('SENTRY_TRACES_SAMPLE_RATE', '0.1')),
        before_send=scrub_event,
        before_send_transaction=scrub_event,
    )
