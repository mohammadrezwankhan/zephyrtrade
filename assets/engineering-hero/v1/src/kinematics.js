/** Pure, dependency-free math. No mutable integrator, timers, or unseeded random values. */
import { FILM, CHAPTERS, TRANSITIONS, LAYOUT } from './config.js';
export const clamp = (x, a = 0, b = 1) => Math.min(b, Math.max(a, x));
export const lerp = (a, b, u) => a + (b - a) * u;
export const smooth = x => { const u = clamp(x); return u * u * (3 - 2 * u); };
export const mod1 = x => ((x % 1) + 1) % 1;
export function validTime(t) {
  if (typeof t !== 'number' || !Number.isFinite(t)) throw new TypeError('Time must be a finite number in seconds.');
  return clamp(t, 0, FILM.duration);
}
export function expoInOut(x) {
  const u = clamp(x);
  if (u === 0 || u === 1) return u;
  return u < 0.5 ? 2 ** (20 * u - 10) / 2 : (2 - 2 ** (-20 * u + 10)) / 2;
}
export function timeline(input) {
  const t = validTime(input);
  let stage = 3, u = 1, transit = false, transition = -1;
  for (let i = 0; i < TRANSITIONS.length; i++) {
    const [start, end] = TRANSITIONS[i];
    if (t < start) { stage = i; u = i / 3; break; }
    if (t <= end) {
      const blend = expoInOut((t - start) / (end - start));
      u = (i + blend) / 3;
      stage = blend < 0.5 ? i : i + 1;
      transit = t > start && t < end;
      transition = i;
      break;
    }
  }
  return { t, stage, u, transit, transition, endcard: smooth((t - 12.55) / 0.8) };
}
export function rotateY([x, y, z], angle) {
  return [x * Math.cos(angle) + z * Math.sin(angle), y, -x * Math.sin(angle) + z * Math.cos(angle)];
}
export const add = (a, b) => a.map((v, i) => v + b[i]);
export const sub = (a, b) => a.map((v, i) => v - b[i]);
export const dot = (a, b) => a.reduce((v, x, i) => v + x * b[i], 0);
export const cross = (a, b) => [a[1]*b[2]-a[2]*b[1], a[2]*b[0]-a[0]*b[2], a[0]*b[1]-a[1]*b[0]];
export const norm = a => { const l = Math.hypot(...a); return a.map(v => v / (l || 1)); };
export const worldPoint = (i, p) => add(CHAPTERS[i].anchor, rotateY(p, CHAPTERS[i].yaw));
export const CAMERA_POINTS = CHAPTERS.map((_, i) => worldPoint(i, LAYOUT.cameraOffset));
export const TARGET_POINTS = CHAPTERS.map((_, i) => worldPoint(i, LAYOUT.cameraTarget));
/** Uniform Catmull-Rom matches THREE.CatmullRomCurve3(..., false, 'catmullrom', tension). */
export function catmullRom(points, u, tension = 0.25) {
  const n = points.length - 1, p = clamp(u) * n;
  let i = Math.floor(p), w = p - i;
  if (i === n) { i = n - 1; w = 1; }
  const p1 = points[i], p2 = points[i + 1];
  const p0 = i > 0 ? points[i - 1] : p1.map((v, k) => 2 * v - p2[k]);
  const p3 = i + 2 <= n ? points[i + 2] : p2.map((v, k) => 2 * v - p1[k]);
  return p1.map((v, k) => {
    const v0 = (p2[k] - p0[k]) * tension, v1 = (p3[k] - p1[k]) * tension;
    return (2*w*w*w-3*w*w+1)*v + (w*w*w-2*w*w+w)*v0
      + (-2*w*w*w+3*w*w)*p2[k] + (w*w*w-w*w)*v1;
  });
}
export function cameraState(input) {
  const state = timeline(input), { t, u } = state;
  const yaw = catmullRom(CHAPTERS.map(c => [c.yaw, 0, 0]), u)[0];
  // Bounded analytical local orbital drift. No accumulated angles or handheld noise.
  const drift = rotateY([0.15*Math.sin(t*0.73), 0.075*Math.sin(t*0.91+0.4), 0.11*Math.cos(t*0.58)], yaw);
  const targetDrift = rotateY([0.025*Math.sin(t*0.46), 0.02*Math.cos(t*0.63), 0], yaw);
  return { ...state, position: add(catmullRom(CAMERA_POINTS, u), drift),
    target: add(catmullRom(TARGET_POINTS, u), targetDrift), roll: 0.0022*Math.sin(t*0.67),
    fov: LAYOUT.fov };
}
/** Perspective projection used by non-WebGL QA. Camera roll is included. */
export function project(point, cam, width = FILM.width, height = FILM.height) {
  const forward = norm(sub(cam.target, cam.position));
  let right = norm(cross(forward, [0, 1, 0]));
  let up = norm(cross(right, forward));
  const r = right, a = cam.roll || 0;
  right = r.map((v, i) => v*Math.cos(a) + up[i]*Math.sin(a));
  up = up.map((v, i) => v*Math.cos(a) - r[i]*Math.sin(a));
  const d = sub(point, cam.position), depth = dot(d, forward);
  const scale = Math.tan(cam.fov * Math.PI / 360);
  return { x: width/2 + dot(d,right)/depth/scale*height/2,
    y: height/2 - dot(d,up)/depth/scale*height/2, depth };
}
export function projectedRect(stage, rect, cam = cameraState(0)) {
  const points = [-1,1].flatMap(sx => [-1,1].map(sy => project(worldPoint(stage,
    [rect.x+sx*rect.width/2, rect.y+sy*rect.height/2, rect.z]), cam)));
  return { x: Math.min(...points.map(p=>p.x)), y: Math.min(...points.map(p=>p.y)),
    right: Math.max(...points.map(p=>p.x)), bottom: Math.max(...points.map(p=>p.y)),
    depths: points.map(p=>p.depth) };
}
export function seedRandom(seed = FILM.seed) {
  let s = seed >>> 0;
  return () => { s ^= s << 13; s ^= s >>> 17; s ^= s << 5; return (s >>> 0) / 4294967296; };
}
export function chapterProgress(index, t) {
  const start = index === 0 ? 0 : TRANSITIONS[index - 1][1];
  return smooth((t - start) / 1.6);
}
export function thermalResponse(p) { return 23 + 15 * (1 - Math.exp(-3.1 * clamp(p))); }
export function telemetry(index, input) {
  const t = validTime(input), p = chapterProgress(index, t);
  return { p, temperature: thermalResponse(p), current: 0.52 + 0.025*Math.sin(t*1.7),
    cursor: Math.floor(t*2) % 2 === 0, checks: Math.min(4, Math.floor(p*4.999)),
    dispatch: 0.60 + 0.12*Math.sin(t*0.8), phase: mod1(t*0.18) };
}
