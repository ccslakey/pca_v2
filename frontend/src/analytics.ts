import type { CaptureResult, PostHog } from 'posthog-js';
import { scrubUrl } from './observability';

// Product analytics. Event names and properties are documented in
// ANALYTICS.md — update it when adding an event.
//
// Privacy: cookieless mode (PostHog derives a daily-rotating hash server-side,
// nothing is stored on the device), no person profiles, no autocapture or
// session replay. URLs are reduced to allowlisted query params and referrers
// to their origin. Client IPs are discarded by the project setting.

const URL_PROPS = ['$current_url', '$initial_current_url'];
const REFERRER_PROPS = ['$referrer', '$initial_referrer'];

function originOnly(url: string): string {
  try {
    return new URL(url).origin;
  } catch {
    return url; // '$direct' and other non-URL markers
  }
}

export function scrubAnalyticsEvent(event: CaptureResult | null): CaptureResult | null {
  if (!event) return event;
  for (const bag of [event.properties, event.$set, event.$set_once]) {
    if (!bag) continue;
    for (const key of URL_PROPS) {
      if (typeof bag[key] === 'string') bag[key] = scrubUrl(bag[key]);
    }
    for (const key of REFERRER_PROPS) {
      if (typeof bag[key] === 'string') bag[key] = originOnly(bag[key]);
    }
  }
  return event;
}

// posthog-js is ~100 kB gzipped, so it loads in its own chunk after first
// render. Events fired before it arrives are queued, then flushed.
let client: PostHog | null = null;
let queue: Array<[string, Record<string, unknown> | undefined]> | null = null;

export function initAnalytics(): void {
  const key = import.meta.env.VITE_POSTHOG_KEY;
  if (!key) return;
  queue = [];
  import('posthog-js').then(({ default: posthog }) => {
    posthog.init(key, {
      api_host: import.meta.env.VITE_POSTHOG_HOST || 'https://us.i.posthog.com',
      cookieless_mode: 'always',
      person_profiles: 'never',
      capture_pageview: 'history_change',
      capture_pageleave: true,
      autocapture: false,
      disable_session_recording: true,
      disable_surveys: true,
      capture_exceptions: false, // Sentry owns errors
      before_send: scrubAnalyticsEvent,
    });
    client = posthog;
    for (const [event, properties] of queue ?? []) posthog.capture(event, properties);
    queue = null;
  });
}

export function track(event: string, properties?: Record<string, unknown>): void {
  if (client) client.capture(event, properties);
  else if (queue && queue.length < 100) queue.push([event, properties]);
}
