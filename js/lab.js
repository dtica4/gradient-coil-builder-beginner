// "From current to position" lab: draws the extra field from one gradient coil
// across the 50 mm field of view and reports what it means for imaging.
import { COILS } from './config.js';
import { t } from './i18n.js';

const GAMMA = 42.58; // Hz per µT  (42.58 MHz/T)
const FOV = 50;      // mm

function lerp(a, b, t) { return a + (b - a) * t; }
function ramp(v) {   // v in [-1, 1] → blue … pale … red
  const blue = [46, 100, 168], mid = [236, 238, 240], red = [194, 65, 58];
  const [a, b, t] = v < 0 ? [mid, blue, -v] : [mid, red, v];
  return `rgb(${a.map((c, i) => Math.round(lerp(c, b[i], Math.min(1, t)))).join(',')})`;
}

export function createLab(root) {
  const canvas = root.querySelector('#lab-canvas');
  const ctx = canvas.getContext('2d');
  const iIn = root.querySelector('#i-in'), eIn = root.querySelector('#e-in');
  const out = (id) => root.querySelector(id);

  function draw() {
    const axis = root.querySelector('input[name="axis"]:checked').value;
    const I = parseFloat(iIn.value), err = parseFloat(eIn.value);
    const G = COILS[axis].efficiency * I;           // mT/m = µT/mm
    const shift = G > 0 ? err / G : 0;              // mm
    const dpr = Math.min(window.devicePixelRatio || 1, 2);
    const size = canvas.clientWidth || 360;
    canvas.width = size * dpr; canvas.height = size * dpr;
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);

    // Slice through the centre that contains the gradient axis.
    const labels = { x: ['x', 'y'], y: ['z', 'y'], z: ['z', 'x'] }[axis];
    const horizontal = axis !== 'y';
    const maxB = 5.4 * 25; // colour scale fixed at the largest case so the current slider shows a change
    const n = 50, cell = size / n;
    for (let i = 0; i < n; i++) for (let j = 0; j < n; j++) {
      const xmm = (i + 0.5) / n * FOV - FOV / 2, ymm = FOV / 2 - (j + 0.5) / n * FOV;
      const pos = horizontal ? xmm : ymm;
      const b = G * pos + err;
      ctx.fillStyle = ramp(b / maxB);
      ctx.fillRect(i * cell, j * cell, cell + 0.5, cell + 0.5);
    }
    // Lines of equal field every 25 µT.
    ctx.strokeStyle = 'rgba(24,33,43,0.55)'; ctx.lineWidth = 1;
    if (G > 0) for (let b = -150; b <= 150; b += 25) {
      const pos = (b - err) / G; if (Math.abs(pos) > FOV / 2) continue;
      const p = (pos + FOV / 2) / FOV * size;
      ctx.beginPath();
      if (horizontal) { ctx.moveTo(p, 0); ctx.lineTo(p, size); } else { ctx.moveTo(0, size - p); ctx.lineTo(size, size - p); }
      ctx.stroke();
    }
    // Zero-field line (where the frequency equals the plain 1.36 MHz).
    if (G > 0 && Math.abs(shift) <= FOV / 2) {
      const p = (-shift + FOV / 2) / FOV * size;
      ctx.strokeStyle = '#18212b'; ctx.lineWidth = 2.5; ctx.setLineDash([6, 4]); ctx.beginPath();
      if (horizontal) { ctx.moveTo(p, 0); ctx.lineTo(p, size); } else { ctx.moveTo(0, size - p); ctx.lineTo(size, size - p); }
      ctx.stroke(); ctx.setLineDash([]);
    }
    ctx.fillStyle = '#18212b'; ctx.font = '600 12px Archivo, sans-serif';
    ctx.fillText(`${labels[0]} →  50 mm`, 8, size - 8);
    ctx.save(); ctx.translate(14, size - 70); ctx.rotate(-Math.PI / 2); ctx.fillText(`${labels[1]} →`, 0, 0); ctx.restore();

    out('#i-out').textContent = `${I.toFixed(1)} A`;
    out('#e-out').textContent = `${err} µT`;
    out('#r-g').textContent = `${(G + 1e-9).toFixed(2)} mT/m`;
    out('#r-df').textContent = `${Math.round(GAMMA * G)} Hz`;
    out('#r-bw').textContent = `${(GAMMA * G * FOV / 1000).toFixed(1)} kHz`;
    out('#r-shift').textContent = G > 0 ? `${shift.toFixed(1)} mm` : t('lab.none');
  }

  root.addEventListener('input', draw);
  document.addEventListener('langchange', draw);
  window.addEventListener('resize', draw);
  draw();
}
