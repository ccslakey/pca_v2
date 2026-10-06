import { describe, it, expect } from 'vitest';
import { scrubBreadcrumb, scrubEvent, scrubUrl } from '../observability';

describe('scrubUrl', () => {
  it('keeps allowlisted params and drops the rest', () => {
    expect(scrubUrl('https://x.app/?compare=ruthba01&email=a%40b.com&fbclid=z&utm_source=reddit'))
      .toBe('https://x.app/?compare=ruthba01&utm_source=reddit');
  });

  it('drops free-text search params from API URLs', () => {
    expect(scrubUrl('/api/players/?search=jane+doe&page_size=15')).toBe('/api/players/?page_size=15');
  });

  it('removes the query entirely when nothing is allowed, and drops the hash', () => {
    expect(scrubUrl('/player/ruthba01?token=abc#section')).toBe('/player/ruthba01');
  });

  it('leaves URLs without a query alone', () => {
    expect(scrubUrl('/browse')).toBe('/browse');
  });
});

describe('scrubEvent', () => {
  it('strips referer, cookies, and user but keeps the user agent', () => {
    const out = scrubEvent({
      request: {
        url: 'https://x.app/?compare=a&gclid=z',
        headers: { Referer: 'https://mail.google.com/mail/u/0/#inbox/123', 'User-Agent': 'UA' },
        cookies: { sessionid: 'abc' },
      },
      user: { ip_address: '1.2.3.4' },
    });
    expect(out.request).toEqual({ url: 'https://x.app/?compare=a', headers: { 'User-Agent': 'UA' } });
    expect(out.user).toBeUndefined();
  });
});

describe('scrubBreadcrumb', () => {
  it('scrubs fetch and navigation URLs', () => {
    const crumb = scrubBreadcrumb({ data: { url: '/api/players/methodology_search/?q=steroids', from: '/?x=1', to: '/browse?pos=C' } });
    expect(crumb.data).toEqual({ url: '/api/players/methodology_search/', from: '/', to: '/browse?pos=C' });
  });
});
