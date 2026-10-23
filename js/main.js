import { COILS } from './config.js';
import { createLab } from './lab.js';

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
  document.getElementById('done-count').textContent = n;
  document.getElementById('step-count').textContent = steps.length;
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
const HELP = ' Drag to turn, scroll to zoom.';

import('./viewer.js').then(({ createViewer }) => {
  const viewer = createViewer({ stage: document.getElementById('stage'), status: document.getElementById('viewer-status') });
  viewer.show('x');

  tabs.forEach((b) => b.addEventListener('click', () => {
    tabs.forEach((t) => t.setAttribute('aria-selected', String(t === b)));
    const c = b.dataset.coil;
    caption.textContent = (c === 'all' ? 'All three coils nested: X inside Y inside Z.' : COILS[c].caption) + HELP;
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
  document.getElementById('viewer-status').textContent = 'The 3D viewer could not start in this browser.';
  console.error(e);
});
