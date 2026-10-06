"""Server-side product analytics (PostHog).

Only for things the browser can't see, e.g. narrative generation cost and
latency. Events are anonymous system events: a fixed distinct_id, no person
profile, and never any prompt/output text. No-op unless POSTHOG_API_KEY is set.
"""

import atexit
import os
from typing import Any

from posthog import Posthog

_DISTINCT_ID = 'pca-backend'

_key = os.environ.get('POSTHOG_API_KEY', '')
client = Posthog(
    _key or 'disabled',
    host=os.environ.get('POSTHOG_HOST', 'https://us.i.posthog.com'),
    disabled=not _key,
    enable_exception_autocapture=False,  # Sentry owns errors
    privacy_mode=True,
)
atexit.register(client.shutdown)


def capture(event: str, properties: dict[str, Any] | None = None) -> None:
    client.capture(
        event,
        distinct_id=_DISTINCT_ID,
        properties={**(properties or {}), '$process_person_profile': False},
    )
