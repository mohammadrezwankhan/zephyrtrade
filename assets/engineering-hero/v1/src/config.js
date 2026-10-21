/** All brand copy and illustrative telemetry are controlled locally. No API calls. */
export const FILM = Object.freeze({
  title: 'From First Principles to Grid-Scale Reality',
  author: 'Dr. Mohammad Rezwan Khan',
  duration: 15, fps: 60, frames: 900, width: 1920, height: 1080,
  textureDPR: 2, seed: 0x4b48414e,
  canonicalTimes: [1.5, 4.5, 8.0, 11.2, 14.0],
});
export const COLORS = Object.freeze({
  orange: '#ff8a4c', green: '#10b981', blue: '#38bdf8',
  white: '#f4f7fc', muted: '#aebed2', ink: '#060c18', violet: '#8b5cf6',
});
export const FONT = Object.freeze({
  sans: '"Inter", "SF Pro Display", Arial, sans-serif',
  mono: '"JetBrains Mono", "SFMono-Regular", "Liberation Mono", monospace',
});
export const SITES = Object.freeze({
  mrkhan: { domain: 'mrkhan.co.technology', label: 'Research & engineering', cta: 'Explore the engineering', href: 'https://mrkhan.co.technology/' },
  khanlab: { domain: 'khanlab.co.technology', label: 'Datacenter Twin Lab', cta: 'Explore the power-systems course', href: 'https://khanlab.co.technology/' },
  mkgrid: { domain: 'mkgrid.co.technology', label: 'HelioForge Energy Lab', cta: 'Explore the hybrid-energy preview', href: 'https://mkgrid.co.technology/' },
  mklab: { domain: 'mklab.co.technology', label: 'MKLab browser laboratories', cta: 'Explore the browser labs', href: 'https://mklab.co.technology/' },
  mktrade: { domain: 'mktrade.co.business', label: 'ZephyrTrade research', cta: 'Explore synthetic market scenarios', href: 'https://mktrade.co.business/' },
});
export function getSite(key = 'mrkhan') {
  return Object.hasOwn(SITES, key) ? SITES[key] : SITES.mrkhan;
}
// These are proposed motion-graphics chapters, not quotations or project outcome claims.
export const CHAPTERS = Object.freeze([
  { id: 'physics', eyebrow: '01 / THE RESEARCH WORKBENCH', title: 'First principles.',
    subtitle: 'Define the system. Make the assumptions visible.',
    panelTitle: 'Electro-thermal model', panelCode: 'MODEL / 001',
    objectLabel: 'CELL → PACK', nav: 'Physics', anchor: [0, 0, 0], yaw: -0.08 },
  { id: 'models', eyebrow: '02 / THE COMPUTATIONAL WORKBENCH', title: 'Executable models.',
    subtitle: 'Turn physical relationships into inspectable tools.',
    panelTitle: 'Power-system workspace', panelCode: 'MODEL / 002',
    objectLabel: 'MODEL → SYSTEM', nav: 'Models', anchor: [20, 3, -13], yaw: 0.13 },
  { id: 'evidence', eyebrow: '03 / THE ASSURANCE WORKBENCH', title: 'Evidence before scale.',
    subtitle: 'Connect requirements, tests, and engineering review.',
    panelTitle: 'Acceptance evidence', panelCode: 'REVIEW / 003',
    objectLabel: 'TEST → TRACEABILITY', nav: 'Evidence', anchor: [42, -1, -28], yaw: -0.12 },
  { id: 'grid', eyebrow: '04 / THE SYSTEMS WORKBENCH', title: 'Grid-scale reality.',
    subtitle: 'Connect storage, generation, control, and decisions.',
    panelTitle: 'Hybrid-energy scenario', panelCode: 'SYSTEM / 004',
    objectLabel: 'CELL → SYSTEM → GRID', nav: 'Grid scale', anchor: [63, 2, -42], yaw: 0.06 },
]);
export const TRANSITIONS = Object.freeze([[2.65, 3.35], [6.4, 7.1], [10.0, 10.8]]);
export const LAYOUT = Object.freeze({
  panel: { x: -2.75, y: -0.10, z: 0, width: 8.20, height: 4.87 },
  header: { x: 0, y: 3.44, z: 0.10, width: 15.8, height: 1.54 },
  object: { x: 4.70, y: -0.15, z: -0.35 },
  label: { x: 4.65, y: -2.94, z: 0.12, width: 5.4, height: 0.54 },
  cameraOffset: [0, 0.78, 17.7], cameraTarget: [0, 0.32, 0], fov: 38,
});
