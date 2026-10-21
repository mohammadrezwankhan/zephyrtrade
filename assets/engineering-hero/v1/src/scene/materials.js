import * as THREE from 'three';
import { COLORS } from '../config.js';
export function roundedSlabGeometry(width, height, depth, radius = 0.18) {
  const x=-width/2,y=-height/2,r=Math.min(radius,width/2,height/2),s=new THREE.Shape();
  s.moveTo(x+r,y);s.lineTo(x+width-r,y);s.quadraticCurveTo(x+width,y,x+width,y+r);
  s.lineTo(x+width,y+height-r);s.quadraticCurveTo(x+width,y+height,x+width-r,y+height);
  s.lineTo(x+r,y+height);s.quadraticCurveTo(x,y+height,x,y+height-r);
  s.lineTo(x,y+r);s.quadraticCurveTo(x,y,x+r,y);
  const g=new THREE.ExtrudeGeometry(s,{depth,bevelEnabled:true,bevelSegments:3,steps:1,bevelSize:0.028,bevelThickness:0.028,curveSegments:8});
  g.translate(0,0,-depth/2);g.computeVertexNormals();return g;
}
export function palette() {
  const standard=(color,metalness=.65,roughness=.32)=>new THREE.MeshStandardMaterial({color,metalness,roughness});
  const glow=(color,power=1.8)=>new THREE.MeshStandardMaterial({color,emissive:color,emissiveIntensity:power,roughness:.38,metalness:.25});
  return {
    glass:new THREE.MeshPhysicalMaterial({color:'#b9cce2',transmission:.92,roughness:.38,ior:1.5,thickness:.6,
      metalness:0,specularIntensity:.6,envMapIntensity:1.2,clearcoat:.24,clearcoatRoughness:.3}),
    prism:new THREE.MeshPhysicalMaterial({color:'#c7d3ff',transmission:.97,roughness:.1,ior:1.5,thickness:1.1,
      dispersion:.58,metalness:0,envMapIntensity:1.4}),
    dark:standard('#111e31',.75,.29), metal:standard('#556b82',.82,.25), deck:standard('#09101e',.6,.36),
    orange:glow(COLORS.orange,1.4),blue:glow(COLORS.blue,1.6),green:glow(COLORS.green,1.5),
    white:standard('#ced7e1',.5,.28),solar:standard('#123d62',.55,.26),
  };
}
export function box(parent,mat,w,h,d,x=0,y=0,z=0,radius=0) {
  const geom=radius?roundedSlabGeometry(w,h,d,radius):new THREE.BoxGeometry(w,h,d);
  const mesh=new THREE.Mesh(geom,mat);mesh.position.set(x,y,z);parent.add(mesh);return mesh;
}
export function cylinder(parent,mat,r,h,x=0,y=0,z=0,segments=32) {
  const mesh=new THREE.Mesh(new THREE.CylinderGeometry(r,r,h,segments),mat);mesh.position.set(x,y,z);parent.add(mesh);return mesh;
}
export function ring(parent,mat,r,thickness=.015,x=0,y=0,z=0) {
  const mesh=new THREE.Mesh(new THREE.TorusGeometry(r,thickness,8,80),mat);mesh.position.set(x,y,z);parent.add(mesh);return mesh;
}
export function wire(parent,points,color='#38bdf8',opacity=.5) {
  const g=new THREE.BufferGeometry().setFromPoints(points.map(p=>new THREE.Vector3(...p)));
  const mat=new THREE.LineBasicMaterial({color,transparent:true,opacity,depthWrite:false});
  const mesh=new THREE.Line(g,mat);parent.add(mesh);return mesh;
}
export function tube(parent,points,mat,radius=.025) {
  const curve=new THREE.CatmullRomCurve3(points.map(p=>new THREE.Vector3(...p)),false,'catmullrom',.12);
  const mesh=new THREE.Mesh(new THREE.TubeGeometry(curve,40,radius,6,false),mat);parent.add(mesh);return mesh;
}
