import { createLab } from './lab.js';
import { t, initLang } from './i18n.js';
import { initMath } from './math.js';

// --- Lab (no 3D needed, so start it first) ---
createLab(document.getElementById('lab'));

// --- Build-step checkboxes, remembered in this browser only ---
const KEY = 'gcb-steps-v1';
const steps = [...document.querySelectorAll('.step')];
let saved = {};
try { saved = JSON.parse(localStorage.getItem(KEY) || '{}'); } catch { saved = {}; }
function refresh() {
  let n = 0;
  steps.forEach((li) => { const on = li.querySelector('input').checked; li.classList.toggle('is-done', on); n += on; });
  document.getElementById('progress-text').textContent = t('progress', { n, total: steps.length });
}
steps.forEach((li) => {
  const box = li.querySelector('input');
  box.checked = !!saved[li.dataset.step];
  box.addEventListener('change', () => {
    saved[li.dataset.step] = box.checked;
    try { localStorage.setItem(KEY, JSON.stringify(saved)); } catch { /* storage unavailable */ }
    refresh();
  });
});
document.getElementById('reset').addEventListener('click', () => {
  saved = {}; steps.forEach((li) => { li.querySelector('input').checked = false; });
  try { localStorage.removeItem(KEY); } catch { /* storage unavailable */ }
  refresh();
});
refresh();

// --- Highlight the current section in the tab bar ---
const navLinks = [...document.querySelectorAll('.tabbar a')];
const sections = navLinks.map((a) => document.querySelector(a.getAttribute('href'))).filter(Boolean);
const markCurrent = () => {
  const y = window.scrollY + 140;
  let cur = sections[0];
  sections.forEach((s) => { if (s.getBoundingClientRect().top + window.scrollY <= y) cur = s; });
  navLinks.forEach((a) => a.setAttribute('aria-current', String(a.getAttribute('href') === '#' + cur.id)));
};
window.addEventListener('scroll', markCurrent, { passive: true });
markCurrent();

// --- Tabs (results and field slices) ---
document.querySelectorAll('[data-tabs]').forEach((box) => {
  const tabs = [...box.querySelectorAll('[role="tab"]')];
  const select = (t) => {
    tabs.forEach((x) => {
      const on = x === t;
      x.setAttribute('aria-selected', String(on)); x.tabIndex = on ? 0 : -1;
      document.getElementById(x.getAttribute('aria-controls')).hidden = !on;
    });
  };
  tabs.forEach((t, i) => {
    t.addEventListener('click', () => select(t));
    t.addEventListener('keydown', (e) => {
      const d = e.key === 'ArrowRight' ? 1 : e.key === 'ArrowLeft' ? -1 : 0;
      if (d) { const n = tabs[(i + d + tabs.length) % tabs.length]; select(n); n.focus(); }
    });
  });
});

// --- 3D viewer (loaded last; the rest of the page works without it) ---
const tabs = [...document.querySelectorAll('.viewer-tabs button')];
const caption = document.getElementById('viewer-caption');
const wrap = document.getElementById('wrap');
const play = document.getElementById('play');
let currentCoil = 'x';
const setCaption = () => { caption.textContent = t('caption.' + currentCoil) + t('viewer.help'); };
document.addEventListener('langchange', () => { setCaption(); refresh(); });
initMath();
initLang(document.getElementById('lang'));

// --- Physics animations: play while on screen, pause button, respect reduced motion ---
const vids = [...document.querySelectorAll('.anim video')];
const animBtn = document.getElementById('anim-toggle');
const reduceMotion = matchMedia('(prefers-reduced-motion: reduce)').matches;
let animsOn = !reduceMotion;
const onScreen = new Set();
const syncVideos = () => vids.forEach((v) => { if (animsOn && onScreen.has(v)) v.play().catch(() => {}); else v.pause(); });
const setAnimLabel = () => { animBtn.textContent = t(animsOn ? 'anim.pause' : 'anim.play'); animBtn.setAttribute('aria-pressed', String(!animsOn)); };
const io = new IntersectionObserver((entries) => {
  entries.forEach((e) => (e.isIntersecting ? onScreen.add(e.target) : onScreen.delete(e.target)));
  syncVideos();
}, { threshold: 0.25 });
vids.forEach((v) => io.observe(v));
animBtn.addEventListener('click', () => { animsOn = !animsOn; setAnimLabel(); syncVideos(); });
document.addEventListener('langchange', setAnimLabel);
setAnimLabel();

import('./viewer.js').then(({ createViewer }) => {
  const viewer = createViewer({ stage: document.getElementById('stage'), status: document.getElementById('viewer-status'), t });
  viewer.show('x');

  tabs.forEach((b) => b.addEventListener('click', () => {
    tabs.forEach((t) => t.setAttribute('aria-selected', String(t === b)));
    const c = b.dataset.coil;
    currentCoil = c; setCaption();
    viewer.show(c);
  }));
  wrap.addEventListener('input', () => viewer.setWrap(wrap.value / 100));
  document.getElementById('show-plates').addEventListener('change', (e) => viewer.setPlates(e.target.checked));
  document.getElementById('show-wire').addEventListener('change', (e) => viewer.setWire(e.target.checked));

  const reduce = matchMedia('(prefers-reduced-motion: reduce)').matches;
  let anim = null;
  play.addEventListener('click', () => {
    if (anim) cancelAnimationFrame(anim);
    if (reduce) { wrap.value = wrap.value > 50 ? 0 : 100; viewer.setWrap(wrap.value / 100); return; }
    const from = wrap.value > 50 ? 1 : 0, to = 1 - from, t0 = performance.now(), dur = 2200;
    const stepFn = (now) => {
      const p = Math.min(1, (now - t0) / dur), e = p < 0.5 ? 2 * p * p : 1 - Math.pow(-2 * p + 2, 2) / 2;
      const k = from + (to - from) * e; wrap.value = Math.round(k * 100); viewer.setWrap(k);
      if (p < 1) anim = requestAnimationFrame(stepFn); else anim = null;
    };
    anim = requestAnimationFrame(stepFn);
  });
}).catch((e) => {
  document.getElementById('viewer-status').textContent = t('viewer.nogl');
  console.error(e);
});
