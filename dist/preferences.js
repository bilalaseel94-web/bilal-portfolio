'use strict';

// Apply appearance before paint, and distinguish a language change from a fresh visit.
(() => {
  const themeKey = 'bilal-portfolio-theme';
  window.applyPortfolioTheme = theme => {
    const chosen = theme === 'light' ? 'light' : 'dark';
    document.documentElement.dataset.theme = chosen;
    document.querySelector('meta[name="theme-color"]').content = chosen === 'light' ? '#f6f7f3' : '#0b1017';
  };
  let savedTheme = 'dark';
  try { savedTheme = localStorage.getItem(themeKey) || 'dark'; } catch (_) {}
  window.applyPortfolioTheme(savedTheme);

  if ('scrollRestoration' in history) history.scrollRestoration = 'manual';
  let languageEntry = null;
  try {
    const stored = JSON.parse(sessionStorage.getItem('bilal-language-entry') || 'null');
    sessionStorage.removeItem('bilal-language-entry');
    const navigation = performance.getEntriesByType('navigation')[0];
    if (stored && stored.path === location.pathname && Date.now() - stored.created < 30000 && navigation && navigation.type === 'navigate') {
      languageEntry = stored;
    }
  } catch (_) {}
  window.portfolioLanguageEntry = languageEntry;

  function startAtTop() {
    if (location.hash) history.replaceState(history.state, '', location.pathname + location.search);
    scrollTo({top: 0, left: 0, behavior: 'instant'});
  }
  // The deferred script restores only an intentional, one-time language transition.
  if (!languageEntry) startAtTop();
  addEventListener('pageshow', event => {
    if (!window.portfolioLanguageEntry || event.persisted) startAtTop();
  });
})();
