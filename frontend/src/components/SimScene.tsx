import { useEffect, useRef } from "react";
import * as THREE from "three";
import { OrbitControls } from "three/examples/jsm/controls/OrbitControls.js";
import type { Replay } from "../lib/types";

export function webglAvailable(): boolean {
  try {
    const c = document.createElement("canvas");
    return !!(window.WebGLRenderingContext && (c.getContext("webgl2") || c.getContext("webgl")));
  } catch { return false; }
}

const css = (name: string) => `rgb(${getComputedStyle(document.documentElement).getPropertyValue(`--${name}`).trim().split(/\s+/).join(",")})`;

/** Three.js replay of a backend simulation. frameIdx is driven by the parent (play/pause/scrub). */
export function SimScene3D({ replay, frameIdx, offset }: { replay: Replay; frameIdx: number; offset: [number, number] }) {
  const mount = useRef<HTMLDivElement>(null);
  const state = useRef<{ renderer: THREE.WebGLRenderer; scene: THREE.Scene; camera: THREE.PerspectiveCamera; points: THREE.Points; trail: THREE.Points; controls: OrbitControls; raf: number } | null>(null);

  useEffect(() => {
    const el = mount.current!;
    const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    renderer.setSize(el.clientWidth, el.clientHeight);
    el.appendChild(renderer.domElement);
    const scene = new THREE.Scene();
    const camera = new THREE.PerspectiveCamera(45, el.clientWidth / el.clientHeight, 0.1, 1000);
    camera.position.set(28, -34, 30);
    camera.up.set(0, 0, 1);
    const controls = new OrbitControls(camera, renderer.domElement);
    controls.enableDamping = true;
    scene.add(new THREE.AmbientLight(0xffffff, 0.7));
    const sun = new THREE.DirectionalLight(0xffffff, 1.1);
    sun.position.set(20, -20, 40);
    scene.add(sun);

    const g = replay.geometry;
    const mode = String(replay.params.mode);
    // petals (schematic): 5 flattened ellipsoids around the origin
    const petalMat = new THREE.MeshStandardMaterial({ color: css("petal"), transparent: true, opacity: 0.35, side: THREE.DoubleSide });
    const nPetals = mode === "ring_progression" ? 24 : 5;
    const petalR = mode === "ring_progression" ? 16 : 9;
    for (let i = 0; i < nPetals; i++) {
      const a = (i / nPetals) * Math.PI * 2;
      const m = new THREE.Mesh(new THREE.SphereGeometry(1, 20, 12), petalMat);
      m.scale.set(mode === "ring_progression" ? 5 : 7, mode === "ring_progression" ? 1.6 : 4, 0.4);
      m.position.set(Math.cos(a) * petalR, Math.sin(a) * petalR, -1);
      m.rotation.z = a;
      scene.add(m);
    }
    addSpeciesStructures(scene, mode, g);
    const anthMat = new THREE.MeshStandardMaterial({ color: css("pollen") });
    g.anthers.forEach(([x, y, z]) => { const s = new THREE.Mesh(new THREE.SphereGeometry(0.45, 12, 8), anthMat); s.position.set(x, y, z); scene.add(s); });
    const tgtMat = new THREE.MeshStandardMaterial({ color: css("leaf"), transparent: true, opacity: 0.65 });
    g.targets.forEach(([x, y, z]) => { const s = new THREE.Mesh(new THREE.SphereGeometry(g.target_radius_mm, 16, 12), tgtMat); s.position.set(x, y, z); scene.add(s); });
    // virtual effector aim point (shows misalignment)
    const eff = new THREE.Mesh(new THREE.TorusGeometry(1.2, 0.12, 8, 32), new THREE.MeshBasicMaterial({ color: css("alert") }));
    eff.position.set(g.stigma[0] + offset[0], g.stigma[1] + offset[1], g.stigma[2]);
    scene.add(eff);
    scene.add(new THREE.GridHelper(80, 16, 0x888888, 0x444444).rotateX(Math.PI / 2).translateY(0).translateZ(0));

    const maxN = Math.max(1, ...replay.frames.map((f) => f.p.length));
    const geom = new THREE.BufferGeometry();
    geom.setAttribute("position", new THREE.BufferAttribute(new Float32Array(maxN * 3), 3));
    geom.setAttribute("color", new THREE.BufferAttribute(new Float32Array(maxN * 3), 3));
    const points = new THREE.Points(geom, new THREE.PointsMaterial({ size: 0.6, vertexColors: true }));
    scene.add(points);
    // short trails: positions of the previous TRAIL frames, drawn faintly
    const trailGeom = new THREE.BufferGeometry();
    trailGeom.setAttribute("position", new THREE.BufferAttribute(new Float32Array(maxN * 3 * TRAIL), 3));
    const trail = new THREE.Points(trailGeom, new THREE.PointsMaterial({ size: 0.3, color: css("pollen"), transparent: true, opacity: 0.3 }));
    scene.add(trail);

    const loop = () => {
      controls.update();
      renderer.render(scene, camera);
      st.raf = requestAnimationFrame(loop);
    };
    const st = { renderer, scene, camera, points, trail, controls, raf: 0 };
    state.current = st;
    loop();
    const onResize = () => {
      renderer.setSize(el.clientWidth, el.clientHeight);
      camera.aspect = el.clientWidth / el.clientHeight;
      camera.updateProjectionMatrix();
    };
    const ro = new ResizeObserver(onResize);
    ro.observe(el);
    return () => {
      cancelAnimationFrame(st.raf);
      ro.disconnect();
      controls.dispose();
      scene.traverse((o) => {
        if (o instanceof THREE.Mesh || o instanceof THREE.Points) {
          o.geometry.dispose();
          (Array.isArray(o.material) ? o.material : [o.material]).forEach((m) => m.dispose());
        }
      });
      renderer.dispose();
      el.removeChild(renderer.domElement);
      state.current = null;
    };
  }, [replay, offset]);

  useEffect(() => {
    const st = state.current;
    const fr = replay.frames[Math.min(frameIdx, replay.frames.length - 1)];
    if (!st || !fr) return;
    const pos = st.points.geometry.getAttribute("position") as THREE.BufferAttribute;
    const col = st.points.geometry.getAttribute("color") as THREE.BufferAttribute;
    const free = new THREE.Color(css("pollen")), got = new THREE.Color(css("leaf"));
    fr.p.forEach(([x, y, z], i) => {
      pos.setXYZ(i, x, y, z);
      const c = fr.c[i] ? got : free;
      col.setXYZ(i, c.r, c.g, c.b);
    });
    st.points.geometry.setDrawRange(0, fr.p.length);
    pos.needsUpdate = true;
    col.needsUpdate = true;
    const tpos = st.trail.geometry.getAttribute("position") as THREE.BufferAttribute;
    let n = 0;
    for (let k = 1; k <= TRAIL; k++) {
      const prev = replay.frames[frameIdx - k];
      if (!prev) break;
      prev.p.forEach(([x, y, z], i) => { if (!prev.c[i] && n < tpos.count) tpos.setXYZ(n++, x, y, z); });
    }
    st.trail.geometry.setDrawRange(0, n);
    tpos.needsUpdate = true;
  }, [frameIdx, replay]);

  return <div ref={mount} className="h-full w-full" aria-label="3D pollination simulation" />;
}

