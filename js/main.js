import { COILS, SHOW_MEASURED, MEASURED } from './config.js';
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

// --- Measured results (switched in js/config.js) ---
const m = document.getElementById('measured');
if (SHOW_MEASURED) {
  m.innerHTML = `
    <h3 class="table-title measured-head">Measured at 5 A (${MEASURED.date})</h3>
    <div class="table-wrap"><table class="results">
      <thead><tr><th scope="col">Coil</th><th scope="col">Measured efficiency<br>(mT/m/A)</th><th scope="col">Design</th><th scope="col">Difference</th><th scope="col">Gradient at 5 A (mT/m)</th><th scope="col">Linearity error, RMS</th><th scope="col">Probe noise removed</th></tr></thead>
      <tbody>${MEASURED.rows.map((r) => `<tr><th scope="row">${r.coil}</th><td>${r.eff}</td><td>${r.design}</td><td>${r.diff}</td><td>${r.grad}</td><td>${r.lin}</td><td>${r.linClean}</td></tr>`).join('')}</tbody>
    </table></div>
    <p class="verdict">All three coils are within 3.5 % of the design and at the 1.0 mT/m/A target (Y within measurement uncertainty: a second method gives 1.032). Linearity error is about 3 %, below the 5 % target; about half of it is probe noise (±3.8 µT per reading).</p>`;
} else {
  m.innerHTML = `<p class="pending">Measured results will appear here once the lab approves publishing them.</p>`;
}

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
