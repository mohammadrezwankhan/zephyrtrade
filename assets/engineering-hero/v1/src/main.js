import { FILM } from './config.js';
/** @param {string} id */
function element(id) {
  const value=document.getElementById(id);
  if(!value) throw new Error(`Missing hero element: ${id}.`);
  return value;
}
/** @param {unknown} value @returns {value is Record<string,unknown>} */
function isRecord(value) { return typeof value==='object' && value!==null && !Array.isArray(value); }
// The scene is dynamically imported so missing WebGL/dependencies leave a readable fallback.
const params=new URLSearchParams(location.search),capture=params.get('capture')==='1',embed=params.get('embed')==='1';
const siteKey=params.get('site')||'mrkhan',stage=element('hero-stage');
const fallback=element('hero-fallback'),status=element('hero-status');
const controls=element('hero-controls'),toggle=element('hero-toggle');
const reduced=matchMedia('(prefers-reduced-motion: reduce)');
document.documentElement.dataset.capture=String(capture);
window.__HERO_ERROR__=null;window.__HERO_READY__=false;
window.__HERO_READINESS__=boot();
async function boot(){
  /** @type {import('./contracts.js').Hero} */
  let hero;
  try {
    const {createHero}=await import('./scene/index.js');
    const initialWidth=capture?FILM.width:Math.max(320,Math.min(1920,Math.round(stage.getBoundingClientRect().width*Math.min(devicePixelRatio,1.5))));
    hero=await createHero({container:stage,capture,site:siteKey,width:initialWidth,height:capture?FILM.height:Math.round(initialWidth*9/16)});
    window.setSimulationTime=t=>hero.setTime(t);
    window.getHeroDiagnostics=()=>hero.diagnostics();
    window.disposeHero=()=>cleanup();
    fallback.hidden=true;window.__HERO_READY__=true;
  } catch(error) {
    window.__HERO_ERROR__=error instanceof Error ? error.stack||error.message : String(error);
    status.textContent='Interactive 3D is unavailable. The engineering story remains available in the text version.';
    console.error(error);return null;
  }
  let raf=0,playing=false,baseTime=0,origin=0,intersecting=true,destroyed=false,autoResume=false;
  function updateToggle(){toggle.textContent=playing?'Pause motion':'Play motion';toggle.setAttribute('aria-pressed',String(playing));}
  function pause(){if(playing){baseTime=Math.min(FILM.duration,(performance.now()-origin)/1000);}playing=false;cancelAnimationFrame(raf);raf=0;updateToggle();}
  /** @param {number} now */
  function tick(now){
    if(!playing||destroyed)return;
    const t=Math.min(FILM.duration,(now-origin)/1000);hero.setTime(t);
    if(t>=FILM.duration){baseTime=FILM.duration;playing=false;updateToggle();return;}
    raf=requestAnimationFrame(tick);
  }
  function play(){
    if(capture||destroyed||playing||document.hidden||!intersecting)return;
    if(baseTime>=FILM.duration)baseTime=0;
    origin=performance.now()-baseTime*1000;playing=true;updateToggle();raf=requestAnimationFrame(tick);
  }
  /** @param {number} t */
  function seek(t){pause();const result=hero.setTime(t);baseTime=result.t;return result;}
  // Capture never constructs observers, starts RAF, or reads a live playback clock.
  if(capture){window.disposeHero=()=>hero.dispose();return hero;}
  window.setSimulationTime=seek;
  controls.hidden=embed;toggle.addEventListener('click',()=>{autoResume=false;playing?pause():play();});
  element('hero-replay').addEventListener('click',()=>{seek(0);play();});
  const resize=new ResizeObserver(entries=>{
    const entry=entries[0];
    if(!entry)return;
    const {width}=entry.contentRect;
    const renderWidth=Math.max(320,Math.min(1920,Math.round(width*Math.min(devicePixelRatio,1.5))));
    hero.resize(renderWidth,Math.round(renderWidth*9/16));
  });resize.observe(stage);
  const intersection=new IntersectionObserver(([entry])=>{
    if(!entry)return;
    intersecting=entry.isIntersecting;
    if(!intersecting){autoResume=playing;pause();}else if(autoResume&&!reduced.matches){autoResume=false;play();}
  },{threshold:.05});intersection.observe(stage);
  const visibility=()=>{if(document.hidden){autoResume=playing;pause();}else if(autoResume&&!reduced.matches){autoResume=false;play();}};
  document.addEventListener('visibilitychange',visibility);
  const onReduced=()=>{if(reduced.matches){autoResume=false;seek(14);}};reduced.addEventListener('change',onReduced);
  const onLost=()=>{pause();fallback.hidden=false;status.textContent='3D rendering was interrupted. Reload this page to restart it.';};
  stage.addEventListener('hero-context-lost',onLost);
  const receive=(/** @type {MessageEvent<unknown>} */ event)=>{
    // Same-origin embed only. Never accept arbitrary cross-origin control messages.
    if(event.origin!==location.origin||event.source!==window.parent||!isRecord(event.data)||event.data.type!=='khan-hero-control')return;
    if(event.data.action==='play')play();else if(event.data.action==='pause')pause();
    else if(event.data.action==='seek'&&typeof event.data.t==='number'&&Number.isFinite(event.data.t))seek(event.data.t);
  };window.addEventListener('message',receive);
  function cleanup(){if(destroyed)return;pause();destroyed=true;resize.disconnect();intersection.disconnect();
    document.removeEventListener('visibilitychange',visibility);reduced.removeEventListener('change',onReduced);
    window.removeEventListener('message',receive);stage.removeEventListener('hero-context-lost',onLost);hero.dispose();}
  // The assignment above is late-bound; capture uses direct disposal below.
  window.disposeHero=cleanup;
  window.addEventListener('pagehide',cleanup,{once:true});
  if(reduced.matches){seek(14);}else if(params.get('autoplay')==='1'){play();}else{seek(1.5);}
  if(embed&&window.parent!==window)window.parent.postMessage({type:'khan-hero-ready'},location.origin);
  return hero;
}
