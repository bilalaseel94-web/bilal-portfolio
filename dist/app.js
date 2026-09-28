'use strict';

// Keep keyboard focus and panel visibility local to each tab group.
document.querySelectorAll('[data-tabs]').forEach(group => {
  const tabs = [...group.querySelectorAll('[role="tab"]')];
  const panels = [...group.querySelectorAll('[role="tabpanel"]')];
  function selectTab(tab, moveFocus = false) {
    tabs.forEach(item => {
      const selected = item === tab;
      item.setAttribute('aria-selected', String(selected));
      item.tabIndex = selected ? 0 : -1;
    });
    panels.forEach(panel => { panel.hidden = panel.id !== tab.getAttribute('aria-controls'); });
    if (moveFocus) tab.focus();
  }
  tabs.forEach((tab, index) => {
    tab.addEventListener('click', () => selectTab(tab));
    tab.addEventListener('keydown', event => {
      if (event.altKey || event.ctrlKey || event.metaKey) return;
      const horizontal = document.documentElement.dir === 'rtl' ? -1 : 1;
      const next = {ArrowRight:(index + horizontal + tabs.length) % tabs.length, ArrowDown:(index + 1) % tabs.length,
        ArrowLeft:(index - horizontal + tabs.length) % tabs.length, ArrowUp:(index - 1 + tabs.length) % tabs.length,
        Home:0, End:tabs.length - 1}[event.key];
      if (next !== undefined) { event.preventDefault(); selectTab(tabs[next], true); }
    });
  });
});

const progress = document.querySelector('.reading-progress');
const header = document.querySelector('.site-header');
let framePending = false;
function updateScroll() {
  const range = document.documentElement.scrollHeight - innerHeight;
  progress.style.transform = `scaleX(${range > 0 ? Math.min(1, Math.max(0, scrollY / range)) : 0})`;
  header.classList.toggle('scrolled', scrollY > 20);
  framePending = false;
}
addEventListener('scroll', () => {
  if (!framePending) { framePending = true; requestAnimationFrame(updateScroll); }
}, {passive:true});
addEventListener('resize', updateScroll);
updateScroll();

const reduceMotion = matchMedia('(prefers-reduced-motion: reduce)');
if ('IntersectionObserver' in window) {
  const navLinks = [...document.querySelectorAll('.main-navigation a')];
  const sectionObserver = new IntersectionObserver(entries => {
    entries.forEach(entry => {
      if (!entry.isIntersecting) return;
      navLinks.forEach(link => {
        if (link.getAttribute('href') === '#' + entry.target.id) link.setAttribute('aria-current', 'location');
        else link.removeAttribute('aria-current');
      });
    });
  }, {rootMargin:'-15% 0px -50% 0px'});
  document.querySelectorAll('main section[id]').forEach(section => sectionObserver.observe(section));
  if (!reduceMotion.matches) {
    document.body.classList.add('motion-enabled');
    const revealObserver = new IntersectionObserver(entries => {
      entries.forEach(entry => {
        if (entry.isIntersecting) { entry.target.classList.remove('waiting'); revealObserver.unobserve(entry.target); }
      });
    }, {threshold:0.05});
    document.querySelectorAll('.reveal').forEach(element => {
      if (element.getBoundingClientRect().top > innerHeight) element.classList.add('waiting');
      revealObserver.observe(element);
    });
    reduceMotion.addEventListener('change', event => {
      if (event.matches) document.querySelectorAll('.waiting').forEach(element => element.classList.remove('waiting'));
    });
  }
}

// Product logos and cards share one disclosure state, including across skill tabs.
const productTriggers = [...document.querySelectorAll('[data-product-trigger]')];
const productsTab = document.getElementById('skill-products');
function setProductOpen(product, open) {
  document.getElementById(product + '-experience').hidden = !open;
  productTriggers.filter(button => button.dataset.productTrigger === product).forEach(button => {
    button.setAttribute('aria-expanded', String(open));
    const label = button.querySelector('.brand-action-label, .product-action-label');
    label.firstChild.textContent = (open ? button.dataset.labelOpen : button.dataset.labelClosed) + ' ';
    label.querySelector('span').textContent = open ? '−' : '+';
    if (button.classList.contains('brand-action')) button.setAttribute('aria-label', open ? button.dataset.ariaOpen : button.dataset.ariaClosed);
  });
}
productTriggers.forEach(trigger => {
  trigger.addEventListener('click', () => {
    const product = trigger.dataset.productTrigger;
    const panel = document.getElementById(product + '-experience');
    const open = panel.hidden || productsTab.getAttribute('aria-selected') !== 'true';
    productsTab.click();
    new Set(productTriggers.map(button => button.dataset.productTrigger)).forEach(name => setProductOpen(name, name === product && open));
    if (trigger.classList.contains('brand-action')) {
      const control = document.getElementById(product + '-toggle');
      control.focus({preventScroll:true});
      control.scrollIntoView({block:'center', behavior:reduceMotion.matches ? 'auto' : 'smooth'});
    }
    updateScroll();
  });
});

