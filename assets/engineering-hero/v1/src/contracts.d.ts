export type Vec2 = [number, number];
export type Vec3 = [number, number, number];

export interface Chapter {
  id: string;
  eyebrow: string;
  title: string;
  subtitle: string;
  panelTitle: string;
  panelCode: string;
  objectLabel: string;
  nav: string;
  anchor: Vec3;
  yaw: number;
}

export interface Rect {
  x: number;
  y: number;
  z: number;
  width: number;
  height: number;
}

export interface Bounds {
  x: number;
  y: number;
  right: number;
  bottom: number;
}

export interface TextAudit {
  str: string;
  tag: string;
  x: number;
  y: number;
  width: number;
  height: number;
  fontSize: number;
  color: string;
  maxWidth: number;
  overflow: boolean;
}

export interface TextOptions {
  weight?: number;
  mono?: boolean;
  align?: CanvasTextAlign;
  tag?: string;
  maxWidth?: number;
  semantic?: boolean;
}

export interface Surface {
  canvas: HTMLCanvasElement;
  ctx: CanvasRenderingContext2D;
  width: number;
  height: number;
  dpr: number;
  audit: TextAudit[];
}

export type Hero = Awaited<ReturnType<typeof import('./scene/index.js').createHero>>;

declare global {
  interface Window {
    __HERO_ERROR__: string | null;
    __HERO_READY__: boolean;
    __HERO_READINESS__: Promise<Hero | null>;
    setSimulationTime?: (time: number) => { t: number; stage: number };
    getHeroDiagnostics?: Hero['diagnostics'];
    disposeHero?: () => void;
  }
}
