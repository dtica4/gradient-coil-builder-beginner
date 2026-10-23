// Language switch: English is the text written in index.html; Chinese and
// Spanish come from js/i18n/zh.js and js/i18n/es.js, keyed by data-i18n ids.
import zh from './i18n/zh.js';
import es from './i18n/es.js';

const PAGE = { zh, es };
const KEY = 'gcb-lang';
const english = {};   // filled from the page on first switch
let lang = 'en';

// Phrases that the scripts write (not in index.html).
const UI = {
  en: {
    progress: '{n} of {total} steps checked',
    'viewer.loading': 'Loading the coil…',
    'viewer.error': 'The 3D model did not load. Check that the models folder was uploaded, then reload the page.',
    'viewer.nogl': 'The 3D viewer could not start in this browser.',
    'viewer.help': ' Drag to turn, scroll to zoom.',
    'caption.x': 'X coil: four plates, one saddle-shaped wire loop in each.',
    'caption.y': 'Y coil: same pattern as X, turned a quarter turn around the bore.',
    'caption.z': 'Z coil: plates TL, TR, BL and BR. The wire winds around the bore many times as a double helix.',
    'caption.all': 'All three coils nested: X inside Y inside Z.',
    'lab.none': 'no gradient',
  },
  zh: {
    progress: '已完成 {n} / {total} 步',
    'viewer.loading': '正在加载线圈…',
    'viewer.error': '3D 模型未能加载。请确认 models 文件夹已上传，然后刷新页面。',
    'viewer.nogl': '此浏览器无法启动 3D 查看器。',
    'viewer.help': ' 拖动旋转，滚轮缩放。',
    'caption.x': 'X 线圈：四块板，每块板上一个马鞍形导线回路。',
    'caption.y': 'Y 线圈：与 X 相同的图案，绕孔径旋转了四分之一圈。',
    'caption.z': 'Z 线圈：TL、TR、BL、BR 四块板。导线以双螺旋形式绕孔径多圈。',
    'caption.all': '三个线圈嵌套：X 在 Y 内，Y 在 Z 内。',
    'lab.none': '无梯度',
  },
  es: {
    progress: '{n} de {total} pasos marcados',
    'viewer.loading': 'Cargando la bobina…',
    'viewer.error': 'El modelo 3D no se cargó. Verifica que la carpeta models se haya subido y vuelve a cargar la página.',
    'viewer.nogl': 'El visor 3D no pudo iniciarse en este navegador.',
    'viewer.help': ' Arrastra para girar, usa la rueda para acercar.',
    'caption.x': 'Bobina X: cuatro placas, un lazo de alambre en forma de silla de montar en cada una.',
    'caption.y': 'Bobina Y: el mismo patrón que X, girado un cuarto de vuelta alrededor del túnel.',
    'caption.z': 'Bobina Z: placas TL, TR, BL y BR. El alambre da muchas vueltas alrededor del túnel como una doble hélice.',
    'caption.all': 'Las tres bobinas anidadas: X dentro de Y, Y dentro de Z.',
    'lab.none': 'sin gradiente',
  },
};

export function t(key, vars = {}) {
  const s = (UI[lang] && UI[lang][key]) ?? UI.en[key] ?? key;
  return s.replace(/\{(\w+)\}/g, (_, v) => vars[v] ?? '');
}
export const currentLang = () => lang;

function swap(selector, attr, read, write) {
  document.querySelectorAll(selector).forEach((el) => {
    const k = el.getAttribute(attr);
    const id = attr + ':' + k;
    if (!(id in english)) english[id] = read(el);
    const text = lang === 'en' ? english[id] : (PAGE[lang][k] ?? english[id]);
    write(el, text);
  });
}

export function setLang(next) {
  lang = PAGE[next] || next === 'en' ? next : 'en';
  swap('[data-i18n]', 'data-i18n', (el) => el.innerHTML, (el, v) => { el.innerHTML = v; });
  swap('[data-i18n-text]', 'data-i18n-text', (el) => el.textContent, (el, v) => { el.textContent = v; });
  swap('[data-i18n-alt]', 'data-i18n-alt', (el) => el.getAttribute('alt'), (el, v) => el.setAttribute('alt', v));
  swap('[data-i18n-aria]', 'data-i18n-aria', (el) => el.getAttribute('aria-label'), (el, v) => el.setAttribute('aria-label', v));
  document.documentElement.lang = lang === 'zh' ? 'zh-CN' : lang;
  try { localStorage.setItem(KEY, lang); } catch { /* storage unavailable */ }
  document.dispatchEvent(new CustomEvent('langchange', { detail: lang }));
}

export function initLang(select) {
  let saved = 'en';
  try { saved = localStorage.getItem(KEY) || 'en'; } catch { /* storage unavailable */ }
  if (!['en', 'zh', 'es'].includes(saved)) saved = 'en';
  select.value = saved;
  select.addEventListener('change', () => setLang(select.value));
  if (saved !== 'en') setLang(saved); else document.dispatchEvent(new CustomEvent('langchange', { detail: 'en' }));
}