document.querySelectorAll('[data-skill-target]').forEach(trigger => {
  trigger.addEventListener('click', () => {
    const tab = document.getElementById(trigger.dataset.skillTarget);
    tab.click();
    const panel = document.getElementById(tab.getAttribute('aria-controls'));
    panel.focus({preventScroll:true});
    panel.scrollIntoView({block:'center', behavior:reduceMotion.matches ? 'auto' : 'smooth'});
    updateScroll();
  });
});


// Each network skill reveals one short, on-page account of its practical use.
const networkTopics = [...document.querySelectorAll('[data-network-topic]')];
function showNetworkTopic(topic) {
  networkTopics.forEach(button => {
    const open = button.dataset.networkTopic === topic;
    document.getElementById(button.getAttribute('aria-controls')).hidden = !open;
    button.setAttribute('aria-expanded', String(open));
    button.querySelector('span').textContent = open ? '−' : '+';
  });
  updateScroll();
}
networkTopics.forEach(button => button.addEventListener('click', () => {
  showNetworkTopic(button.getAttribute('aria-expanded') === 'true' ? null : button.dataset.networkTopic);
}));

const themeButton = document.querySelector('.theme-toggle');

const emailCopyButton = document.querySelector('.copy-email');
emailCopyButton.addEventListener('click', async () => {
  const status = document.getElementById('email-copy-status');
  status.textContent = '';
  emailCopyButton.disabled = true;
  try {
    await navigator.clipboard.writeText(document.getElementById('contact-email-address').textContent.trim());
    status.textContent = emailCopyButton.dataset.copySuccess;
  } catch (_) {
    status.textContent = emailCopyButton.dataset.copyError;
  } finally {
    emailCopyButton.disabled = false;
  }
});

function updateThemeLabel() {
  themeButton.setAttribute('aria-label', document.documentElement.dataset.theme === 'light' ? themeButton.dataset.labelOpen : themeButton.dataset.labelClosed);
}
updateThemeLabel();
themeButton.addEventListener('click', () => {
  const next = document.documentElement.dataset.theme === 'light' ? 'dark' : 'light';
  window.applyPortfolioTheme(next);
  try { localStorage.setItem('bilal-portfolio-theme', next); } catch (_) {}
  updateThemeLabel();
});

// Transfer reading position and open content only for an explicit language switch.
const pageSections = [...document.querySelectorAll('main > section[id]')];
document.querySelectorAll('[data-language-link]').forEach(link => {
  link.addEventListener('click', event => {
    if (event.button !== 0 || event.ctrlKey || event.metaKey || event.shiftKey || event.altKey) return;
    if (link.getAttribute('aria-current') === 'page') { event.preventDefault(); return; }
    const readingLine = header.getBoundingClientRect().bottom + 24;
    const section = pageSections.find(item => item.getBoundingClientRect().bottom > readingLine) || pageSections.at(-1);
    const bounds = section.getBoundingClientRect();
    const openProduct = productTriggers.find(button => button.getAttribute('aria-expanded') === 'true');
    const openTopic = networkTopics.find(button => button.getAttribute('aria-expanded') === 'true');
    const state = {
      path: new URL(link.href).pathname,
      created: Date.now(),
      section: section.id,
      ratio: Math.min(1, Math.max(0, (readingLine - bounds.top) / bounds.height)),
      tab: document.querySelector('[role="tab"][aria-selected="true"]').id,
      product: openProduct ? openProduct.dataset.productTrigger : null,
      topic: openTopic ? openTopic.dataset.networkTopic : null,
      details: pageSections.filter(item => item.querySelector('details[open]')).map(item => item.id)
    };
    try { sessionStorage.setItem('bilal-language-entry', JSON.stringify(state)); } catch (_) {}
  });
});

const languageEntry = window.portfolioLanguageEntry;
if (languageEntry) {
  const selectedTab = document.getElementById(languageEntry.tab);
  if (selectedTab && selectedTab.matches('[role="tab"]')) selectedTab.click();
  if (productTriggers.some(button => button.dataset.productTrigger === languageEntry.product)) setProductOpen(languageEntry.product, true);
  if (networkTopics.some(button => button.dataset.networkTopic === languageEntry.topic)) showNetworkTopic(languageEntry.topic);
  pageSections.forEach(section => {
    if (Array.isArray(languageEntry.details) && languageEntry.details.includes(section.id)) section.querySelectorAll('details').forEach(details => { details.open = true; });
  });
  addEventListener('pageshow', () => {
    const section = pageSections.find(item => item.id === languageEntry.section);
    if (section) {
      const ratio = Number.isFinite(languageEntry.ratio) ? Math.min(1, Math.max(0, languageEntry.ratio)) : 0;
      const bounds = section.getBoundingClientRect();
      const top = scrollY + bounds.top + ratio * bounds.height - header.getBoundingClientRect().height - 24;
      scrollTo({top: Math.max(0, top), left: 0, behavior: 'instant'});
    }
    window.portfolioLanguageEntry = null;
    updateScroll();
  }, {once: true});
}
