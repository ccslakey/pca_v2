import * as Sentry from '@sentry/react';

// Query params we put in URLs ourselves, minus free-text ones (`search`, `q`).
// Everything else (email trackers, ad click IDs, tokens) is dropped before
// anything leaves the browser. Keep in sync with pca_backend/observability.py.
const ALLOWED_QUERY_PARAMS = new Set([
  'compare', 'utm_source', 'utm_medium', 'utm_campaign',
  'pos', 'min_war', 'era_start', 'era_end', 'sort', 'order', 'page', 'page_size', 'role', 'outcome',
]);

export function scrubUrl(url: string): string {
  const qIndex = url.indexOf('?');
  if (qIndex === -1) return url;
  const hashIndex = url.indexOf('#', qIndex);
  const base = url.slice(0, qIndex);
  const query = url.slice(qIndex + 1, hashIndex === -1 ? undefined : hashIndex);
  const kept = new URLSearchParams();
  for (const [k, v] of new URLSearchParams(query)) {
    if (ALLOWED_QUERY_PARAMS.has(k)) kept.append(k, v);
  }
  const qs = kept.toString();
  return qs ? `${base}?${qs}` : base;
}

export function scrubEvent<T extends Sentry.Event>(event: T): T {
  if (event.request) {
    if (event.request.url) event.request.url = scrubUrl(event.request.url);
    // Referer is a full URL from another site; User-Agent stays so Sentry can
    // derive browser/OS.
    if (event.request.headers) {
      const ua = event.request.headers['User-Agent'];
      event.request.headers = ua ? { 'User-Agent': ua } : {};
    }
    delete event.request.cookies;
    delete event.request.query_string;
  }
  delete event.user;
  return event;
}

export function scrubBreadcrumb(crumb: Sentry.Breadcrumb): Sentry.Breadcrumb {
  const data = crumb.data;
  if (data) {
    for (const key of ['url', 'from', 'to']) {
      if (typeof data[key] === 'string') data[key] = scrubUrl(data[key]);
    }
  }
  return crumb;
}

export function initSentry(): void {
  const dsn = import.meta.env.VITE_SENTRY_DSN;
  if (!dsn) return;
  Sentry.init({
    dsn,
    environment: import.meta.env.VITE_SENTRY_ENVIRONMENT || 'production',
    // v11 collects everything unless told otherwise; opt out explicitly.
    // scrubEvent/scrubBreadcrumb below are a backstop for anything this misses.
    dataCollection: {
      userInfo: false,
      cookies: false,
      httpHeaders: { request: { allow: ['User-Agent'] }, response: false },
      httpBodies: [],
      urlQueryParams: { allow: [...ALLOWED_QUERY_PARAMS] },
      genAI: { inputs: false, outputs: false },
      stackFrameVariables: false,
    },
    integrations: [Sentry.browserTracingIntegration()],
    tracesSampleRate: 0.1,
    // Same-origin API calls carry trace headers so frontend and Django spans join up.
    tracePropagationTargets: [/^\/api\//],
    beforeSend: scrubEvent,
    beforeSendTransaction: scrubEvent,
    beforeBreadcrumb: scrubBreadcrumb,
  });
}
