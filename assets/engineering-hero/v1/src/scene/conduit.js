import * as THREE from 'three';
import { CHAPTERS } from '../config.js';
import { worldPoint, mod1 } from '../kinematics.js';
export function createConduit(scene) {
  const points=[[-12,-3.10,3],...CHAPTERS.map((c,i)=>worldPoint(i,[0,-3.10,1.25])),[76,-.9,-45]];
  const curve=new THREE.CatmullRomCurve3(points.map(p=>new THREE.Vector3(...p)),false,'catmullrom',.4);
  const material=new THREE.ShaderMaterial({uniforms:{uTime:{value:0}},
    vertexShader:`varying vec2 vUv;void main(){vUv=uv;gl_Position=projectionMatrix*modelViewMatrix*vec4(position,1.);}`,
    fragmentShader:`uniform float uTime;varying vec2 vUv;void main(){float p=pow(max(0.,sin(vUv.x*95.-uTime*3.2)),12.);
      vec3 c=mix(vec3(.08,.30,.5),vec3(1.,.29,.09),.5+.5*sin(vUv.x*18.-uTime*.5));
      gl_FragColor=vec4(c*(.8+3.*p),1.);}`});
  const mesh=new THREE.Mesh(new THREE.TubeGeometry(curve,440,.028,7,false),material);scene.add(mesh);
  const sheath=new THREE.Mesh(new THREE.TubeGeometry(curve,300,.073,6,false),new THREE.MeshBasicMaterial({color:'#ff8a4c',transparent:true,opacity:.06,depthWrite:false,blending:THREE.AdditiveBlending}));scene.add(sheath);
  const n=28,packets=new THREE.InstancedMesh(new THREE.SphereGeometry(.06,8,6),new THREE.MeshBasicMaterial({color:new THREE.Color('#ffac76').multiplyScalar(2.2)}),n);
  packets.frustumCulled=false;scene.add(packets);const matrix=new THREE.Matrix4();const pos=new THREE.Vector3();
  return {curve,update(t){material.uniforms.uTime.value=t;for(let i=0;i<n;i++){curve.getPointAt(mod1(i/n+t*.062),pos);matrix.makeTranslation(pos.x,pos.y,pos.z);packets.setMatrixAt(i,matrix);}packets.instanceMatrix.needsUpdate=true;}};
}
