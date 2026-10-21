import * as THREE from 'three';
import { EffectComposer } from 'three/addons/postprocessing/EffectComposer.js';
import { RenderPass } from 'three/addons/postprocessing/RenderPass.js';
import { UnrealBloomPass } from 'three/addons/postprocessing/UnrealBloomPass.js';
import { OutputPass } from 'three/addons/postprocessing/OutputPass.js';
import { FILM, CHAPTERS, LAYOUT } from '../config.js';
import { cameraState, CAMERA_POINTS, TARGET_POINTS, catmullRom, sub, timeline, validTime } from '../kinematics.js';
import { makeCanvas, drawPanel, drawHeader, drawObjectLabel, drawHUD, summarizeSurface, PANEL_SIZE } from '../ui/panels.js';
import { loadFonts } from '../font-assets.js';
import { palette, roundedSlabGeometry, box, wire } from './materials.js';
import { createEnvironment } from './environment.js';
import { createHeroObject } from './objects.js';
import { createConduit } from './conduit.js';

function surfacePlane(surface,w,h) {
  const texture=new THREE.CanvasTexture(surface.canvas);texture.colorSpace=THREE.SRGBColorSpace;
  texture.generateMipmaps=false;texture.minFilter=THREE.LinearFilter;texture.magFilter=THREE.LinearFilter;
  texture.anisotropy=4;
  const mat=new THREE.MeshBasicMaterial({map:texture,transparent:true,depthWrite:false,toneMapped:false,side:THREE.FrontSide});
  const mesh=new THREE.Mesh(new THREE.PlaneGeometry(w,h),mat);
  return {surface,texture,mesh};
}
function projectBox(object,camera,width,height) {
  const b=new THREE.Box3().setFromObject(object),pts=[];
  if(b.isEmpty())return null;
  for(const x of [b.min.x,b.max.x])for(const y of [b.min.y,b.max.y])for(const z of [b.min.z,b.max.z]){
    const p=new THREE.Vector3(x,y,z).project(camera);pts.push({x:(p.x*.5+.5)*width,y:(.5-p.y*.5)*height,z:p.z});
  }
  return {x:Math.min(...pts.map(p=>p.x)),y:Math.min(...pts.map(p=>p.y)),right:Math.max(...pts.map(p=>p.x)),
    bottom:Math.max(...pts.map(p=>p.y)),minZ:Math.min(...pts.map(p=>p.z)),maxZ:Math.max(...pts.map(p=>p.z))};
}
function projectedSurface(item,camera,width,height) {
  item.mesh.updateWorldMatrix(true,false);
  const attr=item.mesh.geometry.getAttribute('position'),p=new THREE.Vector3(),corners=[];
  for(let i=0;i<4;i++){p.fromBufferAttribute(attr,i).applyMatrix4(item.mesh.matrixWorld).project(camera);corners.push({x:(p.x*.5+.5)*width,y:(.5-p.y*.5)*height,z:p.z});}
  return {x:Math.min(...corners.map(p=>p.x)),y:Math.min(...corners.map(p=>p.y)),
    right:Math.max(...corners.map(p=>p.x)),bottom:Math.max(...corners.map(p=>p.y)),
    minZ:Math.min(...corners.map(p=>p.z)),maxZ:Math.max(...corners.map(p=>p.z)),corners};
}
function overlaps(a,b,padding=0){return a&&b&&Math.min(a.right,b.right)-Math.max(a.x,b.x)>padding&&Math.min(a.bottom,b.bottom)-Math.max(a.y,b.y)>padding;}

/**
 * Create one lifecycle-owned scene. The only animation entry point is setTime(t).
 * This module never calls requestAnimationFrame, Date, performance.now, or timers.
 */
