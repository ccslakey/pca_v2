import { describe, it, expect } from 'vitest';
import type { CaptureResult } from 'posthog-js';
import { scrubAnalyticsEvent } from '../analytics';

describe('scrubAnalyticsEvent', () => {
  it('allowlists URL params and reduces referrers to their origin', () => {
    const event = {
      uuid: '1',
      event: '$pageview',
      properties: {
        $current_url: 'https://x.app/?compare=ruthba01&email=a%40b.com',
        $referrer: 'https://mail.google.com/mail/u/0/#inbox/123',
        $referring_domain: 'mail.google.com',
      },
      $set_once: {
        $initial_current_url: 'https://x.app/?fbclid=abc',
        $initial_referrer: '$direct',
      },
    } as CaptureResult;
    const out = scrubAnalyticsEvent(event)!;
    expect(out.properties.$current_url).toBe('https://x.app/?compare=ruthba01');
    expect(out.properties.$referrer).toBe('https://mail.google.com');
    expect(out.properties.$referring_domain).toBe('mail.google.com');
    expect(out.$set_once!.$initial_current_url).toBe('https://x.app/');
    expect(out.$set_once!.$initial_referrer).toBe('$direct');
  });
});