const TRAIL = 4;

/** Species-mode specific schematic structures (not to scale; mm units). */
function addSpeciesStructures(scene: THREE.Scene, mode: string, g: Replay["geometry"]) {
  const mat = (name: string, opacity = 1) => new THREE.MeshStandardMaterial({ color: css(name), transparent: opacity < 1, opacity });
  const label = (text: string, x: number, y: number, z: number) => {
    const c = document.createElement("canvas");
    c.width = 256; c.height = 48;
    const ctx = c.getContext("2d")!;
    ctx.font = "26px IBM Plex Mono, monospace";
    ctx.fillStyle = css("ink");
    ctx.fillText(text, 4, 32);
    const sp = new THREE.Sprite(new THREE.SpriteMaterial({ map: new THREE.CanvasTexture(c), transparent: true }));
    sp.scale.set(10, 1.9, 1);
    sp.position.set(x, y, z);
    scene.add(sp);
  };
  if (mode === "vibration") {
    // fused anther cone around the style (tomato / brinjal), opening downwards to the stigma
    const cone = new THREE.Mesh(new THREE.ConeGeometry(1.6, 4, 24, 1, true), mat("pollen", 0.45));
    cone.rotation.x = -Math.PI / 2; cone.position.set(0, 0, -1);
    scene.add(cone);
    label("anther cone", 4, 0, 1.5);
    label("stigma", 3, 0, g.stigma[2] - 1);
  } else if (mode === "cross_transfer") {
    // separate donor flower (compatible cultivar) above the target flower
    const donor = new THREE.Group();
    for (let i = 0; i < 5; i++) {
      const a = (i / 5) * Math.PI * 2;
      const p = new THREE.Mesh(new THREE.SphereGeometry(1, 16, 10), mat("petal", 0.25));
      p.scale.set(4.5, 2.6, 0.3); p.position.set(Math.cos(a) * 5, Math.sin(a) * 5, 0); p.rotation.z = a;
      donor.add(p);
    }
    donor.position.set(0, 0, 25);
    scene.add(donor);
    label("donor flower", 8, 0, 27);
    label("target stigma", 5, 0, g.stigma[2] + 2);
    const style = new THREE.Mesh(new THREE.CylinderGeometry(0.25, 0.25, 2.5, 10), mat("leaf"));
    style.rotation.x = Math.PI / 2; style.position.set(0, 0, 0.2);
    scene.add(style);
  } else if (mode === "air_assisted") {
    // domed receptacle carrying many pistils (strawberry)
    const dome = new THREE.Mesh(new THREE.SphereGeometry(3.4, 32, 16, 0, Math.PI * 2, 0, Math.PI / 2), mat("pollen", 0.35));
    dome.scale.set(1, 1, 0.35);
    scene.add(dome);
    label("receptacle: many pistils", 6, 0, 3);
  } else if (mode === "ring_progression") {
    const disc = new THREE.Mesh(new THREE.CylinderGeometry(13, 13, 0.6, 48), mat("muted", 0.35));
    disc.rotation.x = Math.PI / 2; disc.position.z = -0.4;
    scene.add(disc);
    label("pollen-presenting ring", 14, 0, 2);
    label("receptive floret ring", 0, -11, 3);
  } else if (mode === "column_transfer") {
    const col = new THREE.Mesh(new THREE.CylinderGeometry(0.5, 0.7, g.stigma[2] + 6, 16), mat("petal", 0.6));
    col.rotation.x = Math.PI / 2; col.position.z = (g.stigma[2] - 6) / 2;
    scene.add(col);
    for (let i = 0; i < 5; i++) {
      const a = (i / 5) * Math.PI * 2;
      const pad = new THREE.Mesh(new THREE.SphereGeometry(0.5, 10, 8), mat("alert"));
      pad.position.set(Math.cos(a) * 0.9, Math.sin(a) * 0.9, g.stigma[2] + 0.4);
      scene.add(pad);
    }
    label("staminal column", 4, 0, -3);
    label("5 stigma pads", 4, 0, g.stigma[2] + 2);
  } else {
    label("anther ring", g.anthers[0]?.[0] ?? 3, 0, 2);
    label("stigma", 2, 0, g.stigma[2] + 2);
  }
}

