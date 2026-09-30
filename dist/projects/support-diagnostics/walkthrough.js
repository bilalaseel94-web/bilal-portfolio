'use strict';

// These panels contain recorded evidence. Selecting one never runs a network check.
const phaseTabs = [...document.querySelectorAll('[data-phase-tab]')];
const phasePanels = [...document.querySelectorAll('[data-phase-panel]')];
const phaseGroup = document.querySelector('[data-phase-tabs]');

if (phaseGroup && phaseTabs.length === phasePanels.length && phaseTabs.length) {
  phaseGroup.setAttribute('role', 'tablist');
  phaseTabs.forEach(tab => tab.setAttribute('role', 'tab'));
  phasePanels.forEach(panel => {
    panel.setAttribute('role', 'tabpanel');
    panel.tabIndex = 0;
  });
  function activatePhase(tab, focus = false) {
    phaseTabs.forEach(item => {
      const active = item === tab;
      item.setAttribute('aria-selected', String(active));
      item.tabIndex = active ? 0 : -1;
    });
    phasePanels.forEach(panel => { panel.hidden = panel.id !== tab.getAttribute('aria-controls'); });
    if (focus) tab.focus();
  }
  phaseTabs.forEach((tab, index) => {
    tab.addEventListener('click', () => activatePhase(tab));
    tab.addEventListener('keydown', event => {
      const next = {ArrowRight: (index + 1) % phaseTabs.length,
        ArrowLeft: (index - 1 + phaseTabs.length) % phaseTabs.length,
        Home: 0, End: phaseTabs.length - 1}[event.key];
      if (next !== undefined) {
        event.preventDefault();
        activatePhase(phaseTabs[next], true);
      }
    });
  });
  activatePhase(phaseTabs.find(tab => tab.dataset.phaseTab === 'application-fault') || phaseTabs[0]);
  document.documentElement.classList.add('case-enhanced');
}

const caseTheme = document.querySelector('[data-case-theme]');
function refreshThemeLabel() {
  const light = document.documentElement.dataset.theme === 'light';
  caseTheme.setAttribute('aria-label', light ? 'Switch to dark theme' : 'Switch to light theme');
  caseTheme.querySelector('[data-theme-label]').textContent = light ? 'Dark' : 'Light';
}
if (caseTheme && window.applyPortfolioTheme) {
  refreshThemeLabel();
  caseTheme.hidden = false;
  caseTheme.addEventListener('click', () => {
    const next = document.documentElement.dataset.theme === 'light' ? 'dark' : 'light';
    window.applyPortfolioTheme(next);
    try { localStorage.setItem('bilal-portfolio-theme', next); } catch (_) {}
    refreshThemeLabel();
  });
}

const copyStatus = document.querySelector('#command-copy-status');
document.querySelectorAll('[data-copy-command]').forEach(button => {
  button.hidden = false;
  button.addEventListener('click', async () => {
    const code = document.getElementById(button.dataset.copyCommand);
    if (!code) return;
    try {
      await navigator.clipboard.writeText(code.textContent);
      button.textContent = 'Copied';
      copyStatus.textContent = 'Command copied. This action does not run it.';
    } catch (_) {
      copyStatus.textContent = 'Copy is unavailable. Select the command text to copy it.';
    }
  });
});
