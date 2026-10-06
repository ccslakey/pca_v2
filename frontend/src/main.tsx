import { StrictMode } from 'react';
import * as Sentry from '@sentry/react';
import { createRoot } from 'react-dom/client';
import './globals.scss';
import { App } from './App';
import { ThemeProvider } from './themes/ThemeContext';
import { initSentry } from './observability';
import { initAnalytics } from './analytics';

initSentry();
initAnalytics();

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <Sentry.ErrorBoundary fallback={<p style={{ padding: 24 }}>Something went wrong. Try reloading the page.</p>}>
      <ThemeProvider>
        <App />
      </ThemeProvider>
    </Sentry.ErrorBoundary>
  </StrictMode>,
);