/** 2D fallback: side (x-z) projection on a canvas. */
export function SimScene2D({ replay, frameIdx, offset }: { replay: Replay; frameIdx: number; offset: [number, number] }) {
  const ref = useRef<HTMLCanvasElement>(null);
  useEffect(() => {
    const c = ref.current;
    if (!c) return;
    const ctx = c.getContext("2d")!;
    const W = (c.width = c.clientWidth * devicePixelRatio), H = (c.height = c.clientHeight * devicePixelRatio);
    const s = Math.min(W, H) / 70;
    const X = (x: number) => W / 2 + x * s, Y = (z: number) => H * 0.55 - z * s;
    ctx.clearRect(0, 0, W, H);
    ctx.strokeStyle = css("line");
    ctx.beginPath(); ctx.moveTo(0, Y(-1)); ctx.lineTo(W, Y(-1)); ctx.stroke();
    const g = replay.geometry;
    ctx.fillStyle = css("pollen");
    g.anthers.forEach(([x, , z]) => { ctx.beginPath(); ctx.arc(X(x), Y(z), 0.45 * s, 0, 7); ctx.fill(); });
    ctx.fillStyle = css("leaf");
    g.targets.forEach(([x, , z]) => { ctx.beginPath(); ctx.arc(X(x), Y(z), g.target_radius_mm * s, 0, 7); ctx.fill(); });
    ctx.strokeStyle = css("alert");
    ctx.beginPath(); ctx.arc(X(g.stigma[0] + offset[0]), Y(g.stigma[2]), 1.2 * s, 0, 7); ctx.stroke();
    const fr = replay.frames[Math.min(frameIdx, replay.frames.length - 1)];
    fr?.p.forEach(([x, , z], i) => {
      ctx.fillStyle = fr.c[i] ? css("leaf") : css("pollen");
      ctx.fillRect(X(x) - 2, Y(z) - 2, 4, 4);
    });
    ctx.fillStyle = css("muted");
    ctx.font = `${12 * devicePixelRatio}px IBM Plex Mono, monospace`;
    ctx.fillText("side view (x–z, mm) · 2D fallback", 10 * devicePixelRatio, 18 * devicePixelRatio);
  }, [replay, frameIdx, offset]);
  return <canvas ref={ref} className="h-full w-full" aria-label="2D pollination simulation" />;
}