export async function createHero({ container, capture=false, site='mrkhan', width=1920, height=1080, quality='high' }={}) {
  if(!(container instanceof HTMLElement))throw new TypeError('createHero requires a container element.');
  const fonts=await loadFonts();
  const renderer=new THREE.WebGLRenderer({antialias:false,alpha:false,powerPreference:'high-performance',preserveDrawingBuffer:capture});
  renderer.setPixelRatio(1);renderer.setSize(width,height,false);renderer.domElement.className='khan-hero-webgl';
  renderer.outputColorSpace=THREE.SRGBColorSpace;renderer.toneMapping=THREE.ACESFilmicToneMapping;renderer.toneMappingExposure=1.10;
  renderer.setClearColor('#060a14',1);
  renderer.transmissionResolutionScale=capture?1:.65;
  container.appendChild(renderer.domElement);
  const gl=renderer.getContext(),hasHDR=!!gl.getExtension('EXT_color_buffer_float');
  const sampleOptions=hasHDR ? Array.from(gl.getInternalformatParameter(gl.RENDERBUFFER,gl.RGBA16F,gl.SAMPLES)||[]) : [];
  const samples=Math.max(0,...sampleOptions.filter(n=>n<=4));
  if(capture&&(!hasHDR||samples<4)){renderer.dispose();renderer.domElement.remove();throw new Error('Capture requires WebGL2 RGBA16F HDR + 4x MSAA. Use a compatible GPU/driver.');}
  const target=new THREE.WebGLRenderTarget(width,height,{type:hasHDR?THREE.HalfFloatType:THREE.UnsignedByteType,samples:quality==='low'?0:samples,depthBuffer:true,stencilBuffer:false});
  const world=new THREE.Scene(),uiScene=new THREE.Scene(),camera=new THREE.PerspectiveCamera(LAYOUT.fov,width/height,.1,500);
  const composer=new EffectComposer(renderer,target);composer.setPixelRatio(1);composer.setSize(width,height);
  const renderPass=new RenderPass(world,camera),bloom=new UnrealBloomPass(new THREE.Vector2(width,height),.28,.48,1.15),output=new OutputPass();
  composer.addPass(renderPass);composer.addPass(bloom);composer.addPass(output);bloom.enabled=quality!=='low';
  const mats=palette(),environment=createEnvironment(renderer,world),conduit=createConduit(world);
  const cameraCurve=new THREE.CatmullRomCurve3(CAMERA_POINTS.map(p=>new THREE.Vector3(...p)),false,'catmullrom',.25);
  const targetCurve=new THREE.CatmullRomCurve3(TARGET_POINTS.map(p=>new THREE.Vector3(...p)),false,'catmullrom',.25);
  const look=new THREE.Vector3(),delta=new THREE.Vector3();
  const benches=CHAPTERS.map((chapter,index)=>{
    const root=new THREE.Group(),uiRoot=new THREE.Group();root.position.set(...chapter.anchor);root.rotation.y=chapter.yaw;
    uiRoot.position.copy(root.position);uiRoot.rotation.copy(root.rotation);world.add(root);uiScene.add(uiRoot);
    const L=LAYOUT.panel;
    const slab=new THREE.Mesh(roundedSlabGeometry(L.width+.10,L.height+.10,.22,.21),mats.glass);slab.position.set(L.x,L.y,L.z);root.add(slab);
    // Optical slab behind the UI; intentional overlay pair, not a QA collision.
    const panel=surfacePlane(makeCanvas(PANEL_SIZE.width,PANEL_SIZE.height),L.width,L.height);
    panel.mesh.position.set(L.x,L.y,.153);uiRoot.add(panel.mesh);
    const H=LAYOUT.header,header=surfacePlane(makeCanvas(1580,154),H.width,H.height);
    header.mesh.position.set(H.x,H.y,H.z);uiRoot.add(header.mesh);
    const D=LAYOUT.label,label=surfacePlane(makeCanvas(540,60),D.width,D.height);
    label.mesh.position.set(D.x,D.y,D.z);uiRoot.add(label.mesh);
    const object=new THREE.Group();object.position.set(LAYOUT.object.x,LAYOUT.object.y,LAYOUT.object.z);root.add(object);
    const animate=createHeroObject(index,object,mats);
    const deck=box(root,mats.deck,16.8,.12,5.7,0,-3.32,-.70,.2);
    for(let j=0;j<=14;j++){const x=-8.15+j*1.17;wire(root,[[x,-3.245,-3.4],[x,-3.245,1.95]],'#5a76a4',.14);}
    for(let j=0;j<=6;j++){const z=-3.4+j*.86;wire(root,[[-8.15,-3.24,z],[8.15,-3.24,z]],'#5a76a4',.14);}
    const prism=new THREE.Mesh(new THREE.IcosahedronGeometry(.70,0),mats.prism);prism.position.set(index%2?8.55:-8.7,1.75,-3.8);root.add(prism);
    const rim=new THREE.PointLight(index%2?'#38bdf8':'#ff8a4c',28,11,2);rim.position.set(5,2,3);root.add(rim);
    return {root,uiRoot,slab,panel,header,label,object,animate,prism,deck};
  });
  const hud=makeCanvas(FILM.width,FILM.height);hud.canvas.className='khan-hero-hud';container.appendChild(hud.canvas);
  let currentTime=0,disposed=false;
  const contextLost=e=>{e.preventDefault();container.dispatchEvent(new CustomEvent('hero-context-lost'));};
  renderer.domElement.addEventListener('webglcontextlost',contextLost);
  function setTime(input) {
    if(disposed)throw new Error('The hero scene was disposed.');
    const t=validTime(input),state=cameraState(t);currentTime=t;
    cameraCurve.getPoint(state.u,camera.position);delta.fromArray(sub(state.position,catmullRom(CAMERA_POINTS,state.u)));camera.position.add(delta);
    targetCurve.getPoint(state.u,look);delta.fromArray(sub(state.target,catmullRom(TARGET_POINTS,state.u)));look.add(delta);
    camera.up.set(0,1,0);camera.lookAt(look);camera.rotateZ(state.roll);camera.updateMatrixWorld(true);
    benches.forEach((b,i)=>{
      b.uiRoot.visible=state.transit?(i===state.transition||i===state.transition+1):i===state.stage;
      drawPanel(b.panel.surface,i,t);drawHeader(b.header.surface,i,t);drawObjectLabel(b.label.surface,i,t);
      b.panel.texture.needsUpdate=true;b.header.texture.needsUpdate=true;b.label.texture.needsUpdate=true;
      b.animate(t);b.prism.rotation.set(t*.10+i,.4+t*.12,.2*Math.sin(t*.22+i));
    });
    drawHUD(hud,t,site);environment.update(t,height);conduit.update(t);world.updateMatrixWorld(true);uiScene.updateMatrixWorld(true);
    // Explicit delta=0 prevents EffectComposer from consulting its internal Clock.
    renderer.autoClear=true;composer.render(0);
    // Typography bypasses bloom and ACES so white text does not bleed into glass.
    renderer.autoClear=false;renderer.clearDepth();renderer.render(uiScene,camera);renderer.autoClear=true;
    if(capture)gl.finish();
    return {t,stage:state.stage};
  }
  function diagnostics() {
    const state=timeline(currentTime),active=benches[state.stage];
    const projectItem=item=>({bounds:projectedSurface(item,camera,width,height),...summarizeSurface(item.surface)});
    const panel=projectItem(active.panel),header=projectItem(active.header),label=projectItem(active.label);
    const objectBounds=projectBox(active.object,camera,width,height);
    const dbg=gl.getExtension('WEBGL_debug_renderer_info');
    return {version:'1.0.0',threeRevision:THREE.REVISION,t:currentTime,frame:Math.round(currentTime*FILM.fps),
      stage:state.stage,transit:state.transit,width,height,capture,fonts,
      pipeline:{hdr:hasHDR,samples:target.samples,bloom:bloom.enabled,toneMapping:'ACESFilmic',textureDPR:FILM.textureDPR,
        colorSpace:renderer.outputColorSpace,renderer:dbg?gl.getParameter(dbg.UNMASKED_RENDERER_WEBGL):gl.getParameter(gl.RENDERER)},
      camera:{position:camera.position.toArray(),quaternion:camera.quaternion.toArray(),fov:camera.fov,near:camera.near,far:camera.far},
      panel,header,label,hud:summarizeSurface(hud),objectBounds,
      collisions:{panelHeader:overlaps(panel.bounds,header.bounds),panelObject:overlaps(panel.bounds,objectBounds),headerObject:overlaps(header.bounds,objectBounds),labelPanel:overlaps(label.bounds,panel.bounds)},
      // Normalized state, not wall-time metadata: supports exact seek-history comparisons.
      state:{t:currentTime,stage:state.stage,camera:camera.position.toArray(),objects:benches.map(b=>({rotation:b.prism.rotation.toArray().slice(0,3),position:b.object.position.toArray()}))}};
  }
  function resize(w,h) {
    if(capture)throw new Error('Capture dimensions are immutable.');
    if(!Number.isFinite(w)||!Number.isFinite(h)||w<2||h<2)return;
    width=Math.round(w);height=Math.round(h);renderer.setSize(width,height,false);composer.setSize(width,height);
    camera.aspect=width/height;camera.updateProjectionMatrix();setTime(currentTime);
  }
  function dispose() {
    if(disposed)return;disposed=true;
    renderer.domElement.removeEventListener('webglcontextlost',contextLost);
    const geometries=new Set(),materials=new Set(),textures=new Set();
    [world,uiScene].forEach(s=>s.traverse(o=>{if(o.geometry)geometries.add(o.geometry);if(o.material)(Array.isArray(o.material)?o.material:[o.material]).forEach(m=>materials.add(m));}));
    materials.forEach(m=>{Object.values(m).forEach(v=>{if(v?.isTexture)textures.add(v);});m.dispose();});
    textures.forEach(t=>t.dispose());geometries.forEach(g=>g.dispose());environment.dispose();
    for(const pass of composer.passes)pass.dispose?.();composer.dispose();renderer.dispose();renderer.forceContextLoss();
    renderer.domElement.remove();hud.canvas.remove();
  }
  try {
    // Compile all shader variants before declaring readiness. Initialization may be async;
    // all subsequently captured frames are synchronous functions of the requested t.
    setTime(0);await renderer.compileAsync(world,camera);await renderer.compileAsync(uiScene,camera);setTime(0);
  }catch(e){dispose();throw e;}
  return {setTime,diagnostics,resize,dispose,renderer};
}
