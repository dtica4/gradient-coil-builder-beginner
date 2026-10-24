// Formulas, written in TeX and drawn with KaTeX (loaded in index.html).
// Each element with data-tex="key" shows the formula below. Words inside a
// formula are looked up in WORDS, so they follow the page language.
import { currentLang } from './i18n.js';

const WORDS = {
  efficiency: { en: 'efficiency', zh: '效率', es: 'eficiencia' },
  line: { en: 'line', zh: '直线', es: 'recta' },
  measured: { en: 'measured', zh: '实测', es: 'medida' },
  design: { en: 'design', zh: '设计', es: 'diseño' },
  vs: { en: 'measured vs design', zh: '实测与设计之差', es: 'medido vs diseño' },
  perMm: { en: 'per mm', zh: '每毫米', es: 'por mm' },
};
const w = (k) => `\\text{${WORDS[k][currentLang()] ?? WORDS[k].en}}`;

const TEX = {
  larmor: () => String.raw`f = \gamma\,B_0 = 42.58\,\tfrac{\text{MHz}}{\text{T}} \times 0.032\,\text{T} \approx 1.36\,\text{MHz}`,
  gradfield: () => String.raw`B_z(x) = B_0 + G\,x \quad\Longrightarrow\quad f(x) = \gamma\,\bigl(B_0 + G\,x\bigr)`,
  onlybz: () => String.raw`\bigl|\,\mathbf{B}_0 + \mathbf{B}_{\text{coil}}\,\bigr| \;\approx\; B_0 + B_z`,
  deltaf: () => String.raw`\Delta f = \gamma\, G\, \Delta x`,
  deltafex: () => String.raw`\Delta f = 42.58\,\tfrac{\text{Hz}}{\mu\text{T}} \times 5.24\,\tfrac{\mu\text{T}}{\text{mm}} \approx 223\,\tfrac{\text{Hz}}{\text{mm}}`,
  effdef: () => String.raw`${w('efficiency')} = \frac{G}{I} \quad \left[\tfrac{\text{mT/m}}{\text{A}}\right]`,
  background: () => String.raw`B_{z,\,\text{coil}} = B_z(5\,\text{A}) - \bigl(b_0 + b_1 x + b_2 y + b_3 z\bigr)`,
  fitgrad: () => String.raw`\begin{gathered}B_z = a_0 + a_1 x + a_2 y + a_3 z\\[4pt] |G| = \sqrt{a_1^2 + a_2^2 + a_3^2} \qquad ${w('efficiency')} = \frac{|G|}{5.0\,\text{A}}\end{gathered}`,
  step: () => String.raw`G_{\text{step}} = \frac{\bar{B}_{i+1} - \bar{B}_{i}}{7\,\text{mm}}`,
  rms: () => String.raw`\text{RMS} = \frac{\sqrt{\dfrac{1}{N}\displaystyle\sum_{k=1}^{N}\bigl(B_{z,k} - ${w('line')}_k\bigr)^2}}{|G| \times 25\,\text{mm}} \times 100\,\% \qquad (N = 208)`,
  vsdesign: () => String.raw`${w('vs')}\;(\%) = \frac{${w('efficiency')}_{\,\text{${WORDS.measured[currentLang()] ?? 'measured'}}} - ${w('efficiency')}_{\,\text{${WORDS.design[currentLang()] ?? 'design'}}}}{${w('efficiency')}_{\,\text{${WORDS.design[currentLang()] ?? 'design'}}}} \times 100`,
  df2: () => String.raw`\Delta f = \gamma\,G \approx 209\text{–}275\ \tfrac{\text{Hz}}{\text{mm}}`,
  elec: () => String.raw`V = I\,R \qquad P = I^2 R \qquad \tau = \frac{L}{R}`,
  cubic: () => String.raw`B_z = c_0 + c_1 x + c_2 y + c_3 z + \dots + c_{19}\, z^3`,
};

export function renderMath(root = document) {
  if (!window.katex) return false;
  root.querySelectorAll('[data-tex]').forEach((el) => {
    const make = TEX[el.dataset.tex];
    if (!make) return;
    try {
      window.katex.render(make(), el, { displayMode: true, throwOnError: false, strict: false, output: 'htmlAndMathml' });
      el.classList.add('is-math');
    } catch (e) { console.error(e); }
  });
  return true;
}

// KaTeX loads with "defer", so wait for it once, then redraw on every language change.
export function initMath() {
  let tries = 0; // give up after ~10 s if KaTeX cannot load; the plain-text formula stays
  const tryRender = () => { if (!renderMath() && ++tries < 70) setTimeout(tryRender, 150); };
  if (document.readyState === 'complete') tryRender(); else window.addEventListener('load', tryRender);
  document.addEventListener('langchange', () => renderMath());
}
