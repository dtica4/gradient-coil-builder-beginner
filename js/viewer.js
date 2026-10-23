// 3D viewer: loads each coil's plates and wire as flat-sheet coordinates
// (s = distance along the sheet, h = height along the bore, t = thickness)
// and bends them from a flat sheet (wrap = 0) into the cylinder (wrap = 1).
import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';

const cache = {};

async function loadBin(url) {
  const res = await fetch(url);
  if (!res.ok) throw new Error(`Could not load ${url} (${res.status})`);
  const buf = await res.arrayBuffer();
  const hlen = new DataView(buf).getUint32(0, true);
  const meta = JSON.parse(new TextDecoder().decode(new Uint8Array(buf, 4, hlen)));
  const pos = new Int16Array(buf, 4 + hlen, meta.nv * 3);
  const off = 4 + hlen + meta.nv * 6;
  const idx = new Uint32Array(buf.slice(off, off + meta.nf * 12)); // copy: offset may not be 4-byte aligned
  const flat = new Float32Array(meta.nv * 3);
  for (let i = 0; i < flat.length; i++) flat[i] = pos[i] / meta.scale;
  return { meta, flat, idx };
}

function makeMesh(data, material) {
  const g = new THREE.BufferGeometry();
  g.setAttribute('position', new THREE.BufferAttribute(new Float32Array(data.flat.length), 3));
  g.setIndex(new THREE.BufferAttribute(data.idx, 1));
  const m = new THREE.Mesh(g, material);
  m.userData = data;
  return m;
}

// Bend one mesh. Output axes: x = along the bore, (y, z) = the coil's cross-section.
function bend(mesh, k) {
  const { meta, flat } = mesh.userData;
  const R = meta.R, sc = (meta.s0 + meta.s1) / 2;
  const thc = sc / R + (meta.alpha * Math.PI) / 180;
  const ewx = Math.cos(thc), ewy = Math.sin(thc), eux = -ewy, euy = ewx;
  const out = mesh.geometry.attributes.position.array;
  const kk = Math.max(k, 1e-4), rho = R / kk;
  for (let i = 0; i < flat.length; i += 3) {
    const s = flat[i], h = flat[i + 1], t = flat[i + 2];
    const phi = (s - sc) / rho;
    const w = (rho + t) * Math.cos(phi) - rho + R;
    const u = (rho + t) * Math.sin(phi);
    out[i] = h;
    out[i + 1] = w * ewx + u * eux;
    out[i + 2] = w * ewy + u * euy;
  }
  mesh.geometry.attributes.position.needsUpdate = true;
  mesh.geometry.computeVertexNormals();
  mesh.geometry.computeBoundingSphere();
}

export function createViewer({ stage, status, base = 'models/', t = (k) => k }) {
  const renderer = new THREE.WebGLRenderer({ antialias: true });
  renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
  renderer.setClearColor(0xffffff, 1);
  stage.appendChild(renderer.domElement);

  const scene = new THREE.Scene();
  const camera = new THREE.PerspectiveCamera(35, 4 / 3, 1, 5000);
  camera.position.set(480, 280, 680);
  const controls = new OrbitControls(camera, renderer.domElement);
  controls.enableDamping = true;
  controls.minDistance = 150; controls.maxDistance = 2000;

  scene.add(new THREE.HemisphereLight(0xffffff, 0x9aa3ad, 1.7));
  const key = new THREE.DirectionalLight(0xffffff, 2.2); key.position.set(400, 600, 500); scene.add(key);
  const rim = new THREE.DirectionalLight(0xffd9b8, 0.9); rim.position.set(-500, -200, -400); scene.add(rim);

  const plateMat = new THREE.MeshStandardMaterial({ color: 0x4a4f57, roughness: 0.85, metalness: 0, side: THREE.DoubleSide });
  const ghostMat = new THREE.MeshStandardMaterial({ color: 0x8a9099, roughness: 0.85, transparent: true, opacity: 0.22, depthWrite: false, side: THREE.DoubleSide });
  const wireMat = new THREE.MeshStandardMaterial({ color: 0xc8743a, roughness: 0.35, metalness: 0.75, side: THREE.DoubleSide });

  const root = new THREE.Group(); scene.add(root);
  const state = { coil: 'x', wrap: 1, plates: true, wire: true, groups: {} };

  async function getCoil(c) {
    if (!cache[c]) {
      cache[c] = Promise.all([loadBin(`${base}${c}_plates.bin`), loadBin(`${base}${c}_wire.bin`)]).then(([p, w]) => {
        const g = new THREE.Group();
        g.add(makeMesh(p, plateMat)); g.add(makeMesh(w, wireMat));
        g.userData.lastK = -1;
        return g;
      });
    }
    return cache[c];
  }

  function apply() {
    const list = state.coil === 'all' ? ['x', 'y', 'z'] : [state.coil];
    root.children.slice().forEach((ch) => root.remove(ch));
    list.forEach((c) => {
      const g = state.groups[c]; if (!g) return;
      const [plates, wire] = g.children;
      plates.visible = state.plates; wire.visible = state.wire;
      // Single coil: turn it so the flat sheet faces the viewer. All three: keep the real
      // relative orientation and make the plates see-through so the inner coils show.
      const all = state.coil === 'all';
      plates.material = all ? ghostMat : plateMat;
      const m = plates.userData.meta, thc = (m.s0 + m.s1) / 2 / m.R + (m.alpha * Math.PI) / 180;
      g.rotation.x = all ? 0 : Math.PI / 2 - thc;
      if (g.userData.lastK !== state.wrap) { bend(plates, state.wrap); bend(wire, state.wrap); g.userData.lastK = state.wrap; }
      root.add(g);
    });
  }

  async function show(c) {
    state.coil = c;
    const list = c === 'all' ? ['x', 'y', 'z'] : [c];
    const missing = list.filter((k) => !state.groups[k]);
    if (missing.length) status.hidden = false, status.textContent = t('viewer.loading');
    try {
      for (const k of list) state.groups[k] = await getCoil(k);
      status.hidden = true;
    } catch (e) {
      status.hidden = false;
      status.textContent = t('viewer.error');
      console.error(e);
      return;
    }
    if (state.coil === c) apply();
  }

  function resize() {
    const w = stage.clientWidth, h = stage.clientHeight;
    renderer.setSize(w, h, false); camera.aspect = w / h; camera.updateProjectionMatrix();
  }
  new ResizeObserver(resize).observe(stage); resize();

  let visible = true;
  new IntersectionObserver(([e]) => { visible = e.isIntersecting; }).observe(stage);
  renderer.setAnimationLoop(() => { if (!visible) return; controls.update(); renderer.render(scene, camera); });

  return {
    show,
    setWrap(k) { state.wrap = k; apply(); },
    setPlates(v) { state.plates = v; apply(); },
    setWire(v) { state.wire = v; apply(); },
  };
}
