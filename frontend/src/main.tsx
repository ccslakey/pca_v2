import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import './globals.scss';
import { App } from './App';
import { ThemeProvider } from './themes/ThemeContext';

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <ThemeProvider>
      <App />
    </ThemeProvider>
  </StrictMode>,
);
