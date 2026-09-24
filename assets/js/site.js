// Jervis website: navigation, tabs, the live voice core, copy buttons, download help and the pipeline moment.
// No libraries. Everything here is progressive: without JavaScript the page is complete and every link still works.
(function () {
  'use strict';

  const $ = (sel, root = document) => root.querySelector(sel);
  const $$ = (sel, root = document) => Array.from(root.querySelectorAll(sel));
  const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  // ---------- Which computer is this? (picks the install tab, the copy shortcut and the download behaviour) ----------
  const ua = navigator.userAgent || '';
  const platform = (navigator.userAgentData && navigator.userAgentData.platform) || navigator.platform || '';
  const isMobile = /Android|iPhone|iPad|iPod/i.test(ua) || Boolean(navigator.userAgentData && navigator.userAgentData.mobile)
    || (/Mac/i.test(platform) && navigator.maxTouchPoints > 1);   // iPadOS reports itself as a Mac
  const os = /Win/i.test(platform) || /Windows/i.test(ua) ? 'win' : 'mac';

  // ---------- Header: a border once the page has scrolled ----------
  const header = $('.site-header');
  const sentinel = document.createElement('div');
  sentinel.setAttribute('aria-hidden', 'true');
  sentinel.style.cssText = 'position:absolute;top:0;left:0;width:1px;height:8px;pointer-events:none;';
  document.body.prepend(sentinel);
  new IntersectionObserver(([entry]) => header.classList.toggle('is-scrolled', !entry.isIntersecting)).observe(sentinel);

  // ---------- Mobile menu ----------
  const nav = $('#siteNav');
  const toggle = $('.menu-toggle');
  function setMenu(open) {
    toggle.setAttribute('aria-expanded', String(open));
    nav.classList.toggle('is-open', open);
  }
  toggle.addEventListener('click', () => setMenu(toggle.getAttribute('aria-expanded') !== 'true'));
  nav.addEventListener('click', (e) => { if (e.target.closest('a')) setMenu(false); });
  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape' && toggle.getAttribute('aria-expanded') === 'true') { setMenu(false); toggle.focus(); }
  });
  window.matchMedia('(min-width: 961px)').addEventListener('change', (e) => { if (e.matches) setMenu(false); });

  // ---------- Current section in the nav: every section is watched, so the mark clears between linked ones ----------
  const navLinks = $$('.site-nav a');
  const spy = new IntersectionObserver((entries) => {
    entries.forEach((entry) => {
      if (!entry.isIntersecting) return;
      navLinks.forEach((a) => {
        if (a.getAttribute('href') === `#${entry.target.id}`) a.setAttribute('aria-current', 'true');
        else a.removeAttribute('aria-current');
      });
    });
  }, { rootMargin: '-45% 0px -50% 0px' });
  $$('main > section').forEach((s) => spy.observe(s));

  // ---------- Tabs (WAI-ARIA pattern: arrows, Home and End move between tabs) ----------
  function selectTab(tab, focus) {
    const list = tab.closest('[role="tablist"]');
    $$('[role="tab"]', list).forEach((t) => {
      const on = t === tab;
      t.setAttribute('aria-selected', String(on));
      t.tabIndex = on ? 0 : -1;
      const panel = document.getElementById(t.getAttribute('aria-controls'));
      if (panel) panel.hidden = !on;
    });
    if (focus) tab.focus();
  }
  $$('[data-tabs]').forEach((list) => {
    const tabs = $$('[role="tab"]', list);
    list.addEventListener('click', (e) => { const t = e.target.closest('[role="tab"]'); if (t) selectTab(t, false); });
    list.addEventListener('keydown', (e) => {
      const i = tabs.indexOf(document.activeElement);
      if (i < 0) return;
      const next = { ArrowRight: i + 1, ArrowLeft: i - 1, Home: 0, End: tabs.length - 1 }[e.key];
      if (next === undefined) return;
      e.preventDefault();
      selectTab(tabs[(next + tabs.length) % tabs.length], true);
    });
  });
  const osTab = $(`.os-tabs [data-os="${os}"]`);
  if (osTab) selectTab(osTab, false);

  // ---------- The live voice core: the app's own orb.js, playing real exchanges ----------
  // State titles and colours are the app's (renderer.js and orb.js). Each reply is the opening sentence of what
  // Jervis's own code answers to that request (equations.py, planets.py, earth.py); see tools/screenshot_feed.py.
  const COLORS = { idle: '79 216 255', listening: '61 242 192', thinking: '165 139 255', speaking: '90 169 255' };
  const TITLES = { idle: 'Ready', listening: 'Listening…', thinking: 'Thinking…', speaking: 'Speaking' };
  const EXCHANGES = [
    ['Solve x squared minus 5x plus 6 equals 0', 'The solutions are x equals 2 and x equals 3.'],
    ['Tell me about Saturn', 'Saturn is a planet, about 1,434 million kilometers from the Sun.'],
    ['How far is New York from Tel Aviv?', 'The distance between New York, United States and Tel Aviv, Israel is about 9,115 kilometers, or 5,664 miles, in a straight line.'],
  ];
  const SCRIPT = EXCHANGES.flatMap(([ask, reply]) => [
    { state: 'idle', text: 'Say “Hey Jervis”.', ms: 2200 },
    { state: 'listening', text: `“${ask}”`, ms: 3000 },
    { state: 'thinking', text: 'Working on it.', ms: 1400 },
    { state: 'speaking', text: `“${reply}”`, ms: 2600 + reply.length * 30 },   // time to read the whole reply
  ]);
  const coreStage = $('.core-stage');
  const coreFigure = $('.hero-core');
  const coreState = $('#coreState');
  const coreSub = $('#coreSub');
  function showCoreStep(step) {
    window.setOrbState && window.setOrbState(step.state);
    coreState.textContent = TITLES[step.state];
    coreFigure.style.setProperty('--core-rgb', COLORS[step.state]);
    coreSub.classList.add('is-swapping');
    setTimeout(() => { coreSub.textContent = step.text; coreSub.classList.remove('is-swapping'); }, reducedMotion ? 0 : 180);
  }
  if (typeof window.initOrb === 'function' && coreStage) {
    window.initOrb('heroOrb');
    let index = 0;
    let timer = null;
    let visible = true;
    const advance = () => {
      timer = null;
      index = (index + 1) % SCRIPT.length;
      showCoreStep(SCRIPT[index]);
      schedule();
    };
    const schedule = () => { if (!timer && visible && !document.hidden) timer = setTimeout(advance, SCRIPT[index].ms); };
    const stop = () => { clearTimeout(timer); timer = null; };
    if (reducedMotion) {
      // A single still frame of the core with one real exchange written out; nothing plays by itself.
      window.setOrbState && window.setOrbState('speaking');
      coreState.textContent = TITLES.speaking;
      coreFigure.style.setProperty('--core-rgb', COLORS.speaking);
      coreSub.textContent = `“${EXCHANGES[0][0]}” … “${EXCHANGES[0][1]}”`;
      setTimeout(() => document.body.classList.add('scene-paused'), 400);
    } else {
      showCoreStep(SCRIPT[0]);
      // orb.js skips drawing while body has .scene-paused: no work at all while the hero is off screen.
      new IntersectionObserver(([entry]) => {
        visible = entry.isIntersecting;
        document.body.classList.toggle('scene-paused', !visible);
        visible ? schedule() : stop();
      }, { threshold: 0.05 }).observe(coreStage);
      document.addEventListener('visibilitychange', () => (document.hidden ? stop() : schedule()));
    }
  }

  // ---------- Copy buttons ----------
  function selectText(el) {
    const range = document.createRange();
    range.selectNodeContents(el);
    const sel = window.getSelection();
    sel.removeAllRanges();
    sel.addRange(range);
  }
  async function copyText(text) {
    try {
      await navigator.clipboard.writeText(text);
      return true;
    } catch (_) {
      const area = document.createElement('textarea');
      area.value = text;
      area.setAttribute('readonly', '');
      area.style.cssText = 'position:fixed;opacity:0;';
      document.body.append(area);
      area.select();
      let ok = false;
      try { ok = document.execCommand('copy'); } catch (__) { ok = false; }
      area.remove();
      return ok;
    }
  }
  $$('.copy-btn').forEach((btn) => {
    const label = $('.copy-text', btn);
    btn.addEventListener('click', async () => {
      const source = (btn.dataset.copyTarget && document.getElementById(btn.dataset.copyTarget)) || btn.parentElement.querySelector('code');
      const text = btn.dataset.copy || (source && source.textContent.trim()) || '';
      const ok = await copyText(text);
      if (!ok && source) selectText(source);   // leave it selected so the keyboard shortcut works
      label.textContent = ok ? 'Copied' : (os === 'mac' ? 'Press ⌘C' : 'Press Ctrl+C');
      btn.classList.toggle('is-copied', ok);
      clearTimeout(btn._t);
      btn._t = setTimeout(() => { label.textContent = 'Copy'; btn.classList.remove('is-copied'); }, 2400);
    });
  });

  // ---------- Download ----------
  // On a computer the links download the real zip and a note points to the next step. On a phone, where Jervis
  // can't run, the same buttons send the page to your computer instead (the zip is still one tap away in the note).
  const toast = $('#toast');
  const toastText = $('#toastText');
  const toastLink = $('#toastLink');
  const zipHref = $('[data-download]').getAttribute('href');
  let toastTimer = null;
  function hideToast() { toast.hidden = true; }
  function showToast(text, linkText, linkHref, asDownload) {
    toastText.textContent = text;
    toastLink.textContent = linkText;
    toastLink.setAttribute('href', linkHref);
    toastLink.toggleAttribute('download', Boolean(asDownload));
    toast.hidden = false;
    clearTimeout(toastTimer);
    toastTimer = setTimeout(hideToast, 12000);
  }
  if (isMobile) {
    $$('[data-download]').forEach((link) => {
      link.setAttribute('aria-label', 'Send Jervis to my computer');
      const label = $('.btn-label', link);
      if (label) label.textContent = 'Send to my computer';
      const use = $('use', link);
      if (use) use.setAttribute('href', '#i-paper-plane-tilt');
    });
    $('#heroMeta').textContent = 'Jervis runs on a Mac or a Windows PC. Send yourself the link and download it there.';
    $$('.mobile-note').forEach((n) => { n.hidden = false; });
  }
  $$('[data-download]').forEach((link) => {
    link.addEventListener('click', async (e) => {
      if (isMobile) {
        e.preventDefault();
        const url = new URL('#download', location.href).href;
        let shared = false;
        if (navigator.share) {
          try { await navigator.share({ title: 'Jervis', text: 'Jervis, a voice assistant for macOS and Windows', url }); shared = true; }
          catch (err) { if (err && err.name === 'AbortError') return; }
        }
        const copied = shared ? false : await copyText(url);
        showToast(shared ? 'Open the link on your Mac or PC to download Jervis.'
          : copied ? 'Link copied. Open it on your Mac or PC to download Jervis.'
            : 'Open this page on your Mac or PC to download Jervis.', 'Download here anyway', zipHref, true);
        return;
      }
      const file = link.getAttribute('href').split('/').pop();
      showToast(`Downloading ${file}. Next, unzip it and follow the ${os === 'win' ? 'Windows' : 'macOS'} steps.`, 'See the install steps', '#install', false);
      const tab = $(`.os-tabs [data-os="${os}"]`);
      if (tab) selectTab(tab, false);
    });
  });
  $('.toast-close').addEventListener('click', hideToast);
  toastLink.addEventListener('click', hideToast);

  // ---------- The pipeline lights up once, in order, when it comes into view ----------
  const flow = $('[data-flow]');
  if (flow) {
    if (reducedMotion || !('IntersectionObserver' in window)) flow.classList.add('is-lit');
    else {
      const io = new IntersectionObserver(([entry]) => {
        if (entry.isIntersecting) { flow.classList.add('is-lit'); io.disconnect(); }
      }, { threshold: 0.4 });
      io.observe(flow);
    }
  }
})();
