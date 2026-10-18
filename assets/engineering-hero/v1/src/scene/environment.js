import * as THREE from 'three';
import { seedRandom } from '../kinematics.js';
export function makeDome() {
  const material=new THREE.ShaderMaterial({side:THREE.BackSide,depthWrite:false,
    uniforms:{uTime:{value:0}},
    vertexShader:`varying vec3 vDirection;
      void main(){vDirection=normalize(position);gl_Position=projectionMatrix*modelViewMatrix*vec4(position,1.0);}`,
    fragmentShader:`precision highp float;varying vec3 vDirection;uniform float uTime;
      float blob(vec3 d,vec3 center,float falloff){return exp(-falloff*dot(d-normalize(center),d-normalize(center)));}
      void main(){vec3 d=normalize(vDirection);float s=sin(uTime*0.12)*0.06;
        vec3 col=vec3(0.004,0.008,0.022);
        col+=vec3(0.19,0.055,0.45)*blob(d,vec3(-.85,.5,-.9),4.8);
        col+=vec3(.58,.13,.045)*blob(d,vec3(.80+s,.25,.6),8.0);
        col+=vec3(.016,.20,.52)*blob(d,vec3(-.60,-.05,.7),7.5);
        col+=vec3(.21,.035,.22)*blob(d,vec3(.6,.75,-.9),6.0);
        col+=vec3(.023,.035,.10)*blob(d,vec3(0.,-.7,1.),2.5);
        gl_FragColor=vec4(col*.25,1.0);
      }`});
  return new THREE.Mesh(new THREE.SphereGeometry(230,48,24),material);
}
export function createEnvironment(renderer,scene) {
  const dome=makeDome();dome.position.set(30,0,-20);dome.renderOrder=-10;scene.add(dome);
  // Static HDR illumination probe of the same procedural dome at t=0. No remote HDRI.
  const probeScene=new THREE.Scene(),probeDome=makeDome();probeScene.add(probeDome);
  const keyPositions=[[4,4,2],[-4,1,-2],[0,6,-3]];
  keyPositions.forEach((p,i)=>{
    const m=new THREE.MeshBasicMaterial({color:[0xffb288,0x67bfff,0xb08bff][i]});
    m.color.multiplyScalar(3.5);const lightCard=new THREE.Mesh(new THREE.PlaneGeometry(4,5),m);
    lightCard.position.set(...p);lightCard.lookAt(0,0,0);probeScene.add(lightCard);
  });
  const pmrem=new THREE.PMREMGenerator(renderer),env=pmrem.fromScene(probeScene,.06,.1,500);
  scene.environment=env.texture;scene.environmentIntensity=.85;
  pmrem.dispose();probeScene.traverse(o=>{o.geometry?.dispose();if(o.material)o.material.dispose();});
  scene.add(new THREE.AmbientLight('#778ebf',.35));
  const sun=new THREE.DirectionalLight('#ddeaff',3.2);sun.position.set(10,18,30);scene.add(sun);
  const fill=new THREE.DirectionalLight('#ff8a4c',1.3);fill.position.set(-20,2,-10);scene.add(fill);
  const rng=seedRandom(),count=440,positions=new Float32Array(count*3),phase=new Float32Array(count);
  for(let i=0;i<count;i++){positions[i*3]=-15+rng()*96;positions[i*3+1]=-10+rng()*30;positions[i*3+2]=-65+rng()*78;phase[i]=rng()*6.2831853;}
  const geometry=new THREE.BufferGeometry();geometry.setAttribute('position',new THREE.BufferAttribute(positions,3));geometry.setAttribute('aPhase',new THREE.BufferAttribute(phase,1));
  const starMat=new THREE.ShaderMaterial({transparent:true,depthWrite:false,blending:THREE.AdditiveBlending,
    uniforms:{uTime:{value:0},uResolution:{value:1080}},
    vertexShader:`attribute float aPhase;uniform float uTime;uniform float uResolution;varying float vAlpha;
      void main(){vec3 p=position;p.x+=.20*sin(uTime*.14+aPhase);p.y+=.13*cos(uTime*.2+aPhase);
      vec4 mv=modelViewMatrix*vec4(p,1.);gl_Position=projectionMatrix*mv;
      gl_PointSize=clamp(uResolution*.024/-mv.z,1.,3.2);vAlpha=.18+.13*sin(aPhase+uTime*.5);}`,
    fragmentShader:`varying float vAlpha;void main(){float r=length(gl_PointCoord-.5);float a=(1.-smoothstep(.12,.5,r))*vAlpha;gl_FragColor=vec4(.42,.65,1.,a);}`});
  const stars=new THREE.Points(geometry,starMat);stars.frustumCulled=false;scene.add(stars);
  return { update(t,height){dome.material.uniforms.uTime.value=t;starMat.uniforms.uTime.value=t;starMat.uniforms.uResolution.value=height;},dispose(){env.dispose();} };
}
