/** Deterministic 2D primitives shared by the real textures and the isolated UI test page. */
import { COLORS, FONT } from '../config.js';
/** @typedef {CanvasRenderingContext2D} Context */
/** @typedef {import('../contracts.js').TextAudit} TextAudit */
/** @typedef {import('../contracts.js').TextOptions} TextOptions */
/** @typedef {import('../contracts.js').Vec2} Vec2 */
/** @param {Context} ctx @param {number} x @param {number} y @param {number} w @param {number} h @param {number} [r] */
export function round(ctx, x, y, w, h, r = 14) {
  ctx.beginPath(); ctx.roundRect(x, y, w, h, r);
}
/** @param {Context} ctx @param {number} x @param {number} y @param {number} w @param {number} h @param {string} [fill] @param {string} [border] */
export function card(ctx, x, y, w, h, fill = '#101b2b', border = '#29364a') {
  round(ctx,x,y,w,h,14); ctx.fillStyle=fill; ctx.fill();
  if (border) { ctx.strokeStyle=border; ctx.lineWidth=1; ctx.stroke(); }
}
/** @param {Context} ctx @param {Vec2[]} points @param {string} [color] @param {number} [width] */
export function line(ctx, points, color = COLORS.orange, width = 2) {
  ctx.beginPath(); points.forEach(([x,y],i) => i ? ctx.lineTo(x,y) : ctx.moveTo(x,y));
  ctx.strokeStyle=color; ctx.lineWidth=width; ctx.lineJoin='round'; ctx.lineCap='round'; ctx.stroke();
}
/** @param {Context} ctx @param {TextAudit[] | null} audit @param {string} str @param {number} x @param {number} y @param {number} [size] @param {string} [color] @param {TextOptions} [options] */
export function text(ctx, audit, str, x, y, size = 22, color = COLORS.white,
  { weight = 400, mono = false, align = 'left', tag = '', maxWidth = Infinity, semantic = true } = {}) {
  ctx.font = `${weight} ${size}px ${mono ? FONT.mono : FONT.sans}`;
  ctx.fillStyle=color; ctx.textAlign=align; ctx.textBaseline='alphabetic';
  const m=ctx.measureText(str), w=m.width;
  ctx.fillText(str,x,y);
  if (audit && semantic) audit.push({ str, tag, x: x-(align==='center'?w/2:align==='right'?w:0),
    y: y-(m.actualBoundingBoxAscent||size*.8), width: w,
    height: (m.actualBoundingBoxAscent||size*.8)+(m.actualBoundingBoxDescent||size*.2),
    fontSize: size, color, maxWidth, overflow: w > maxWidth + 0.5 });
}
/** @param {Context} ctx @param {TextAudit[] | null} audit @param {string} str @param {number} x @param {number} y @param {string} [color] @param {TextOptions} [opts] */
export function label(ctx, audit, str, x, y, color = COLORS.muted, opts = {}) {
  text(ctx,audit,str,x,y,18,color,{mono:true,...opts});
}
/** @param {Context} ctx @param {TextAudit[] | null} audit @param {string} str @param {number} x @param {number} y @param {number} w @param {string} [color] */
export function pill(ctx, audit, str, x, y, w, color = COLORS.orange) {
  card(ctx,x,y,w,34,'#101b2b','#384355');
  text(ctx,audit,str,x+w/2,y+23,15,color,{mono:true,align:'center',maxWidth:w-16});
}
/** @param {Context} ctx @param {number} x @param {number} y @param {boolean} [on] */
export function check(ctx,x,y,on=true) {
  ctx.beginPath();ctx.arc(x,y,12,0,Math.PI*2);ctx.fillStyle=on?'#0d3c32':'#1c2a3a';ctx.fill();
  if(on) line(ctx,[[x-5,y],[x-1,y+4],[x+6,y-5]],COLORS.green,2.2);
  else {ctx.beginPath();ctx.arc(x,y,3,0,Math.PI*2);ctx.fillStyle='#698096';ctx.fill();}
}
/** @param {Context} ctx @param {number} x @param {number} y @param {number} w @param {number} h @param {number} [rows] @param {number} [cols] */
export function grid(ctx,x,y,w,h,rows=4,cols=6) {
  for(let i=0;i<=rows;i++) line(ctx,[[x,y+h*i/rows],[x+w,y+h*i/rows]],'#263248',1);
  for(let i=0;i<=cols;i++) line(ctx,[[x+w*i/cols,y],[x+w*i/cols,y+h]],'#1b2a3c',1);
}
/** @param {Context} ctx @param {number} x @param {number} y @param {number} w @param {number} h @param {(u:number)=>number} fn @param {string} [color] @param {number} [progress] */
export function chart(ctx,x,y,w,h,fn,color=COLORS.orange,progress=1) {
  /** @type {Vec2[]} */
  const points=[];
  for(let i=0;i<=120*progress;i++) {const u=i/120;points.push([x+u*w,y+h*(1-fn(u))]);}
  if(points.length>1) line(ctx,points,color,2.5);
  const end=points.at(-1);
  if(end) {const [px,py]=end;ctx.beginPath();ctx.arc(px,py,4,0,Math.PI*2);ctx.fillStyle=color;ctx.fill();}
}
